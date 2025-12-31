"""
Valuation Statistics Engine

Calculates statistical metrics from multiple LLM market cap estimates:
- Mean, Median, Mode
- Standard Deviation, Variance
- Confidence Intervals
- Outlier Detection
- Consensus Strength
"""

from dataclasses import dataclass, field
from typing import Optional
import math
from statistics import mean, median, stdev, variance

from llm_asset_oracle.valuation.parser import MarketCapResult


@dataclass
class ValuationStatistics:
    """Complete statistical analysis of valuation estimates."""

    # Token info
    token_name: str
    ticker: str
    target_year: int

    # Raw data
    estimates: list[MarketCapResult] = field(default_factory=list)
    valid_estimates: list[float] = field(default_factory=list)

    # Central tendency (all in billions)
    mean_value: float = 0.0
    median_value: float = 0.0
    mode_value: Optional[float] = None

    # Spread
    std_dev: float = 0.0
    variance: float = 0.0
    min_value: float = 0.0
    max_value: float = 0.0
    range_value: float = 0.0

    # Quartiles
    q1: float = 0.0  # 25th percentile
    q3: float = 0.0  # 75th percentile
    iqr: float = 0.0  # Interquartile range

    # Confidence
    confidence_interval_low: float = 0.0  # 95% CI lower bound
    confidence_interval_high: float = 0.0  # 95% CI upper bound
    consensus_strength: float = 0.0  # 0-100%

    # Outliers
    outliers: list[MarketCapResult] = field(default_factory=list)
    outlier_count: int = 0

    # Counts
    total_models: int = 0
    successful_parses: int = 0
    failed_parses: int = 0

    # Interpretation
    consensus_label: str = ""
    verdict: str = ""

    @property
    def mean_formatted(self) -> str:
        return _format_billions(self.mean_value)

    @property
    def median_formatted(self) -> str:
        return _format_billions(self.median_value)

    @property
    def range_formatted(self) -> str:
        return f"{_format_billions(self.min_value)} - {_format_billions(self.max_value)}"

    @property
    def iqr_formatted(self) -> str:
        return f"{_format_billions(self.q1)} - {_format_billions(self.q3)}"

    @property
    def ci_formatted(self) -> str:
        return f"{_format_billions(self.confidence_interval_low)} - {_format_billions(self.confidence_interval_high)}"


def _format_billions(value: float) -> str:
    """Format value in billions to readable string."""
    if value <= 0:
        return "$0"
    if value >= 1000:
        return f"${value / 1000:.2f}T"
    elif value >= 1:
        return f"${value:.1f}B"
    else:
        return f"${value * 1000:.0f}M"


def calculate_valuation_stats(
    token_name: str,
    ticker: str,
    target_year: int,
    estimates: list[MarketCapResult],
) -> ValuationStatistics:
    """
    Calculate comprehensive statistics from market cap estimates.

    Args:
        token_name: Name of the token
        ticker: Ticker symbol
        target_year: Target year for valuation
        estimates: List of MarketCapResult from each model

    Returns:
        ValuationStatistics with all metrics calculated
    """
    stats = ValuationStatistics(
        token_name=token_name,
        ticker=ticker,
        target_year=target_year,
        estimates=estimates,
        total_models=len(estimates),
    )

    # Extract valid values
    valid_values = []
    for est in estimates:
        if est.value_billions is not None and est.value_billions > 0:
            valid_values.append(est.value_billions)
            stats.successful_parses += 1
        else:
            stats.failed_parses += 1

    stats.valid_estimates = valid_values

    if len(valid_values) == 0:
        stats.verdict = "No valid estimates could be parsed from model responses."
        stats.consensus_label = "No Data"
        return stats

    if len(valid_values) == 1:
        # Only one valid estimate
        val = valid_values[0]
        stats.mean_value = val
        stats.median_value = val
        stats.min_value = val
        stats.max_value = val
        stats.consensus_label = "Single Estimate"
        stats.verdict = f"Only one model provided a parseable estimate: {_format_billions(val)}"
        return stats

    # Sort for percentile calculations
    sorted_values = sorted(valid_values)
    n = len(sorted_values)

    # Central tendency
    stats.mean_value = mean(valid_values)
    stats.median_value = median(valid_values)

    # Spread
    stats.min_value = min(valid_values)
    stats.max_value = max(valid_values)
    stats.range_value = stats.max_value - stats.min_value

    if n >= 2:
        stats.std_dev = stdev(valid_values)
        stats.variance = variance(valid_values)

    # Quartiles
    stats.q1 = _percentile(sorted_values, 25)
    stats.q3 = _percentile(sorted_values, 75)
    stats.iqr = stats.q3 - stats.q1

    # 95% Confidence Interval (using t-distribution approximation)
    if n >= 2 and stats.std_dev > 0:
        # Standard error
        se = stats.std_dev / math.sqrt(n)
        # t-value for 95% CI (approximation for small samples)
        t_value = 2.0 if n > 30 else 2.5 if n > 10 else 3.0
        margin = t_value * se
        stats.confidence_interval_low = max(0, stats.mean_value - margin)
        stats.confidence_interval_high = stats.mean_value + margin
    else:
        stats.confidence_interval_low = stats.mean_value
        stats.confidence_interval_high = stats.mean_value

    # Outlier detection using IQR method
    lower_fence = stats.q1 - 1.5 * stats.iqr
    upper_fence = stats.q3 + 1.5 * stats.iqr

    for est in estimates:
        if est.value_billions is not None:
            if est.value_billions < lower_fence or est.value_billions > upper_fence:
                stats.outliers.append(est)

    stats.outlier_count = len(stats.outliers)

    # Consensus strength calculation
    # Based on coefficient of variation (lower = more consensus)
    if stats.mean_value > 0:
        cv = stats.std_dev / stats.mean_value  # Coefficient of variation

        # Convert CV to consensus percentage
        # CV of 0 = 100% consensus, CV of 1+ = low consensus
        if cv <= 0.1:
            stats.consensus_strength = 95
        elif cv <= 0.2:
            stats.consensus_strength = 85
        elif cv <= 0.3:
            stats.consensus_strength = 75
        elif cv <= 0.5:
            stats.consensus_strength = 60
        elif cv <= 0.75:
            stats.consensus_strength = 45
        elif cv <= 1.0:
            stats.consensus_strength = 30
        else:
            stats.consensus_strength = max(10, 30 - (cv - 1) * 20)

    # Consensus label
    if stats.consensus_strength >= 80:
        stats.consensus_label = "Very High"
    elif stats.consensus_strength >= 65:
        stats.consensus_label = "High"
    elif stats.consensus_strength >= 50:
        stats.consensus_label = "Moderate"
    elif stats.consensus_strength >= 35:
        stats.consensus_label = "Low"
    else:
        stats.consensus_label = "Very Low"

    # Generate verdict
    stats.verdict = _generate_verdict(stats)

    return stats


def _percentile(sorted_values: list[float], p: float) -> float:
    """Calculate percentile from sorted values."""
    if not sorted_values:
        return 0.0

    n = len(sorted_values)
    k = (n - 1) * p / 100
    f = math.floor(k)
    c = math.ceil(k)

    if f == c:
        return sorted_values[int(k)]

    return sorted_values[int(f)] * (c - k) + sorted_values[int(c)] * (k - f)


def _generate_verdict(stats: ValuationStatistics) -> str:
    """Generate human-readable verdict."""
    lines = []

    # Main estimate
    lines.append(
        f"LLM consensus suggests a market cap of **{stats.median_formatted}** "
        f"(median) to **{stats.mean_formatted}** (mean) for {stats.token_name} by {stats.target_year}."
    )

    # Consensus strength
    if stats.consensus_strength >= 70:
        lines.append(
            f"Models show **{stats.consensus_label.lower()} agreement** "
            f"({stats.consensus_strength:.0f}% consensus) - estimates are fairly clustered."
        )
    elif stats.consensus_strength >= 50:
        lines.append(
            f"Models show **{stats.consensus_label.lower()} agreement** "
            f"({stats.consensus_strength:.0f}% consensus) - some variation in estimates."
        )
    else:
        lines.append(
            f"Models show **{stats.consensus_label.lower()} agreement** "
            f"({stats.consensus_strength:.0f}% consensus) - estimates are scattered, treat with caution."
        )

    # Range info
    if stats.range_value > 0:
        range_ratio = stats.max_value / stats.min_value if stats.min_value > 0 else float('inf')
        if range_ratio <= 2:
            lines.append(f"Tight range: {stats.range_formatted}")
        elif range_ratio <= 5:
            lines.append(f"Moderate range: {stats.range_formatted}")
        else:
            lines.append(f"Wide range: {stats.range_formatted} - significant disagreement among models.")

    # Outliers
    if stats.outlier_count > 0:
        outlier_names = [o.model_name for o in stats.outliers]
        lines.append(f"Outliers detected from: {', '.join(outlier_names)}")

    return "\n".join(lines)


def format_stats_table(stats: ValuationStatistics) -> str:
    """Format statistics as ASCII table for Discord."""
    lines = [
        "```",
        f"📊 VALUATION STATISTICS: {stats.token_name} ({stats.ticker})",
        f"   Target Year: {stats.target_year}",
        "─" * 45,
        f"  Mean:         {stats.mean_formatted:>12}",
        f"  Median:       {stats.median_formatted:>12}",
        f"  Std Dev:      {_format_billions(stats.std_dev):>12}",
        "",
        f"  Range:        {stats.range_formatted}",
        f"  IQR (25-75%): {stats.iqr_formatted}",
        f"  95% CI:       {stats.ci_formatted}",
        "",
        f"  Consensus:    {stats.consensus_strength:.0f}% ({stats.consensus_label})",
        f"  Valid/Total:  {stats.successful_parses}/{stats.total_models} models",
        "```",
    ]
    return "\n".join(lines)
