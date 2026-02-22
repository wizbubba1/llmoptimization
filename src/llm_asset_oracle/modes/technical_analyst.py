"""
Mode D: Technical Analyst

User picks up to 8 vision-capable models, uploads a candlestick chart
screenshot + timeframe. Each model gives a LONG or SHORT recommendation.
Results displayed as a bar chart.
"""

import re
from dataclasses import dataclass

from llm_asset_oracle.engine.query_engine import QueryEngine, ProgressCallback


TECHNICAL_ANALYST_PROMPT = """You are a technical analyst. Analyze this {timeframe} candlestick chart.

Based purely on technical analysis (price action, support/resistance, trend, patterns, volume if visible), would you go LONG or SHORT on this asset?

IMPORTANT: End your response with a single line in this exact format:
POSITION: [LONG or SHORT]"""


@dataclass
class TechnicalResult:
    """Parsed technical analysis from a single model."""

    model_name: str
    model_id: str
    position: str  # "LONG", "SHORT", or "UNKNOWN"
    success: bool
    error: str | None = None


@dataclass
class TechnicalAnalystResult:
    """Aggregated results from all selected models."""

    timeframe: str
    results: list[TechnicalResult]
    long_count: int
    short_count: int
    unknown_count: int
    total_models: int
    long_pct: float
    short_pct: float


def parse_position(response: str) -> str:
    """Parse LONG or SHORT from model response."""
    text = response.upper()

    # Look for explicit POSITION: line
    match = re.search(r"POSITION:\s*(LONG|SHORT)", text)
    if match:
        return match.group(1)

    # Fallback: look for final mention
    long_idx = text.rfind("LONG")
    short_idx = text.rfind("SHORT")

    if long_idx > short_idx:
        return "LONG"
    elif short_idx > long_idx:
        return "SHORT"

    return "UNKNOWN"


async def run_technical_analyst(
    engine: QueryEngine,
    model_ids: list[str],
    image_base64: str,
    timeframe: str,
    image_media_type: str = "image/png",
    on_result: ProgressCallback | None = None,
) -> TechnicalAnalystResult:
    """Run Mode D: Technical Analyst analysis."""

    prompt = TECHNICAL_ANALYST_PROMPT.format(timeframe=timeframe)

    raw_results = await engine.query_multiple_vision(
        model_ids=model_ids,
        prompt=prompt,
        image_base64=image_base64,
        image_media_type=image_media_type,
        max_tokens=500,
        on_result=on_result,
    )

    results = []
    for r in raw_results:
        if r.success:
            position = parse_position(r.content)
            results.append(TechnicalResult(
                model_name=r.model_name,
                model_id=r.model_id,
                position=position,
                success=True,
            ))
        else:
            results.append(TechnicalResult(
                model_name=r.model_name,
                model_id=r.model_id,
                position="UNKNOWN",
                success=False,
                error=r.error,
            ))

    longs = sum(1 for r in results if r.position == "LONG")
    shorts = sum(1 for r in results if r.position == "SHORT")
    unknown = sum(1 for r in results if r.position == "UNKNOWN")
    valid = longs + shorts

    return TechnicalAnalystResult(
        timeframe=timeframe,
        results=results,
        long_count=longs,
        short_count=shorts,
        unknown_count=unknown,
        total_models=len(results),
        long_pct=(longs / valid * 100) if valid > 0 else 0,
        short_pct=(shorts / valid * 100) if valid > 0 else 0,
    )
