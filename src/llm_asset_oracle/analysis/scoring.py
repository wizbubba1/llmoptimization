"""Scoring and consensus calculation algorithms."""

from collections import Counter
from typing import Optional

import numpy as np
from scipy import stats

from llm_asset_oracle.core.models import (
    Asset,
    LLMResponse,
    ConsensusScore,
    ConsensusMetrics,
)


class ScoreAggregator:
    """Aggregates individual scores into composite metrics."""

    # Weights for different score components
    COMPONENT_WEIGHTS = {
        "overall": 0.25,
        "bullish": 0.10,
        "short_term": 0.10,
        "medium_term": 0.15,
        "long_term": 0.15,
        "fundamentals": 0.10,
        "momentum": 0.10,
        "sentiment": 0.05,
    }

    @classmethod
    def calculate_composite_score(cls, response: LLMResponse) -> float:
        """
        Calculate a weighted composite score from an LLM response.

        Args:
            response: The LLM response with ratings

        Returns:
            Composite score (1-10 scale)
        """
        rating = response.rating

        # Calculate weighted sum
        score = (
            rating.overall_score * cls.COMPONENT_WEIGHTS["overall"]
            + rating.bullish_score * cls.COMPONENT_WEIGHTS["bullish"]
            + rating.short_term_outlook * cls.COMPONENT_WEIGHTS["short_term"]
            + rating.medium_term_outlook * cls.COMPONENT_WEIGHTS["medium_term"]
            + rating.long_term_outlook * cls.COMPONENT_WEIGHTS["long_term"]
            + rating.fundamentals_score * cls.COMPONENT_WEIGHTS["fundamentals"]
            + rating.momentum_score * cls.COMPONENT_WEIGHTS["momentum"]
            + rating.sentiment_score * cls.COMPONENT_WEIGHTS["sentiment"]
        )

        # Apply risk adjustment
        # Lower risk = bonus, higher risk = penalty
        risk_adjustment = (5 - rating.risk_score) * 0.1  # -0.5 to +0.4
        adjusted_score = score + risk_adjustment

        return max(1.0, min(10.0, adjusted_score))


class ConsensusCalculator:
    """
    Calculates consensus scores using statistical methods.

    The LLM Optimization Score (LOS) measures how positively and consistently
    an asset is rated across multiple AI models.

    Scientific Methodology:
    1. Collect ratings from diverse LLM providers
    2. Calculate statistical metrics (mean, variance, etc.)
    3. Adjust for consensus strength (lower variance = higher confidence)
    4. Normalize to 0-100 scale for interpretability
    """

    @classmethod
    def calculate_consensus(
        cls, asset: Asset, responses: list[LLMResponse]
    ) -> ConsensusScore:
        """
        Calculate consensus score from multiple LLM responses.

        Args:
            asset: The analyzed asset
            responses: List of LLM responses

        Returns:
            ConsensusScore with aggregated metrics
        """
        if not responses:
            raise ValueError("At least one response is required for consensus")

        # Extract composite scores from each response
        composite_scores = [ScoreAggregator.calculate_composite_score(r) for r in responses]

        # Calculate basic statistics
        metrics = cls._calculate_metrics(composite_scores)

        # Calculate LLM Optimization Score (LOS)
        # Base score from mean, adjusted for consensus
        los_score = cls._calculate_los(metrics)

        # Calculate consensus strength (inverse of normalized variance)
        consensus_strength = cls._calculate_consensus_strength(metrics)

        # Calculate confidence interval
        confidence_interval = cls._calculate_confidence_interval(
            composite_scores, metrics
        )

        # Count bullish/bearish/neutral models
        bullish = sum(1 for s in composite_scores if s > 6)
        bearish = sum(1 for s in composite_scores if s < 5)
        neutral = len(composite_scores) - bullish - bearish

        # Calculate category-specific scores
        category_scores = cls._calculate_category_scores(responses)

        # Aggregate common factors
        common_bullish = cls._aggregate_factors(
            [r.rating.key_bullish_factors for r in responses]
        )
        common_bearish = cls._aggregate_factors(
            [r.rating.key_bearish_factors for r in responses]
        )

        # Total latency
        total_latency = sum(r.latency_ms for r in responses)

        return ConsensusScore(
            asset=asset,
            responses=responses,
            los_score=los_score,
            consensus_strength=consensus_strength,
            confidence_interval=confidence_interval,
            metrics=metrics,
            category_scores=category_scores,
            bullish_models=bullish,
            bearish_models=bearish,
            neutral_models=neutral,
            common_bullish_factors=common_bullish,
            common_bearish_factors=common_bearish,
            total_models_queried=len(responses),
            total_latency_ms=total_latency,
        )

    @classmethod
    def _calculate_metrics(cls, scores: list[float]) -> ConsensusMetrics:
        """Calculate statistical metrics from scores."""
        arr = np.array(scores)

        mean = float(np.mean(arr))
        std_dev = float(np.std(arr, ddof=1)) if len(arr) > 1 else 0.0
        cv = std_dev / mean if mean > 0 else 0.0

        # Calculate IQR
        q75, q25 = np.percentile(arr, [75, 25])
        iqr = float(q75 - q25)

        return ConsensusMetrics(
            mean=mean,
            median=float(np.median(arr)),
            std_dev=std_dev,
            min_score=float(np.min(arr)),
            max_score=float(np.max(arr)),
            range=float(np.max(arr) - np.min(arr)),
            coefficient_of_variation=cv,
            interquartile_range=iqr,
        )

    @classmethod
    def _calculate_los(cls, metrics: ConsensusMetrics) -> float:
        """
        Calculate LLM Optimization Score (0-100).

        Formula:
        LOS = (normalized_mean * base_weight) * consensus_multiplier

        Where:
        - normalized_mean: Mean score scaled to 0-100
        - consensus_multiplier: Bonus/penalty based on agreement level
        """
        # Normalize mean from 1-10 to 0-100
        normalized_mean = (metrics.mean - 1) / 9 * 100

        # Calculate consensus multiplier
        # Low CV = high consensus = bonus
        # CV of 0 = 1.15x multiplier (15% bonus)
        # CV of 0.3+ = 0.85x multiplier (15% penalty)
        cv_factor = max(0, min(0.3, metrics.coefficient_of_variation))
        consensus_multiplier = 1.15 - (cv_factor / 0.3 * 0.30)

        los = normalized_mean * consensus_multiplier

        return max(0.0, min(100.0, los))

    @classmethod
    def _calculate_consensus_strength(cls, metrics: ConsensusMetrics) -> float:
        """
        Calculate consensus strength (0-100).

        Based on coefficient of variation:
        - CV = 0: 100% consensus
        - CV >= 0.4: 0% consensus
        """
        max_cv = 0.4  # CV threshold for "no consensus"
        cv = min(metrics.coefficient_of_variation, max_cv)

        consensus = (1 - (cv / max_cv)) * 100
        return max(0.0, min(100.0, consensus))

    @classmethod
    def _calculate_confidence_interval(
        cls, scores: list[float], metrics: ConsensusMetrics, confidence: float = 0.95
    ) -> tuple[float, float]:
        """Calculate confidence interval for the LOS score."""
        if len(scores) < 2:
            los = (metrics.mean - 1) / 9 * 100
            return (los, los)

        # Calculate CI for the mean
        n = len(scores)
        se = metrics.std_dev / np.sqrt(n)

        # t-score for 95% confidence
        t_score = stats.t.ppf((1 + confidence) / 2, n - 1)
        margin = t_score * se

        # Convert to LOS scale (0-100)
        mean_los = (metrics.mean - 1) / 9 * 100
        lower = max(0, (metrics.mean - margin - 1) / 9 * 100)
        upper = min(100, (metrics.mean + margin - 1) / 9 * 100)

        return (round(lower, 2), round(upper, 2))

    @classmethod
    def _calculate_category_scores(
        cls, responses: list[LLMResponse]
    ) -> dict[str, float]:
        """Calculate average scores per category."""
        categories = {
            "overall": [],
            "short_term": [],
            "medium_term": [],
            "long_term": [],
            "fundamentals": [],
            "momentum": [],
            "risk": [],
        }

        for r in responses:
            categories["overall"].append(r.rating.overall_score)
            categories["short_term"].append(r.rating.short_term_outlook)
            categories["medium_term"].append(r.rating.medium_term_outlook)
            categories["long_term"].append(r.rating.long_term_outlook)
            categories["fundamentals"].append(r.rating.fundamentals_score)
            categories["momentum"].append(r.rating.momentum_score)
            categories["risk"].append(r.rating.risk_score)

        return {k: float(np.mean(v)) for k, v in categories.items() if v}

    @classmethod
    def _aggregate_factors(cls, factor_lists: list[list[str]]) -> list[str]:
        """Aggregate and rank common factors across responses."""
        # Flatten and count
        all_factors = []
        for factors in factor_lists:
            all_factors.extend(factors)

        # Count occurrences
        counter = Counter(all_factors)

        # Return most common (mentioned by multiple models)
        common = [factor for factor, count in counter.most_common(5) if count > 1]

        # If no factor mentioned multiple times, return top unique ones
        if not common:
            common = [factor for factor, _ in counter.most_common(3)]

        return common


class RankingEngine:
    """Engine for ranking assets by their LOS scores."""

    @classmethod
    def rank_assets(cls, consensus_scores: list[ConsensusScore]) -> list[ConsensusScore]:
        """
        Rank assets by their LOS scores.

        Args:
            consensus_scores: List of consensus scores for different assets

        Returns:
            Sorted list (highest LOS first)
        """
        return sorted(consensus_scores, key=lambda x: x.los_score, reverse=True)

    @classmethod
    def get_top_assets(
        cls, consensus_scores: list[ConsensusScore], n: int = 10
    ) -> list[ConsensusScore]:
        """Get top N assets by LOS score."""
        ranked = cls.rank_assets(consensus_scores)
        return ranked[:n]

    @classmethod
    def filter_by_consensus(
        cls,
        consensus_scores: list[ConsensusScore],
        min_consensus: float = 50.0,
    ) -> list[ConsensusScore]:
        """Filter assets that meet minimum consensus threshold."""
        return [cs for cs in consensus_scores if cs.consensus_strength >= min_consensus]

    @classmethod
    def get_high_conviction_picks(
        cls,
        consensus_scores: list[ConsensusScore],
        min_los: float = 65.0,
        min_consensus: float = 60.0,
    ) -> list[ConsensusScore]:
        """
        Get high-conviction picks - assets with both high LOS and high consensus.

        Args:
            consensus_scores: List of consensus scores
            min_los: Minimum LOS score (default 65)
            min_consensus: Minimum consensus strength (default 60)

        Returns:
            Filtered and ranked list of high-conviction picks
        """
        filtered = [
            cs
            for cs in consensus_scores
            if cs.los_score >= min_los and cs.consensus_strength >= min_consensus
        ]
        return cls.rank_assets(filtered)
