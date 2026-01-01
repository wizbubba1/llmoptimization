"""
Advanced Data Science Analysis for Valuation Data

Sophisticated statistical analysis to derive meaningful insights:
- Outlier detection and removal (IQR method)
- Trimmed/Winsorized statistics
- Cluster detection (valuation camps)
- Model reliability scoring
- Refined consensus calculation
- Actionable verdict generation
"""

import math
from dataclasses import dataclass, field
from typing import Optional
from collections import Counter

from llm_asset_oracle.valuation.parser import MarketCapResult


@dataclass
class OutlierAnalysis:
    """Results of outlier detection."""

    outlier_models: list[str]  # Names of outlier models
    outlier_values: list[float]  # Their values
    clean_values: list[float]  # Values after outlier removal
    clean_estimates: list[MarketCapResult]  # Estimates after outlier removal
    outlier_method: str  # Method used (IQR, etc.)
    lower_fence: float
    upper_fence: float


@dataclass
class ClusterAnalysis:
    """Results of cluster/camp detection."""

    num_clusters: int  # 1 = consensus, 2+ = divided opinion
    clusters: list[dict]  # Each cluster: {center, count, models, range}
    is_divided: bool  # True if clear camps exist
    dominant_cluster: Optional[dict]  # Largest cluster if exists
    division_description: str  # Human-readable description


@dataclass
class RefinedStatistics:
    """Refined statistics after data cleaning."""

    # Raw stats (before cleaning)
    raw_mean: float
    raw_median: float
    raw_std: float
    raw_count: int

    # Cleaned stats (after outlier removal)
    clean_mean: float
    clean_median: float
    clean_std: float
    clean_count: int

    # Trimmed stats (10% trim)
    trimmed_mean: float

    # Robust stats
    mad: float  # Median Absolute Deviation
    robust_cv: float  # Coefficient of variation using MAD

    # Consensus metrics (the 4 key metrics)
    raw_consensus: float  # % within 25% of median (all models)
    refined_consensus: float  # % within 25% of median (after outlier removal)
    tight_band_consensus: float  # % within 10% of median (stricter)
    consensus_grade: str  # A/B/C/D grade based on metrics
    consensus_improvement: float  # How much it improved after cleaning


@dataclass
class ModelReliability:
    """Reliability score for each model."""

    model_name: str
    estimate: float
    deviation_from_median: float  # Absolute
    deviation_pct: float  # Percentage
    reliability_score: float  # 0-100, higher = more reliable/aligned
    tier: str  # "core", "moderate", "outlier"


@dataclass
class AdvancedAnalysis:
    """Complete advanced analysis results."""

    outliers: OutlierAnalysis
    clusters: ClusterAnalysis
    refined_stats: RefinedStatistics
    model_reliability: list[ModelReliability]

    # Final verdict components
    confidence_level: str  # "high", "moderate", "low", "very_low"
    best_estimate: float  # Our best single number
    estimate_range: tuple[float, float]  # Credible range
    verdict_summary: str  # One-line summary
    detailed_verdict: str  # Full analysis text


def detect_outliers_iqr(values: list[float], multiplier: float = 1.5) -> OutlierAnalysis:
    """
    Detect outliers using IQR (Interquartile Range) method.

    Outliers are values below Q1 - 1.5*IQR or above Q3 + 1.5*IQR
    """
    if len(values) < 4:
        return OutlierAnalysis(
            outlier_models=[],
            outlier_values=[],
            clean_values=values,
            clean_estimates=[],
            outlier_method="IQR (insufficient data)",
            lower_fence=0,
            upper_fence=float('inf'),
        )

    sorted_vals = sorted(values)
    n = len(sorted_vals)

    q1_idx = n // 4
    q3_idx = (3 * n) // 4

    q1 = sorted_vals[q1_idx]
    q3 = sorted_vals[q3_idx]
    iqr = q3 - q1

    lower_fence = q1 - multiplier * iqr
    upper_fence = q3 + multiplier * iqr

    outlier_values = [v for v in values if v < lower_fence or v > upper_fence]
    clean_values = [v for v in values if lower_fence <= v <= upper_fence]

    return OutlierAnalysis(
        outlier_models=[],  # Will be filled in later
        outlier_values=outlier_values,
        clean_values=clean_values,
        clean_estimates=[],
        outlier_method=f"IQR (x{multiplier})",
        lower_fence=max(0, lower_fence),
        upper_fence=upper_fence,
    )


def detect_clusters(values: list[float], estimates: list[MarketCapResult]) -> ClusterAnalysis:
    """
    Detect if models cluster into distinct valuation "camps".

    Uses a simple gap-based clustering approach:
    If there's a gap > 50% of the median between groups, they're separate camps.
    """
    if len(values) < 3:
        return ClusterAnalysis(
            num_clusters=1,
            clusters=[],
            is_divided=False,
            dominant_cluster=None,
            division_description="Insufficient data for cluster analysis",
        )

    sorted_pairs = sorted(zip(values, estimates), key=lambda x: x[0])
    sorted_vals = [p[0] for p in sorted_pairs]
    sorted_ests = [p[1] for p in sorted_pairs]

    median = sorted_vals[len(sorted_vals) // 2]
    gap_threshold = median * 0.4  # 40% of median is a significant gap

    # Find gaps
    clusters = []
    current_cluster = {
        'values': [sorted_vals[0]],
        'models': [sorted_ests[0].model_name],
        'estimates': [sorted_ests[0]],
    }

    for i in range(1, len(sorted_vals)):
        gap = sorted_vals[i] - sorted_vals[i-1]

        if gap > gap_threshold:
            # New cluster
            clusters.append(current_cluster)
            current_cluster = {
                'values': [sorted_vals[i]],
                'models': [sorted_ests[i].model_name],
                'estimates': [sorted_ests[i]],
            }
        else:
            current_cluster['values'].append(sorted_vals[i])
            current_cluster['models'].append(sorted_ests[i].model_name)
            current_cluster['estimates'].append(sorted_ests[i])

    clusters.append(current_cluster)

    # Enrich cluster data
    enriched_clusters = []
    for c in clusters:
        vals = c['values']
        enriched_clusters.append({
            'center': sum(vals) / len(vals),
            'median': sorted(vals)[len(vals)//2],
            'count': len(vals),
            'models': c['models'],
            'range': (min(vals), max(vals)),
            'pct_of_total': len(vals) / len(values) * 100,
        })

    # Sort by size
    enriched_clusters.sort(key=lambda x: x['count'], reverse=True)

    # Determine if truly divided
    is_divided = len(enriched_clusters) >= 2 and enriched_clusters[1]['count'] >= 2

    # Build description
    if len(enriched_clusters) == 1:
        description = f"Models are unified around ${enriched_clusters[0]['center']:.1f}B"
    elif is_divided:
        camps = []
        for i, c in enumerate(enriched_clusters[:3]):  # Top 3 clusters
            camps.append(f"Camp {i+1}: {c['count']} models @ ${c['center']:.1f}B")
        description = "Divided opinion: " + " | ".join(camps)
    else:
        description = f"Mostly unified with {len(enriched_clusters)-1} outlier(s)"

    return ClusterAnalysis(
        num_clusters=len(enriched_clusters),
        clusters=enriched_clusters,
        is_divided=is_divided,
        dominant_cluster=enriched_clusters[0] if enriched_clusters else None,
        division_description=description,
    )


def calculate_trimmed_mean(values: list[float], trim_pct: float = 0.1) -> float:
    """Calculate trimmed mean (remove top and bottom X%)."""
    if len(values) < 3:
        return sum(values) / len(values) if values else 0

    sorted_vals = sorted(values)
    trim_count = max(1, int(len(sorted_vals) * trim_pct))

    trimmed = sorted_vals[trim_count:-trim_count] if trim_count < len(sorted_vals) // 2 else sorted_vals

    return sum(trimmed) / len(trimmed) if trimmed else 0


def calculate_mad(values: list[float]) -> float:
    """Calculate Median Absolute Deviation (robust spread measure)."""
    if not values:
        return 0

    median = sorted(values)[len(values) // 2]
    deviations = [abs(v - median) for v in values]
    mad = sorted(deviations)[len(deviations) // 2]

    return mad


def calculate_consensus_score(values: list[float], median: float) -> float:
    """
    Calculate consensus score (0-100).

    Based on what % of estimates fall within 25% of the median.
    """
    if not values or median == 0:
        return 0

    threshold = median * 0.25
    within_range = sum(1 for v in values if abs(v - median) <= threshold)

    return (within_range / len(values)) * 100


def calculate_tight_band_consensus(values: list[float], median: float) -> float:
    """
    Calculate tight band consensus (0-100).

    Stricter metric: % of estimates within ±10% of median.
    This shows how many models are in very close agreement.
    """
    if not values or median == 0:
        return 0

    threshold = median * 0.10  # ±10%
    within_range = sum(1 for v in values if abs(v - median) <= threshold)

    return (within_range / len(values)) * 100


def calculate_consensus_grade(
    raw_consensus: float,
    refined_consensus: float,
    tight_band: float,
    is_divided: bool,
) -> str:
    """
    Calculate overall consensus grade (A/B/C/D).

    Grading criteria:
    - A: Strong consensus (refined ≥70%, tight ≥40%, not divided)
    - B: Good consensus (refined ≥55%, tight ≥25%)
    - C: Moderate consensus (refined ≥40%, OR tight ≥15%)
    - D: Weak/No consensus (below thresholds or divided camps)
    """
    # Heavily divided opinion is automatic D
    if is_divided and refined_consensus < 50:
        return "D"

    # A grade: Strong agreement across all metrics
    if refined_consensus >= 70 and tight_band >= 40 and not is_divided:
        return "A"

    # B grade: Good agreement
    if refined_consensus >= 55 and tight_band >= 25:
        return "B"

    # C grade: Moderate agreement
    if refined_consensus >= 40 or tight_band >= 15:
        return "C"

    # D grade: Weak consensus
    return "D"


def score_model_reliability(
    estimates: list[MarketCapResult],
    clean_median: float,
) -> list[ModelReliability]:
    """Score each model's reliability based on alignment with consensus."""

    results = []

    for est in estimates:
        if est.value_billions is None or est.value_billions <= 0:
            continue

        deviation = abs(est.value_billions - clean_median)
        deviation_pct = (deviation / clean_median * 100) if clean_median > 0 else 100

        # Score: 100 at median, decreasing as you deviate
        # -20 points per 10% deviation, floor at 0
        score = max(0, 100 - (deviation_pct * 2))

        # Tier assignment
        if deviation_pct <= 15:
            tier = "core"
        elif deviation_pct <= 35:
            tier = "moderate"
        else:
            tier = "outlier"

        results.append(ModelReliability(
            model_name=est.model_name,
            estimate=est.value_billions,
            deviation_from_median=deviation,
            deviation_pct=deviation_pct,
            reliability_score=score,
            tier=tier,
        ))

    # Sort by reliability score
    results.sort(key=lambda x: x.reliability_score, reverse=True)

    return results


def generate_verdict(
    refined_stats: RefinedStatistics,
    clusters: ClusterAnalysis,
    model_reliability: list[ModelReliability],
    outliers: OutlierAnalysis,
) -> tuple[str, float, tuple[float, float], str, str]:
    """
    Generate the final verdict based on all analysis.

    Returns: (confidence_level, best_estimate, range, summary, detailed)
    """

    # Determine confidence level
    consensus = refined_stats.refined_consensus
    cv = refined_stats.robust_cv

    if consensus >= 70 and not clusters.is_divided:
        confidence_level = "high"
    elif consensus >= 50 or (clusters.dominant_cluster and clusters.dominant_cluster['pct_of_total'] >= 60):
        confidence_level = "moderate"
    elif consensus >= 30:
        confidence_level = "low"
    else:
        confidence_level = "very_low"

    # Best estimate: Use cleaned median (most robust)
    best_estimate = refined_stats.clean_median

    # Range: Use IQR of clean data
    clean_sorted = sorted(outliers.clean_values) if outliers.clean_values else [best_estimate]
    if len(clean_sorted) >= 4:
        q1 = clean_sorted[len(clean_sorted) // 4]
        q3 = clean_sorted[(3 * len(clean_sorted)) // 4]
    else:
        q1 = clean_sorted[0] if clean_sorted else best_estimate
        q3 = clean_sorted[-1] if clean_sorted else best_estimate

    estimate_range = (q1, q3)

    # Count tiers
    core_count = sum(1 for m in model_reliability if m.tier == "core")
    total_count = len(model_reliability)

    # Build summary
    if confidence_level == "high":
        summary = f"Strong consensus at ${best_estimate:.1f}B ({core_count}/{total_count} models aligned)"
    elif confidence_level == "moderate":
        if clusters.is_divided:
            summary = f"Divided opinion but dominant view: ${best_estimate:.1f}B"
        else:
            summary = f"Moderate consensus at ${best_estimate:.1f}B (some divergence)"
    elif confidence_level == "low":
        summary = f"Weak consensus around ${best_estimate:.1f}B (high uncertainty)"
    else:
        summary = f"No clear consensus - estimates range widely (${q1:.1f}B - ${q3:.1f}B)"

    # Build detailed verdict
    detailed_parts = []

    # Outlier info
    if outliers.outlier_values:
        detailed_parts.append(
            f"**Data Cleaning:** Removed {len(outliers.outlier_values)} outlier(s) "
            f"outside ${outliers.lower_fence:.1f}B - ${outliers.upper_fence:.1f}B range"
        )

    # Consensus improvement
    if refined_stats.consensus_improvement > 5:
        detailed_parts.append(
            f"**Consensus Improved:** {refined_stats.raw_consensus:.0f}% → "
            f"{refined_stats.refined_consensus:.0f}% after cleaning"
        )

    # Cluster info
    if clusters.is_divided:
        detailed_parts.append(f"**Valuation Camps:** {clusters.division_description}")

    # Core models
    core_models = [m for m in model_reliability if m.tier == "core"]
    if core_models:
        core_names = ", ".join([m.model_name for m in core_models[:5]])
        detailed_parts.append(f"**Core Agreement ({core_count} models):** {core_names}")

    # Statistics summary
    detailed_parts.append(
        f"**Refined Stats:** Median ${refined_stats.clean_median:.1f}B | "
        f"Trimmed Mean ${refined_stats.trimmed_mean:.1f}B | "
        f"MAD ${refined_stats.mad:.1f}B"
    )

    detailed = "\n".join(detailed_parts)

    return confidence_level, best_estimate, estimate_range, summary, detailed


def run_advanced_analysis(estimates: list[MarketCapResult]) -> AdvancedAnalysis:
    """
    Run complete advanced analysis on valuation estimates.

    This is the main entry point.
    """

    # Filter valid estimates
    valid_estimates = [e for e in estimates if e.value_billions is not None and e.value_billions > 0]
    values = [e.value_billions for e in valid_estimates]

    if len(values) < 2:
        # Not enough data
        return AdvancedAnalysis(
            outliers=OutlierAnalysis([], [], values, valid_estimates, "N/A", 0, 0),
            clusters=ClusterAnalysis(0, [], False, None, "Insufficient data"),
            refined_stats=RefinedStatistics(
                raw_mean=0, raw_median=0, raw_std=0, raw_count=0,
                clean_mean=0, clean_median=0, clean_std=0, clean_count=0,
                trimmed_mean=0, mad=0, robust_cv=0,
                raw_consensus=0, refined_consensus=0, tight_band_consensus=0,
                consensus_grade="D", consensus_improvement=0,
            ),
            model_reliability=[],
            confidence_level="very_low",
            best_estimate=values[0] if values else 0,
            estimate_range=(0, 0),
            verdict_summary="Insufficient data for analysis",
            detailed_verdict="Need at least 2 valid estimates for analysis",
        )

    # 1. Calculate raw statistics
    raw_mean = sum(values) / len(values)
    raw_sorted = sorted(values)
    raw_median = raw_sorted[len(raw_sorted) // 2]
    raw_std = (sum((v - raw_mean) ** 2 for v in values) / len(values)) ** 0.5
    raw_consensus = calculate_consensus_score(values, raw_median)

    # 2. Detect outliers
    outliers = detect_outliers_iqr(values)

    # Fill in model names for outliers
    outlier_models = []
    clean_estimates = []
    for est in valid_estimates:
        if est.value_billions in outliers.outlier_values:
            outlier_models.append(est.model_name)
        else:
            clean_estimates.append(est)
    outliers.outlier_models = outlier_models
    outliers.clean_estimates = clean_estimates

    # 3. Calculate cleaned statistics
    clean_values = outliers.clean_values
    if clean_values:
        clean_mean = sum(clean_values) / len(clean_values)
        clean_sorted = sorted(clean_values)
        clean_median = clean_sorted[len(clean_sorted) // 2]
        clean_std = (sum((v - clean_mean) ** 2 for v in clean_values) / len(clean_values)) ** 0.5
    else:
        clean_mean = raw_mean
        clean_median = raw_median
        clean_std = raw_std
        clean_values = values

    # 4. Trimmed mean and robust stats
    trimmed_mean = calculate_trimmed_mean(values)
    mad = calculate_mad(clean_values)
    robust_cv = (mad / clean_median * 100) if clean_median > 0 else 100

    # 5. Refined consensus
    refined_consensus = calculate_consensus_score(clean_values, clean_median)
    consensus_improvement = refined_consensus - raw_consensus

    # 6. Cluster analysis (needed for grade calculation)
    clusters = detect_clusters(values, valid_estimates)

    # 7. Tight band consensus and grade
    tight_band_consensus = calculate_tight_band_consensus(clean_values, clean_median)
    consensus_grade = calculate_consensus_grade(
        raw_consensus=raw_consensus,
        refined_consensus=refined_consensus,
        tight_band=tight_band_consensus,
        is_divided=clusters.is_divided,
    )

    refined_stats = RefinedStatistics(
        raw_mean=raw_mean,
        raw_median=raw_median,
        raw_std=raw_std,
        raw_count=len(values),
        clean_mean=clean_mean,
        clean_median=clean_median,
        clean_std=clean_std,
        clean_count=len(clean_values),
        trimmed_mean=trimmed_mean,
        mad=mad,
        robust_cv=robust_cv,
        raw_consensus=raw_consensus,
        refined_consensus=refined_consensus,
        tight_band_consensus=tight_band_consensus,
        consensus_grade=consensus_grade,
        consensus_improvement=consensus_improvement,
    )

    # 8. Model reliability scoring
    model_reliability = score_model_reliability(valid_estimates, clean_median)

    # 9. Generate verdict
    confidence_level, best_estimate, estimate_range, summary, detailed = generate_verdict(
        refined_stats, clusters, model_reliability, outliers
    )

    return AdvancedAnalysis(
        outliers=outliers,
        clusters=clusters,
        refined_stats=refined_stats,
        model_reliability=model_reliability,
        confidence_level=confidence_level,
        best_estimate=best_estimate,
        estimate_range=estimate_range,
        verdict_summary=summary,
        detailed_verdict=detailed,
    )


def format_advanced_analysis(analysis: AdvancedAnalysis) -> str:
    """Format advanced analysis for display."""

    lines = []

    # Confidence badge
    confidence_emoji = {
        "high": "🟢",
        "moderate": "🟡",
        "low": "🟠",
        "very_low": "🔴",
    }
    emoji = confidence_emoji.get(analysis.confidence_level, "⚪")

    lines.append(f"{emoji} **{analysis.confidence_level.upper()} CONFIDENCE**")
    lines.append("")
    lines.append(f"**Best Estimate:** ${analysis.best_estimate:.1f}B")
    lines.append(f"**Credible Range:** ${analysis.estimate_range[0]:.1f}B - ${analysis.estimate_range[1]:.1f}B")
    lines.append("")
    lines.append(f"*{analysis.verdict_summary}*")

    return "\n".join(lines)
