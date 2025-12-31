"""
Valuation Engine

The core engine that:
1. Builds prompts from user input
2. Queries 15 LLMs via OpenRouter
3. Parses market cap estimates
4. Calculates statistics
5. Generates charts
"""

import asyncio
import logging
import time
from dataclasses import dataclass, field
from typing import Optional, Callable, Awaitable

import httpx

from llm_asset_oracle.valuation.prompt_template import (
    ValuationPrompt,
    build_valuation_prompt,
)
from llm_asset_oracle.valuation.parser import (
    parse_market_cap,
    MarketCapResult,
)
from llm_asset_oracle.valuation.statistics import (
    ValuationStatistics,
    calculate_valuation_stats,
)
from llm_asset_oracle.valuation.charts import (
    generate_valuation_chart,
)
from llm_asset_oracle.valuation.models import (
    VALUATION_MODELS,
    MODELS_BY_ID,
    ALL_MODEL_IDS,
)

logger = logging.getLogger(__name__)


@dataclass
class ValuationResult:
    """Complete result of a valuation query."""

    # Input
    prompt_data: ValuationPrompt
    prompt_text: str

    # Results
    estimates: list[MarketCapResult] = field(default_factory=list)
    statistics: Optional[ValuationStatistics] = None

    # Metadata
    total_time_ms: float = 0
    total_cost_usd: float = 0
    models_queried: int = 0
    models_succeeded: int = 0
    models_failed: int = 0


# Callback type for streaming updates
StreamCallback = Callable[[MarketCapResult], Awaitable[None]]


class ValuationEngine:
    """
    Engine for multi-model valuation analysis.

    Usage:
        engine = ValuationEngine(api_key="sk-or-...")

        result = await engine.valuate(
            token_name="Post Fiat",
            ticker="PF",
            year=2026,
            description="...",
            differentiator="...",
            factors="...",
            on_result=my_callback,  # Called as each model responds
        )
    """

    BASE_URL = "https://openrouter.ai/api/v1"

    def __init__(
        self,
        api_key: str,
        site_url: str = "https://llm-asset-oracle.app",
        site_name: str = "LLM Asset Oracle",
        timeout: float = 120.0,  # Longer timeout for reasoning models
        max_concurrent: int = 8,
    ):
        self.api_key = api_key
        self.site_url = site_url
        self.site_name = site_name
        self.timeout = timeout
        self._semaphore = asyncio.Semaphore(max_concurrent)

    async def valuate(
        self,
        token_name: str,
        ticker: str,
        year: int,
        category: str,
        description: str,
        differentiator: str,
        factors: str,
        comparable: Optional[str] = None,
        on_result: Optional[StreamCallback] = None,
        model_ids: Optional[list[str]] = None,
    ) -> ValuationResult:
        """
        Run valuation analysis across all models.

        Args:
            token_name: Name of the token
            ticker: Ticker symbol
            year: Target year
            category: Token category (e.g., "Layer 1")
            description: What it does
            differentiator: What makes it unique
            factors: What to consider
            comparable: Optional comparable projects
            on_result: Callback called as each model responds
            model_ids: Optional custom list of models (defaults to all)

        Returns:
            ValuationResult with all data
        """
        start_time = time.time()

        # Build prompt
        prompt_data = ValuationPrompt(
            token_name=token_name,
            ticker=ticker,
            year=year,
            category=category,
            description=description,
            key_differentiator=differentiator,
            factors=factors,
            comparable_projects=comparable,
        )
        prompt_text = build_valuation_prompt(prompt_data)

        logger.info(f"Starting valuation for {token_name} ({ticker})")
        logger.debug(f"Prompt: {prompt_text}")

        # Use specified models or all
        models_to_query = model_ids or ALL_MODEL_IDS

        # Query all models concurrently
        tasks = []
        for model_id in models_to_query:
            task = self._query_model(model_id, prompt_text, on_result)
            tasks.append(task)

        estimates = await asyncio.gather(*tasks)

        # Calculate statistics
        statistics = calculate_valuation_stats(
            token_name=token_name,
            ticker=ticker,
            target_year=year,
            estimates=estimates,
        )

        total_time = (time.time() - start_time) * 1000

        # Build result
        result = ValuationResult(
            prompt_data=prompt_data,
            prompt_text=prompt_text,
            estimates=estimates,
            statistics=statistics,
            total_time_ms=total_time,
            models_queried=len(models_to_query),
            models_succeeded=statistics.successful_parses,
            models_failed=statistics.failed_parses,
        )

        logger.info(
            f"Valuation complete: {statistics.successful_parses}/{len(models_to_query)} successful, "
            f"median={statistics.median_formatted}"
        )

        return result

    async def _query_model(
        self,
        model_id: str,
        prompt: str,
        on_result: Optional[StreamCallback],
    ) -> MarketCapResult:
        """Query a single model and parse the response."""
        model_config = MODELS_BY_ID.get(model_id)
        model_name = model_config.name if model_config else model_id

        async with self._semaphore:
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    response = await client.post(
                        f"{self.BASE_URL}/chat/completions",
                        headers={
                            "Authorization": f"Bearer {self.api_key}",
                            "HTTP-Referer": self.site_url,
                            "X-Title": self.site_name,
                            "Content-Type": "application/json",
                        },
                        json={
                            "model": model_id,
                            "messages": [{"role": "user", "content": prompt}],
                            "max_tokens": 500,
                            "temperature": 0.3,  # Lower temp for more consistent estimates
                        },
                    )

                    if response.status_code != 200:
                        error_text = response.text[:200]
                        logger.warning(f"{model_name} failed: HTTP {response.status_code}")
                        result = MarketCapResult(
                            value_billions=None,
                            raw_text="",
                            confidence=0,
                            model_name=model_name,
                            model_id=model_id,
                            full_response=error_text,
                            error=f"HTTP {response.status_code}",
                        )
                    else:
                        data = response.json()
                        content = data["choices"][0]["message"]["content"]

                        # Parse the response
                        result = parse_market_cap(content, model_name, model_id)

                        if result.value_billions:
                            logger.info(f"✅ {model_name}: {result.value_formatted}")
                        else:
                            logger.warning(f"⚠️ {model_name}: Could not parse value")

            except asyncio.TimeoutError:
                logger.warning(f"{model_name} timed out")
                result = MarketCapResult(
                    value_billions=None,
                    raw_text="",
                    confidence=0,
                    model_name=model_name,
                    model_id=model_id,
                    full_response="",
                    error="Timeout",
                )
            except Exception as e:
                logger.error(f"{model_name} error: {e}")
                result = MarketCapResult(
                    value_billions=None,
                    raw_text="",
                    confidence=0,
                    model_name=model_name,
                    model_id=model_id,
                    full_response="",
                    error=str(e),
                )

        # Call streaming callback
        if on_result:
            try:
                await on_result(result)
            except Exception as e:
                logger.error(f"Callback error: {e}")

        return result

    def generate_chart(self, result: ValuationResult):
        """Generate chart from result."""
        if result.statistics:
            return generate_valuation_chart(result.statistics)
        return None


async def quick_valuate(
    api_key: str,
    token_name: str,
    ticker: str,
    year: int,
    description: str,
    differentiator: str,
    factors: str,
) -> ValuationResult:
    """
    Quick one-shot valuation.

    Args:
        api_key: OpenRouter API key
        Other args: Valuation parameters

    Returns:
        ValuationResult
    """
    engine = ValuationEngine(api_key)
    return await engine.valuate(
        token_name=token_name,
        ticker=ticker,
        year=year,
        category="",
        description=description,
        differentiator=differentiator,
        factors=factors,
    )
