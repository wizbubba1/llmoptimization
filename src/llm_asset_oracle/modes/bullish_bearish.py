"""
Mode A: Bullish or Bearish

Queries all 18 models for a simple BULLISH/BEARISH sentiment on an asset
over a given time horizon. Results displayed as a pie chart.
"""

import re
from dataclasses import dataclass

from llm_asset_oracle.engine.query_engine import QueryEngine, QueryResult, ProgressCallback
from llm_asset_oracle.models.registry import ALL_MODEL_IDS


BULLISH_BEARISH_PROMPT = """Year is 2026. Consider the following asset: {asset_description}

Time horizon: {time_horizon}

Based on your analysis, are you BULLISH or BEARISH on this asset over the given time horizon?

IMPORTANT: End your response with a single line in this exact format:
SENTIMENT: [BULLISH or BEARISH]"""


@dataclass
class SentimentResult:
    """Parsed sentiment from a single model."""

    model_name: str
    model_id: str
    sentiment: str  # "BULLISH", "BEARISH", or "UNKNOWN"
    success: bool
    error: str | None = None


@dataclass
class BullishBearishResult:
    """Aggregated results from all models."""

    asset_description: str
    time_horizon: str
    results: list[SentimentResult]
    bullish_count: int
    bearish_count: int
    unknown_count: int
    total_models: int
    bullish_pct: float
    bearish_pct: float


def parse_sentiment(response: str) -> str:
    """Parse BULLISH or BEARISH from model response."""
    text = response.upper()

    # Look for explicit SENTIMENT: line
    match = re.search(r"SENTIMENT:\s*(BULLISH|BEARISH)", text)
    if match:
        return match.group(1)

    # Fallback: count occurrences
    bullish_count = text.count("BULLISH")
    bearish_count = text.count("BEARISH")

    if bullish_count > bearish_count:
        return "BULLISH"
    elif bearish_count > bullish_count:
        return "BEARISH"

    return "UNKNOWN"


async def run_bullish_bearish(
    engine: QueryEngine,
    asset_description: str,
    time_horizon: str,
    on_result: ProgressCallback | None = None,
) -> BullishBearishResult:
    """Run Mode A: Bullish or Bearish analysis."""

    prompt = BULLISH_BEARISH_PROMPT.format(
        asset_description=asset_description,
        time_horizon=time_horizon,
    )

    raw_results = await engine.query_multiple(
        model_ids=ALL_MODEL_IDS,
        prompt=prompt,
        max_tokens=300,
        on_result=on_result,
    )

    # Parse sentiments
    sentiments = []
    for r in raw_results:
        if r.success:
            sentiment = parse_sentiment(r.content)
            sentiments.append(SentimentResult(
                model_name=r.model_name,
                model_id=r.model_id,
                sentiment=sentiment,
                success=True,
            ))
        else:
            sentiments.append(SentimentResult(
                model_name=r.model_name,
                model_id=r.model_id,
                sentiment="UNKNOWN",
                success=False,
                error=r.error,
            ))

    bullish = sum(1 for s in sentiments if s.sentiment == "BULLISH")
    bearish = sum(1 for s in sentiments if s.sentiment == "BEARISH")
    unknown = sum(1 for s in sentiments if s.sentiment == "UNKNOWN")
    total = len(sentiments)
    valid = bullish + bearish

    return BullishBearishResult(
        asset_description=asset_description,
        time_horizon=time_horizon,
        results=sentiments,
        bullish_count=bullish,
        bearish_count=bearish,
        unknown_count=unknown,
        total_models=total,
        bullish_pct=(bullish / valid * 100) if valid > 0 else 0,
        bearish_pct=(bearish / valid * 100) if valid > 0 else 0,
    )
