"""Data source interfaces for market, documentation, and community metrics."""

from __future__ import annotations

import abc
import dataclasses
import datetime as dt
from typing import Any, Iterable, Mapping

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from .config import Config


class DataSourceError(RuntimeError):
    """Raised when a downstream data provider returns an error."""


class BaseDataSource(abc.ABC):
    """Shared functionality for external data sources."""

    def __init__(self, config: Config) -> None:
        self.config = config

    @abc.abstractmethod
    async def fetch(self, *args: Any, **kwargs: Any) -> Any:
        """Retrieve data from the provider."""


@dataclasses.dataclass(slots=True)
class PricePoint:
    timestamp: dt.datetime
    price: float
    volume: float
    market_cap: float


class CoinGeckoSource(BaseDataSource):
    """Wrapper around the CoinGecko professional API."""

    BASE_URL = "https://pro-api.coingecko.com/api/v3"

    def __init__(self, config: Config) -> None:
        super().__init__(config)
        self.client = httpx.AsyncClient(timeout=30)
        self.api_key = self.config.get("apis.coingecko.api_key")
        base_url = self.config.get("apis.coingecko.base_url")
        if base_url:
            self.BASE_URL = base_url

    @retry(wait=wait_exponential(multiplier=1, min=1, max=60), stop=stop_after_attempt(5))
    async def fetch_market_chart(self, asset_id: str, days: int = 90) -> Mapping[str, Any]:
        params = {"vs_currency": "usd", "days": days}
        headers = {"x-cg-pro-api-key": self.api_key} if self.api_key else {}
        response = await self.client.get(f"{self.BASE_URL}/coins/{asset_id}/market_chart", params=params, headers=headers)
        if response.status_code != 200:
            raise DataSourceError(f"CoinGecko error {response.status_code}: {response.text}")
        return response.json()

    async def fetch(self, asset_id: str, days: int = 90) -> Iterable[PricePoint]:
        payload = await self.fetch_market_chart(asset_id, days)
        prices = payload.get("prices", [])
        volumes = {ts: vol for ts, vol in payload.get("total_volumes", [])}
        market_caps = {ts: cap for ts, cap in payload.get("market_caps", [])}
        for ts, price in prices:
            timestamp = dt.datetime.fromtimestamp(ts / 1000, tz=dt.timezone.utc)
            yield PricePoint(
                timestamp=timestamp,
                price=float(price),
                volume=float(volumes.get(ts, 0.0)),
                market_cap=float(market_caps.get(ts, 0.0)),
            )


class WikipediaSource(BaseDataSource):
    """Retrieves article metadata relevant to LLOS web presence scoring."""

    API_URL = "https://en.wikipedia.org/w/api.php"

    def __init__(self, config: Config) -> None:
        super().__init__(config)
        self.client = httpx.AsyncClient(timeout=20)

    @retry(wait=wait_exponential(multiplier=1, min=1, max=30), stop=stop_after_attempt(5))
    async def fetch(self, title: str) -> Mapping[str, Any]:  # type: ignore[override]
        params = {
            "action": "query",
            "prop": "info|revisions",
            "titles": title,
            "rvprop": "content|timestamp",
            "format": "json",
            "formatversion": 2,
        }
        response = await self.client.get(self.API_URL, params=params)
        if response.status_code != 200:
            raise DataSourceError(f"Wikipedia error {response.status_code}: {response.text}")
        return response.json()


async def close_sources(*sources: BaseDataSource) -> None:
    """Gracefully close HTTP clients to release resources."""

    for source in sources:
        client = getattr(source, "client", None)
        if hasattr(client, "aclose"):
            await client.aclose()

