"""Data fetchers for real-time market data."""

import asyncio
import logging
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from typing import Optional

import httpx

from llm_asset_oracle.core.models import Asset, AssetType

logger = logging.getLogger(__name__)


class AssetDataFetcher(ABC):
    """Abstract base class for asset data fetchers."""

    @abstractmethod
    async def fetch_price(self, symbol: str) -> Optional[dict]:
        """Fetch current price data for an asset."""
        pass

    @abstractmethod
    async def fetch_details(self, symbol: str) -> Optional[dict]:
        """Fetch detailed information about an asset."""
        pass

    async def enrich_asset(self, asset: Asset) -> Asset:
        """
        Enrich an asset with current market data.

        Args:
            asset: The asset to enrich

        Returns:
            Updated asset with market data
        """
        try:
            price_data = await self.fetch_price(asset.symbol)
            if price_data:
                return Asset(
                    symbol=asset.symbol,
                    name=asset.name,
                    asset_type=asset.asset_type,
                    description=asset.description,
                    current_price=price_data.get("price"),
                    price_change_24h=price_data.get("change_24h"),
                    market_cap=price_data.get("market_cap"),
                    volume_24h=price_data.get("volume_24h"),
                )
        except Exception as e:
            logger.warning(f"Failed to enrich asset {asset.symbol}: {e}")

        return asset


class CryptoDataFetcher(AssetDataFetcher):
    """Fetcher for cryptocurrency data using CoinGecko API."""

    BASE_URL = "https://api.coingecko.com/api/v3"

    # Symbol to CoinGecko ID mapping
    SYMBOL_MAP = {
        "BTC": "bitcoin",
        "ETH": "ethereum",
        "SOL": "solana",
        "XRP": "ripple",
        "ADA": "cardano",
        "DOGE": "dogecoin",
        "DOT": "polkadot",
        "AVAX": "avalanche-2",
        "LINK": "chainlink",
        "MATIC": "matic-network",
        "UNI": "uniswap",
        "ATOM": "cosmos",
        "LTC": "litecoin",
        "NEAR": "near",
        "ARB": "arbitrum",
    }

    def __init__(self, api_key: Optional[str] = None):
        """Initialize with optional API key for higher rate limits."""
        self.api_key = api_key
        self._cache: dict = {}
        self._cache_ttl = timedelta(minutes=5)

    def _get_coin_id(self, symbol: str) -> Optional[str]:
        """Convert symbol to CoinGecko coin ID."""
        return self.SYMBOL_MAP.get(symbol.upper())

    async def fetch_price(self, symbol: str) -> Optional[dict]:
        """Fetch current price data for a cryptocurrency."""
        coin_id = self._get_coin_id(symbol)
        if not coin_id:
            logger.warning(f"Unknown crypto symbol: {symbol}")
            return None

        # Check cache
        cache_key = f"price_{coin_id}"
        if cache_key in self._cache:
            cached_time, cached_data = self._cache[cache_key]
            if datetime.now() - cached_time < self._cache_ttl:
                return cached_data

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                params = {
                    "ids": coin_id,
                    "vs_currencies": "usd",
                    "include_24hr_change": "true",
                    "include_market_cap": "true",
                    "include_24hr_vol": "true",
                }
                if self.api_key:
                    params["x_cg_demo_api_key"] = self.api_key

                response = await client.get(
                    f"{self.BASE_URL}/simple/price",
                    params=params,
                )
                response.raise_for_status()
                data = response.json()

                if coin_id in data:
                    coin_data = data[coin_id]
                    result = {
                        "price": coin_data.get("usd"),
                        "change_24h": coin_data.get("usd_24h_change"),
                        "market_cap": coin_data.get("usd_market_cap"),
                        "volume_24h": coin_data.get("usd_24h_vol"),
                    }

                    # Cache result
                    self._cache[cache_key] = (datetime.now(), result)
                    return result

        except Exception as e:
            logger.error(f"Failed to fetch crypto price for {symbol}: {e}")

        return None

    async def fetch_details(self, symbol: str) -> Optional[dict]:
        """Fetch detailed information about a cryptocurrency."""
        coin_id = self._get_coin_id(symbol)
        if not coin_id:
            return None

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    f"{self.BASE_URL}/coins/{coin_id}",
                    params={
                        "localization": "false",
                        "tickers": "false",
                        "community_data": "false",
                        "developer_data": "false",
                    },
                )
                response.raise_for_status()
                return response.json()

        except Exception as e:
            logger.error(f"Failed to fetch crypto details for {symbol}: {e}")

        return None


class StockDataFetcher(AssetDataFetcher):
    """Fetcher for stock data using Yahoo Finance (via yfinance)."""

    def __init__(self, alpha_vantage_key: Optional[str] = None):
        """Initialize with optional Alpha Vantage API key."""
        self.alpha_vantage_key = alpha_vantage_key
        self._cache: dict = {}
        self._cache_ttl = timedelta(minutes=5)

    async def fetch_price(self, symbol: str) -> Optional[dict]:
        """Fetch current price data for a stock."""
        # Check cache
        cache_key = f"price_{symbol}"
        if cache_key in self._cache:
            cached_time, cached_data = self._cache[cache_key]
            if datetime.now() - cached_time < self._cache_ttl:
                return cached_data

        # Use yfinance in a thread pool to avoid blocking
        try:
            import yfinance as yf

            def _fetch():
                ticker = yf.Ticker(symbol)
                info = ticker.info

                # Get price data
                price = info.get("regularMarketPrice") or info.get("currentPrice")
                prev_close = info.get("regularMarketPreviousClose") or info.get("previousClose")

                change_24h = None
                if price and prev_close:
                    change_24h = ((price - prev_close) / prev_close) * 100

                return {
                    "price": price,
                    "change_24h": change_24h,
                    "market_cap": info.get("marketCap"),
                    "volume_24h": info.get("regularMarketVolume"),
                }

            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(None, _fetch)

            if result.get("price"):
                self._cache[cache_key] = (datetime.now(), result)
                return result

        except Exception as e:
            logger.error(f"Failed to fetch stock price for {symbol}: {e}")

        return None

    async def fetch_details(self, symbol: str) -> Optional[dict]:
        """Fetch detailed information about a stock."""
        try:
            import yfinance as yf

            def _fetch():
                ticker = yf.Ticker(symbol)
                return ticker.info

            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(None, _fetch)

        except Exception as e:
            logger.error(f"Failed to fetch stock details for {symbol}: {e}")

        return None


class UnifiedDataFetcher:
    """Unified fetcher that routes to appropriate data source."""

    def __init__(
        self,
        coingecko_key: Optional[str] = None,
        alpha_vantage_key: Optional[str] = None,
    ):
        """Initialize with optional API keys."""
        self.crypto_fetcher = CryptoDataFetcher(api_key=coingecko_key)
        self.stock_fetcher = StockDataFetcher(alpha_vantage_key=alpha_vantage_key)

    def _get_fetcher(self, asset_type: AssetType) -> AssetDataFetcher:
        """Get appropriate fetcher for asset type."""
        if asset_type == AssetType.CRYPTO:
            return self.crypto_fetcher
        else:
            return self.stock_fetcher

    async def enrich_asset(self, asset: Asset) -> Asset:
        """Enrich an asset with current market data."""
        fetcher = self._get_fetcher(asset.asset_type)
        return await fetcher.enrich_asset(asset)

    async def enrich_assets(self, assets: list[Asset]) -> list[Asset]:
        """Enrich multiple assets concurrently."""
        tasks = [self.enrich_asset(asset) for asset in assets]
        return await asyncio.gather(*tasks)

    async def fetch_price(self, asset: Asset) -> Optional[dict]:
        """Fetch price data for an asset."""
        fetcher = self._get_fetcher(asset.asset_type)
        return await fetcher.fetch_price(asset.symbol)
