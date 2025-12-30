"""Base classes for LLM providers."""

import asyncio
import json
import logging
import re
import time
from abc import ABC, abstractmethod
from typing import Optional

from llm_asset_oracle.core.models import Asset, LLMResponse, SentimentRating

logger = logging.getLogger(__name__)


class LLMProvider(ABC):
    """Abstract base class for LLM providers."""

    provider_name: str = "base"
    default_model: str = "unknown"

    def __init__(self, api_key: str, model: Optional[str] = None):
        """Initialize the provider with API credentials."""
        self.api_key = api_key
        self.model = model or self.default_model
        self._rate_limiter: Optional[asyncio.Semaphore] = None

    @abstractmethod
    async def query(self, prompt: str, system_prompt: Optional[str] = None) -> tuple[str, int]:
        """
        Send a query to the LLM and get a response.

        Args:
            prompt: The user prompt to send
            system_prompt: Optional system prompt for context

        Returns:
            Tuple of (response_text, tokens_used)
        """
        pass

    async def analyze_asset(self, asset: Asset, prompt_template: str) -> LLMResponse:
        """
        Analyze an asset using the standardized prompt template.

        Args:
            asset: The asset to analyze
            prompt_template: The formatted prompt template

        Returns:
            LLMResponse with structured rating
        """
        start_time = time.time()

        try:
            raw_response, tokens = await self.query(prompt_template)
            latency_ms = (time.time() - start_time) * 1000

            # Parse the structured response
            rating = self._parse_rating(raw_response)

            return LLMResponse(
                provider=self.provider_name,
                model=self.model,
                asset_symbol=asset.symbol,
                rating=rating,
                raw_response=raw_response,
                latency_ms=latency_ms,
                tokens_used=tokens,
            )

        except Exception as e:
            logger.error(f"Error analyzing asset {asset.symbol} with {self.provider_name}: {e}")
            raise

    def _parse_rating(self, response: str) -> SentimentRating:
        """Parse LLM response into structured SentimentRating."""
        # Try to extract JSON from the response
        json_match = re.search(r"\{[\s\S]*\}", response)

        if json_match:
            try:
                data = json.loads(json_match.group())
                return self._create_rating_from_dict(data)
            except json.JSONDecodeError:
                pass

        # Fallback: Parse structured text response
        return self._parse_text_rating(response)

    def _create_rating_from_dict(self, data: dict) -> SentimentRating:
        """Create SentimentRating from parsed JSON dict."""

        def get_score(keys: list[str], default: float = 5.0) -> float:
            """Get score from multiple possible key names."""
            for key in keys:
                if key in data:
                    val = data[key]
                    if isinstance(val, (int, float)):
                        return max(1, min(10, float(val)))
            return default

        def get_list(keys: list[str]) -> list[str]:
            """Get list from multiple possible key names."""
            for key in keys:
                if key in data and isinstance(data[key], list):
                    return [str(item) for item in data[key][:5]]
            return []

        return SentimentRating(
            overall_score=get_score(["overall_score", "overall", "rating", "score"]),
            bullish_score=get_score(["bullish_score", "bullish", "bull_score"]),
            risk_score=get_score(["risk_score", "risk", "risk_level"]),
            short_term_outlook=get_score(["short_term_outlook", "short_term", "st_outlook"]),
            medium_term_outlook=get_score(["medium_term_outlook", "medium_term", "mt_outlook"]),
            long_term_outlook=get_score(["long_term_outlook", "long_term", "lt_outlook"]),
            fundamentals_score=get_score(["fundamentals_score", "fundamentals", "fundamental"]),
            momentum_score=get_score(["momentum_score", "momentum", "technical"]),
            sentiment_score=get_score(["sentiment_score", "sentiment", "market_sentiment"]),
            key_bullish_factors=get_list(
                ["key_bullish_factors", "bullish_factors", "bull_factors", "positives"]
            ),
            key_bearish_factors=get_list(
                ["key_bearish_factors", "bearish_factors", "bear_factors", "negatives"]
            ),
            summary=data.get("summary", data.get("analysis", "Analysis completed.")),
        )

    def _parse_text_rating(self, response: str) -> SentimentRating:
        """Parse unstructured text response into rating (fallback)."""

        def extract_score(pattern: str, text: str, default: float = 5.0) -> float:
            """Extract a numerical score using regex pattern."""
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    score = float(match.group(1))
                    return max(1, min(10, score))
                except ValueError:
                    pass
            return default

        # Try to extract scores from text
        overall = extract_score(r"overall[:\s]+(\d+(?:\.\d+)?)", response)
        bullish = extract_score(r"bullish[:\s]+(\d+(?:\.\d+)?)", response)
        risk = extract_score(r"risk[:\s]+(\d+(?:\.\d+)?)", response)

        # Extract factors from bullet points or numbered lists
        bullish_factors = re.findall(r"(?:bullish|positive|pro)[^:]*:\s*([^\n]+)", response, re.I)
        bearish_factors = re.findall(r"(?:bearish|negative|con)[^:]*:\s*([^\n]+)", response, re.I)

        return SentimentRating(
            overall_score=overall,
            bullish_score=bullish,
            risk_score=risk,
            short_term_outlook=extract_score(r"short[- ]term[:\s]+(\d+(?:\.\d+)?)", response),
            medium_term_outlook=extract_score(r"medium[- ]term[:\s]+(\d+(?:\.\d+)?)", response),
            long_term_outlook=extract_score(r"long[- ]term[:\s]+(\d+(?:\.\d+)?)", response),
            fundamentals_score=extract_score(r"fundamental[s]?[:\s]+(\d+(?:\.\d+)?)", response),
            momentum_score=extract_score(r"momentum[:\s]+(\d+(?:\.\d+)?)", response),
            sentiment_score=extract_score(r"sentiment[:\s]+(\d+(?:\.\d+)?)", response),
            key_bullish_factors=bullish_factors[:5],
            key_bearish_factors=bearish_factors[:5],
            summary=response[:500] if len(response) > 500 else response,
        )


class LLMQueryEngine:
    """Engine for querying multiple LLM providers."""

    def __init__(self, providers: list[LLMProvider]):
        """Initialize with a list of LLM providers."""
        self.providers = providers
        self._semaphore = asyncio.Semaphore(5)  # Max concurrent queries

    async def query_all(
        self, asset: Asset, prompt_template: str
    ) -> list[LLMResponse]:
        """
        Query all providers for an asset analysis.

        Args:
            asset: The asset to analyze
            prompt_template: Formatted prompt template

        Returns:
            List of LLMResponse from each provider
        """
        tasks = []
        for provider in self.providers:
            task = self._query_with_semaphore(provider, asset, prompt_template)
            tasks.append(task)

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Filter out failed queries
        responses = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(
                    f"Provider {self.providers[i].provider_name} failed: {result}"
                )
            else:
                responses.append(result)

        return responses

    async def _query_with_semaphore(
        self, provider: LLMProvider, asset: Asset, prompt_template: str
    ) -> LLMResponse:
        """Query a provider with rate limiting."""
        async with self._semaphore:
            return await provider.analyze_asset(asset, prompt_template)

    async def query_subset(
        self, asset: Asset, prompt_template: str, count: int = 3
    ) -> list[LLMResponse]:
        """
        Query a subset of providers for faster results.

        Args:
            asset: The asset to analyze
            prompt_template: Formatted prompt template
            count: Number of providers to query

        Returns:
            List of LLMResponse from queried providers
        """
        providers_to_query = self.providers[:count]
        engine = LLMQueryEngine(providers_to_query)
        return await engine.query_all(asset, prompt_template)
