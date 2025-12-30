"""
Multi-Model Oracle - The New Core Engine

This is the redesigned oracle that:
1. Uses OpenRouter to query 10-20 diverse LLM models
2. Sends factual-only prompts (no bias-inducing language)
3. Collects simple BUY/SELL/CONFIDENCE responses
4. Aggregates using statistical consensus methods
5. Produces grades, heatmaps, and directional signals
"""

import asyncio
import logging
from dataclasses import dataclass
from typing import Optional

from llm_asset_oracle.analysis.factual_prompts import (
    AssetFacts,
    build_factual_prompt,
    get_preset_facts,
    create_minimal_facts,
)
from llm_asset_oracle.analysis.consensus_math import (
    ConsensusResult,
    calculate_consensus,
    generate_heatmap_data,
    format_heatmap_text,
    format_consensus_summary,
)
from llm_asset_oracle.llm.openrouter import (
    OpenRouterClient,
    ModelResponse,
    AVAILABLE_MODELS,
    get_model_subset,
)
from llm_asset_oracle.data.fetchers import CryptoDataFetcher, StockDataFetcher

logger = logging.getLogger(__name__)


@dataclass
class OracleConfig:
    """Configuration for the Multi-Model Oracle."""

    # OpenRouter
    openrouter_api_key: str
    site_url: str = "https://llm-asset-oracle.app"
    site_name: str = "LLM Asset Oracle"

    # Model selection
    model_count: int = 15  # How many models to query
    include_providers: Optional[list[str]] = None  # Filter to specific providers
    exclude_providers: Optional[list[str]] = None  # Exclude specific providers
    budget_mode: bool = False  # Prefer cheaper models

    # Query settings
    max_concurrent: int = 10  # Max parallel requests
    timeout_seconds: float = 60.0  # Per-request timeout
    max_tokens: int = 100  # Keep responses short

    # Data enrichment
    fetch_market_data: bool = True  # Enrich with live prices


class MultiModelOracle:
    """
    Multi-Model Oracle for consensus-based asset analysis.

    This oracle queries multiple LLMs through OpenRouter with identical
    factual prompts and aggregates their responses into actionable signals.
    """

    def __init__(self, config: OracleConfig):
        """
        Initialize the oracle.

        Args:
            config: OracleConfig with settings
        """
        self.config = config

        # Initialize OpenRouter client
        self.client = OpenRouterClient(
            api_key=config.openrouter_api_key,
            site_url=config.site_url,
            site_name=config.site_name,
            timeout=config.timeout_seconds,
            max_concurrent=config.max_concurrent,
        )

        # Data fetchers
        self.crypto_fetcher = CryptoDataFetcher()
        self.stock_fetcher = StockDataFetcher()

        # Model selection
        self._model_ids = get_model_subset(
            count=config.model_count,
            include_providers=config.include_providers,
            exclude_providers=config.exclude_providers,
            budget_mode=config.budget_mode,
        )

        logger.info(f"Oracle initialized with {len(self._model_ids)} models")

    @property
    def models(self) -> list[str]:
        """Get list of active model IDs."""
        return self._model_ids

    @property
    def model_count(self) -> int:
        """Get number of active models."""
        return len(self._model_ids)

    async def analyze(
        self,
        symbol: str,
        name: Optional[str] = None,
        asset_class: Optional[str] = None,
        custom_facts: Optional[AssetFacts] = None,
    ) -> ConsensusResult:
        """
        Analyze an asset across all configured models.

        Args:
            symbol: Asset symbol (e.g., "BTC", "AAPL")
            name: Asset name (optional, will lookup if not provided)
            asset_class: "Cryptocurrency" or "Stock" (optional)
            custom_facts: Custom AssetFacts (optional)

        Returns:
            ConsensusResult with aggregated analysis
        """
        symbol = symbol.upper()

        # Get or create facts
        if custom_facts:
            facts = custom_facts
        else:
            facts = await self._get_facts(symbol, name, asset_class)

        logger.info(f"Analyzing {facts.symbol} ({facts.name}) with {self.model_count} models")

        # Build the factual prompt
        prompt = build_factual_prompt(facts)

        logger.debug(f"Prompt:\n{prompt}")

        # Query all models
        responses = await self.client.query_all_models(
            prompt=prompt,
            model_ids=self._model_ids,
            max_tokens=self.config.max_tokens,
        )

        # Calculate consensus
        result = calculate_consensus(
            symbol=facts.symbol,
            name=facts.name,
            responses=responses,
        )

        logger.info(
            f"Analysis complete: {result.direction.value} "
            f"(Grade: {result.grade.value}, Score: {result.grade_score:.0f})"
        )

        return result

    async def analyze_batch(
        self,
        symbols: list[str],
        max_concurrent_assets: int = 3,
    ) -> list[ConsensusResult]:
        """
        Analyze multiple assets.

        Args:
            symbols: List of asset symbols
            max_concurrent_assets: How many assets to analyze in parallel

        Returns:
            List of ConsensusResult for each asset
        """
        semaphore = asyncio.Semaphore(max_concurrent_assets)

        async def analyze_one(symbol: str) -> Optional[ConsensusResult]:
            async with semaphore:
                try:
                    return await self.analyze(symbol)
                except Exception as e:
                    logger.error(f"Failed to analyze {symbol}: {e}")
                    return None

        tasks = [analyze_one(s) for s in symbols]
        results = await asyncio.gather(*tasks)

        return [r for r in results if r is not None]

    async def compare(
        self,
        symbol1: str,
        symbol2: str,
    ) -> dict:
        """
        Compare two assets.

        Args:
            symbol1: First asset symbol
            symbol2: Second asset symbol

        Returns:
            Comparison dictionary
        """
        results = await self.analyze_batch([symbol1, symbol2])

        if len(results) < 2:
            return {"error": "Failed to analyze one or both assets"}

        r1, r2 = results[0], results[1]

        # Determine winner
        if r1.grade_score > r2.grade_score + 5:
            winner = r1.symbol
        elif r2.grade_score > r1.grade_score + 5:
            winner = r2.symbol
        else:
            winner = "TIE"

        return {
            "asset1": {
                "symbol": r1.symbol,
                "direction": r1.direction.value,
                "grade": r1.grade.value,
                "score": r1.grade_score,
                "consensus": r1.consensus_strength,
                "buy_pct": r1.buy_pct,
                "sell_pct": r1.sell_pct,
            },
            "asset2": {
                "symbol": r2.symbol,
                "direction": r2.direction.value,
                "grade": r2.grade.value,
                "score": r2.grade_score,
                "consensus": r2.consensus_strength,
                "buy_pct": r2.buy_pct,
                "sell_pct": r2.sell_pct,
            },
            "winner": winner,
            "score_diff": abs(r1.grade_score - r2.grade_score),
        }

    async def rank_assets(
        self,
        symbols: list[str],
    ) -> list[ConsensusResult]:
        """
        Rank multiple assets by their signal grade.

        Args:
            symbols: List of asset symbols

        Returns:
            Sorted list of ConsensusResult (best first)
        """
        results = await self.analyze_batch(symbols)

        # Sort by grade score (descending)
        results.sort(key=lambda r: r.grade_score, reverse=True)

        return results

    async def _get_facts(
        self,
        symbol: str,
        name: Optional[str],
        asset_class: Optional[str],
    ) -> AssetFacts:
        """Get or create facts for an asset."""
        # Try preset facts first
        preset = get_preset_facts(symbol)
        if preset:
            # Enrich with live data if enabled
            if self.config.fetch_market_data:
                preset = await self._enrich_facts(preset)
            return preset

        # Create minimal facts
        if not name:
            name = symbol

        if not asset_class:
            # Guess based on symbol
            if len(symbol) <= 5 and symbol.isalpha():
                asset_class = "Unknown"
            else:
                asset_class = "Stock"

        facts = create_minimal_facts(symbol, name, asset_class)

        # Try to enrich with market data
        if self.config.fetch_market_data:
            facts = await self._enrich_facts(facts)

        return facts

    async def _enrich_facts(self, facts: AssetFacts) -> AssetFacts:
        """Enrich facts with live market data."""
        try:
            if facts.asset_class == "Cryptocurrency":
                data = await self.crypto_fetcher.fetch_price(facts.symbol)
            else:
                data = await self.stock_fetcher.fetch_price(facts.symbol)

            if data:
                # Update facts with live data
                facts.current_price_usd = data.get("price")
                facts.price_change_24h_pct = data.get("change_24h")
                facts.market_cap_usd = data.get("market_cap")
                facts.volume_24h_usd = data.get("volume_24h")

        except Exception as e:
            logger.warning(f"Failed to enrich {facts.symbol}: {e}")

        return facts

    def get_heatmap(self, result: ConsensusResult) -> str:
        """Generate ASCII heatmap for a result."""
        cells = generate_heatmap_data(result)
        return format_heatmap_text(cells)

    def get_summary(self, result: ConsensusResult) -> str:
        """Generate text summary for a result."""
        return format_consensus_summary(result)


# =============================================================================
# FACTORY FUNCTIONS
# =============================================================================

def create_oracle_from_env() -> MultiModelOracle:
    """
    Create oracle from environment variables.

    Required env vars:
        OPENROUTER_API_KEY: Your OpenRouter API key

    Optional env vars:
        ORACLE_MODEL_COUNT: Number of models (default: 15)
        ORACLE_BUDGET_MODE: "true" for cheaper models (default: false)
        ORACLE_MAX_CONCURRENT: Max parallel requests (default: 10)
    """
    import os

    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        raise ValueError("OPENROUTER_API_KEY environment variable is required")

    model_count = int(os.getenv("ORACLE_MODEL_COUNT", "15"))
    budget_mode = os.getenv("ORACLE_BUDGET_MODE", "").lower() == "true"
    max_concurrent = int(os.getenv("ORACLE_MAX_CONCURRENT", "10"))

    config = OracleConfig(
        openrouter_api_key=api_key,
        model_count=model_count,
        budget_mode=budget_mode,
        max_concurrent=max_concurrent,
    )

    return MultiModelOracle(config)


async def quick_analyze(symbol: str, api_key: str) -> ConsensusResult:
    """
    Quick one-off analysis.

    Args:
        symbol: Asset symbol
        api_key: OpenRouter API key

    Returns:
        ConsensusResult
    """
    config = OracleConfig(
        openrouter_api_key=api_key,
        model_count=10,  # Fewer models for speed
        budget_mode=True,  # Use cheaper models
    )

    oracle = MultiModelOracle(config)
    return await oracle.analyze(symbol)
