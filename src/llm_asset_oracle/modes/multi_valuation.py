"""
Mode B: Multi-Valuation

User picks up to 8 models, describes an asset, picks a target quarter/year.
Gets aggregated market cap estimates displayed as a bar chart.
"""

import re
from dataclasses import dataclass

from llm_asset_oracle.engine.query_engine import QueryEngine, QueryResult, ProgressCallback


MULTI_VALUATION_PROMPT = """Year is 2026. Consider {asset_description}

Target time: {target_time}

What is your best-estimate market cap (not FDV) for this asset at the target time? Do not use web search.

IMPORTANT: End your response with a single line in this exact format:
VERDICT: $[amount] - [one sentence reasoning]

Examples: VERDICT: $5B - Strong ecosystem growth expected
          VERDICT: $500M - Early stage with limited adoption"""


@dataclass
class ValuationEstimate:
    """Parsed valuation from a single model."""

    model_name: str
    model_id: str
    value_billions: float | None
    value_formatted: str
    reasoning: str
    success: bool
    error: str | None = None


@dataclass
class MultiValuationResult:
    """Aggregated results from selected models."""

    asset_description: str
    target_time: str
    prompt_text: str
    estimates: list[ValuationEstimate]
    valid_count: int
    failed_count: int
    median_billions: float
    mean_billions: float
    min_billions: float
    max_billions: float


def parse_valuation(response: str) -> tuple[float | None, str, str]:
    """
    Parse market cap value and reasoning from model response.

    Returns: (value_in_billions, formatted_value, reasoning)
    """
    text = response.strip()

    # Look for VERDICT line
    verdict_match = re.search(
        r"VERDICT:\s*\$?([\d,.]+)\s*(T|B|M|K|trillion|billion|million)?\s*[-–—]\s*(.*)",
        text,
        re.IGNORECASE,
    )

    if verdict_match:
        num_str = verdict_match.group(1).replace(",", "")
        unit = (verdict_match.group(2) or "B").upper()[0]
        reasoning = verdict_match.group(3).strip()

        try:
            value = float(num_str)

            if unit == "T":
                value_b = value * 1000
            elif unit == "B":
                value_b = value
            elif unit == "M":
                value_b = value / 1000
            elif unit == "K":
                value_b = value / 1_000_000
            else:
                value_b = value

            if value_b >= 1:
                formatted = f"${value_b:.1f}B"
            elif value_b >= 0.001:
                formatted = f"${value_b * 1000:.0f}M"
            else:
                formatted = f"${value_b * 1_000_000:.0f}K"

            return value_b, formatted, reasoning
        except ValueError:
            pass

    # Fallback: look for dollar amounts anywhere
    amount_match = re.search(r"\$([\d,.]+)\s*(T|B|M|trillion|billion|million)", text, re.IGNORECASE)
    if amount_match:
        try:
            value = float(amount_match.group(1).replace(",", ""))
            unit = amount_match.group(2).upper()[0]

            if unit == "T":
                value_b = value * 1000
            elif unit == "B":
                value_b = value
            else:
                value_b = value / 1000

            if value_b >= 1:
                formatted = f"${value_b:.1f}B"
            else:
                formatted = f"${value_b * 1000:.0f}M"

            return value_b, formatted, ""
        except ValueError:
            pass

    return None, "$?", ""


async def run_multi_valuation(
    engine: QueryEngine,
    model_ids: list[str],
    asset_description: str,
    target_time: str,
    on_result: ProgressCallback | None = None,
) -> MultiValuationResult:
    """Run Mode B: Multi-Valuation analysis."""

    prompt = MULTI_VALUATION_PROMPT.format(
        asset_description=asset_description,
        target_time=target_time,
    )

    raw_results = await engine.query_multiple(
        model_ids=model_ids,
        prompt=prompt,
        max_tokens=500,
        on_result=on_result,
    )

    estimates = []
    for r in raw_results:
        if r.success:
            value_b, formatted, reasoning = parse_valuation(r.content)
            estimates.append(ValuationEstimate(
                model_name=r.model_name,
                model_id=r.model_id,
                value_billions=value_b,
                value_formatted=formatted,
                reasoning=reasoning,
                success=value_b is not None,
            ))
        else:
            estimates.append(ValuationEstimate(
                model_name=r.model_name,
                model_id=r.model_id,
                value_billions=None,
                value_formatted="$?",
                reasoning="",
                success=False,
                error=r.error,
            ))

    # Calculate stats
    valid_values = [e.value_billions for e in estimates if e.value_billions is not None]
    valid_count = len(valid_values)
    failed_count = len(estimates) - valid_count

    if valid_values:
        sorted_vals = sorted(valid_values)
        median = sorted_vals[len(sorted_vals) // 2]
        mean = sum(valid_values) / len(valid_values)
        min_val = min(valid_values)
        max_val = max(valid_values)
    else:
        median = mean = min_val = max_val = 0

    return MultiValuationResult(
        asset_description=asset_description,
        target_time=target_time,
        prompt_text=prompt,
        estimates=estimates,
        valid_count=valid_count,
        failed_count=failed_count,
        median_billions=median,
        mean_billions=mean,
        min_billions=min_val,
        max_billions=max_val,
    )
