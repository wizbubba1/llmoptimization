"""Main LLM Asset Oracle - the core analysis engine."""

import asyncio
import logging
from typing import Optional

from llm_asset_oracle.analysis.prompts import PromptTemplates
from llm_asset_oracle.analysis.scoring import ConsensusCalculator, RankingEngine
from llm_asset_oracle.analysis.insights import InsightExtractor
from llm_asset_oracle.core.config import Settings, get_settings
from llm_asset_oracle.core.models import Asset, AssetType, ConsensusScore, AnalysisResult
from llm_asset_oracle.data.assets import (
    get_asset_by_symbol,
    create_custom_asset,
    POPULAR_CRYPTOS,
    POPULAR_STOCKS,
)
from llm_asset_oracle.data.cache import DataCache
from llm_asset_oracle.data.fetchers import UnifiedDataFetcher
from llm_asset_oracle.llm.base import LLMQueryEngine
from llm_asset_oracle.llm.factory import get_all_providers, get_diverse_providers

logger = logging.getLogger(__name__)


class LLMAssetOracle:
    """
    The LLM Asset Oracle - main analysis engine.

    This class orchestrates the entire analysis pipeline:
    1. Asset lookup and enrichment with market data
    2. LLM querying across multiple providers
    3. Consensus calculation and scoring
    4. Result caching and historical tracking

    Usage:
        oracle = LLMAssetOracle()
        await oracle.initialize()

        # Analyze a single asset
        result = await oracle.analyze("BTC")

        # Compare two assets
        comparison = await oracle.compare("BTC", "ETH")

        # Get top-rated assets
        top = await oracle.get_top_assets(category="crypto", limit=10)
    """

    def __init__(self, settings: Optional[Settings] = None):
        """
        Initialize the Oracle.

        Args:
            settings: Optional Settings instance. Uses default if not provided.
        """
        self.settings = settings or get_settings()
        self._initialized = False

        # Components (initialized lazily)
        self._providers: list = []
        self._query_engine: Optional[LLMQueryEngine] = None
        self._data_fetcher: Optional[UnifiedDataFetcher] = None
        self._cache: Optional[DataCache] = None

    async def initialize(self):
        """Initialize all Oracle components."""
        if self._initialized:
            return

        logger.info("Initializing LLM Asset Oracle...")

        # Initialize providers
        self._providers = get_diverse_providers(
            count=self.settings.consensus_model_count,
            settings=self.settings,
        )

        if not self._providers:
            logger.warning(
                "No LLM providers configured. "
                "Please set API keys in .env file."
            )

        self._query_engine = LLMQueryEngine(self._providers)

        # Initialize data fetcher
        self._data_fetcher = UnifiedDataFetcher(
            coingecko_key=self.settings.coingecko_api_key,
            alpha_vantage_key=self.settings.alpha_vantage_api_key,
        )

        # Initialize cache
        self._cache = DataCache(self.settings.database_path)
        await self._cache.initialize()

        self._initialized = True
        logger.info(
            f"Oracle initialized with {len(self._providers)} LLM providers: "
            f"{[p.provider_name for p in self._providers]}"
        )

    async def analyze(
        self,
        symbol: str,
        asset_type: Optional[AssetType] = None,
        use_cache: bool = True,
        enrich_data: bool = True,
    ) -> AnalysisResult:
        """
        Analyze an asset and get consensus score.

        Args:
            symbol: The asset symbol (e.g., "BTC", "AAPL")
            asset_type: Optional asset type hint
            use_cache: Whether to use cached responses
            enrich_data: Whether to fetch current market data

        Returns:
            AnalysisResult with consensus and market data
        """
        await self.initialize()

        # Look up or create asset
        asset = self._get_or_create_asset(symbol, asset_type)

        # Enrich with market data if requested
        if enrich_data:
            asset = await self._data_fetcher.enrich_asset(asset)

        # Check cache for recent responses
        cached_responses = []
        if use_cache:
            cached_responses = await self._cache.get_cached_responses(
                asset.symbol,
                max_age_seconds=self.settings.cache_ttl_seconds,
            )

        # Determine how many new queries we need
        needed_count = self.settings.consensus_model_count - len(cached_responses)

        # Query LLMs if needed
        new_responses = []
        if needed_count > 0 and self._providers:
            prompt = PromptTemplates.format_asset_analysis(asset)

            # Query subset of providers
            new_responses = await self._query_engine.query_subset(
                asset, prompt, count=needed_count
            )

            # Cache new responses
            if new_responses:
                await self._cache.cache_responses(
                    new_responses,
                    ttl_seconds=self.settings.cache_ttl_seconds,
                )

        # Combine all responses
        all_responses = cached_responses + new_responses

        if not all_responses:
            raise ValueError(
                f"No LLM responses available for {symbol}. "
                "Please configure at least one LLM provider."
            )

        # Calculate consensus
        consensus = ConsensusCalculator.calculate_consensus(asset, all_responses)

        # Save to history
        await self._cache.save_consensus(consensus)

        # Get historical data
        historical = await self._cache.get_historical_scores(asset.symbol)
        historical_scores = [h["los_score"] for h in historical]
        trend = await self._cache.get_score_trend(asset.symbol)

        return AnalysisResult(
            consensus=consensus,
            market_data={
                "price": asset.current_price,
                "change_24h": asset.price_change_24h,
                "market_cap": asset.market_cap,
                "volume_24h": asset.volume_24h,
            } if asset.current_price else None,
            historical_scores=historical_scores[:10],
            score_trend=trend,
        )

    async def quick_analyze(self, symbol: str) -> dict:
        """
        Quick analysis with minimal LLM queries.

        Returns a simplified result dictionary.
        """
        try:
            result = await self.analyze(symbol, use_cache=True)
            return {
                "symbol": result.consensus.asset.symbol,
                "name": result.consensus.asset.name,
                "los_score": result.consensus.los_score,
                "recommendation": result.consensus.recommendation,
                "consensus_strength": result.consensus.consensus_strength,
                "models_queried": result.consensus.total_models_queried,
            }
        except Exception as e:
            return {
                "symbol": symbol,
                "error": str(e),
            }

    async def compare(
        self, symbol1: str, symbol2: str
    ) -> dict:
        """
        Compare two assets.

        Args:
            symbol1: First asset symbol
            symbol2: Second asset symbol

        Returns:
            Comparison result dictionary
        """
        # Analyze both assets concurrently
        results = await asyncio.gather(
            self.analyze(symbol1),
            self.analyze(symbol2),
            return_exceptions=True,
        )

        # Handle errors
        errors = []
        consensuses = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                errors.append(f"{[symbol1, symbol2][i]}: {result}")
            else:
                consensuses.append(result.consensus)

        if len(consensuses) < 2:
            return {"error": "Failed to analyze one or both assets", "details": errors}

        # Generate comparison
        comparison = InsightExtractor.compare_assets(consensuses[0], consensuses[1])
        return comparison

    async def analyze_batch(
        self, symbols: list[str], max_concurrent: int = 3
    ) -> list[AnalysisResult]:
        """
        Analyze multiple assets.

        Args:
            symbols: List of asset symbols
            max_concurrent: Maximum concurrent analyses

        Returns:
            List of AnalysisResult objects
        """
        semaphore = asyncio.Semaphore(max_concurrent)

        async def _analyze_with_semaphore(symbol: str):
            async with semaphore:
                try:
                    return await self.analyze(symbol)
                except Exception as e:
                    logger.error(f"Failed to analyze {symbol}: {e}")
                    return None

        tasks = [_analyze_with_semaphore(s) for s in symbols]
        results = await asyncio.gather(*tasks)

        return [r for r in results if r is not None]

    async def get_top_assets(
        self,
        category: Optional[str] = None,
        limit: int = 10,
        min_consensus: float = 40.0,
    ) -> list[ConsensusScore]:
        """
        Get top-rated assets by LOS score.

        Args:
            category: Filter by "crypto", "stock", or None for all
            limit: Maximum number of results
            min_consensus: Minimum consensus strength threshold

        Returns:
            List of ConsensusScore objects, sorted by LOS
        """
        await self.initialize()

        # Select assets to analyze
        if category == "crypto":
            assets = POPULAR_CRYPTOS[:limit * 2]  # Analyze more than needed
        elif category == "stock":
            assets = POPULAR_STOCKS[:limit * 2]
        else:
            assets = (POPULAR_CRYPTOS + POPULAR_STOCKS)[:limit * 2]

        # Analyze all assets
        results = await self.analyze_batch([a.symbol for a in assets])

        # Extract consensus scores
        consensus_scores = [r.consensus for r in results]

        # Filter and rank
        filtered = RankingEngine.filter_by_consensus(consensus_scores, min_consensus)
        ranked = RankingEngine.rank_assets(filtered)

        return ranked[:limit]

    async def get_high_conviction_picks(
        self,
        category: Optional[str] = None,
        limit: int = 5,
    ) -> list[ConsensusScore]:
        """
        Get high-conviction picks (high LOS + high consensus).

        Args:
            category: Filter by category
            limit: Maximum results

        Returns:
            List of high-conviction picks
        """
        top = await self.get_top_assets(category=category, limit=limit * 3)
        return RankingEngine.get_high_conviction_picks(top)[:limit]

    def _get_or_create_asset(
        self, symbol: str, asset_type: Optional[AssetType] = None
    ) -> Asset:
        """Look up or create an asset."""
        # Try to find in known assets
        asset = get_asset_by_symbol(symbol)
        if asset:
            return asset

        # Create custom asset
        if asset_type is None:
            # Guess type based on symbol characteristics
            if len(symbol) <= 5 and symbol.isupper():
                # Could be either - default to crypto for short symbols
                asset_type = AssetType.CRYPTO
            else:
                asset_type = AssetType.STOCK

        return create_custom_asset(
            symbol=symbol,
            name=symbol,  # Will be updated if we can fetch details
            asset_type=asset_type,
        )

    def get_summary(self, consensus: ConsensusScore) -> str:
        """Generate human-readable summary."""
        return InsightExtractor.generate_summary(consensus)

    def get_discord_embed_data(self, consensus: ConsensusScore) -> dict:
        """Generate Discord embed data."""
        return InsightExtractor.generate_discord_embed_data(consensus)

    @property
    def available_providers(self) -> list[str]:
        """Get list of configured provider names."""
        return [p.provider_name for p in self._providers]

    @property
    def is_initialized(self) -> bool:
        """Check if Oracle is initialized."""
        return self._initialized
