"""
Mode C: Solo-Valuation

User picks one model, runs it up to 5 times to test consistency.
Gets a bar chart showing distribution of estimates with mean/median marked.
"""

from dataclasses import dataclass

from llm_asset_oracle.engine.query_engine import QueryEngine, ProgressCallback
from llm_asset_oracle.modes.multi_valuation import parse_valuation, MULTI_VALUATION_PROMPT


@dataclass
class SoloEstimate:
    """Single run result."""

    run_number: int
    value_billions: float | None
    value_formatted: str
    reasoning: str
    success: bool
    error: str | None = None


@dataclass
class SoloValuationResult:
    """Aggregated results from repeated runs of one model."""

    model_name: str
    model_id: str
    asset_description: str
    target_time: str
    prompt_text: str
    num_runs: int
    estimates: list[SoloEstimate]
    valid_count: int
    median_billions: float
    mean_billions: float
    min_billions: float
    max_billions: float
    std_dev: float
    range_spread: float  # max - min as % of median


async def run_solo_valuation(
    engine: QueryEngine,
    model_id: str,
    asset_description: str,
    target_time: str,
    num_runs: int = 5,
    on_result: ProgressCallback | None = None,
) -> SoloValuationResult:
    """Run Mode C: Solo-Valuation analysis."""

    from llm_asset_oracle.models.registry import get_model_name
    model_name = get_model_name(model_id)

    prompt = MULTI_VALUATION_PROMPT.format(
        asset_description=asset_description,
        target_time=target_time,
    )

    raw_results = await engine.query_repeated(
        model_id=model_id,
        prompt=prompt,
        runs=num_runs,
        max_tokens=500,
        on_result=on_result,
    )

    estimates = []
    for r in raw_results:
        if r.success:
            value_b, formatted, reasoning = parse_valuation(r.content)
            estimates.append(SoloEstimate(
                run_number=r.run_index + 1,
                value_billions=value_b,
                value_formatted=formatted,
                reasoning=reasoning,
                success=value_b is not None,
            ))
        else:
            estimates.append(SoloEstimate(
                run_number=r.run_index + 1,
                value_billions=None,
                value_formatted="$?",
                reasoning="",
                success=False,
                error=r.error,
            ))

    # Calculate stats
    valid_values = [e.value_billions for e in estimates if e.value_billions is not None]
    valid_count = len(valid_values)

    if valid_values:
        sorted_vals = sorted(valid_values)
        median = sorted_vals[len(sorted_vals) // 2]
        mean = sum(valid_values) / len(valid_values)
        min_val = min(valid_values)
        max_val = max(valid_values)
        std_dev = (sum((v - mean) ** 2 for v in valid_values) / len(valid_values)) ** 0.5
        range_spread = ((max_val - min_val) / median * 100) if median > 0 else 0
    else:
        median = mean = min_val = max_val = std_dev = range_spread = 0

    return SoloValuationResult(
        model_name=model_name,
        model_id=model_id,
        asset_description=asset_description,
        target_time=target_time,
        prompt_text=prompt,
        num_runs=num_runs,
        estimates=estimates,
        valid_count=valid_count,
        median_billions=median,
        mean_billions=mean,
        min_billions=min_val,
        max_billions=max_val,
        std_dev=std_dev,
        range_spread=range_spread,
    )
