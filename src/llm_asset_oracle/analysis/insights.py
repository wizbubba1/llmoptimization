"""Insight extraction and summary generation."""

from collections import Counter
from typing import Optional

from llm_asset_oracle.core.models import ConsensusScore, LLMResponse


class InsightExtractor:
    """Extracts actionable insights from consensus analysis."""

    @classmethod
    def generate_summary(cls, consensus: ConsensusScore) -> str:
        """
        Generate a human-readable summary of the consensus analysis.

        Args:
            consensus: The consensus score to summarize

        Returns:
            Formatted summary string
        """
        asset = consensus.asset
        los = consensus.los_score
        rec = consensus.recommendation
        cs = consensus.consensus_strength

        summary_lines = [
            f"## {asset.name} ({asset.symbol}) Analysis",
            "",
            f"**LLM Optimization Score**: {los:.1f}/100",
            f"**Recommendation**: {rec}",
            f"**Consensus Strength**: {cs:.1f}% ({consensus.consensus_label})",
            "",
            f"**Model Agreement**:",
            f"  - Bullish: {consensus.bullish_models}",
            f"  - Neutral: {consensus.neutral_models}",
            f"  - Bearish: {consensus.bearish_models}",
            "",
        ]

        # Add confidence interval
        ci_low, ci_high = consensus.confidence_interval
        summary_lines.append(f"**95% Confidence Interval**: {ci_low:.1f} - {ci_high:.1f}")
        summary_lines.append("")

        # Add category breakdown
        if consensus.category_scores:
            summary_lines.append("**Category Scores** (1-10):")
            for category, score in consensus.category_scores.items():
                summary_lines.append(f"  - {category.replace('_', ' ').title()}: {score:.1f}")
            summary_lines.append("")

        # Add common factors
        if consensus.common_bullish_factors:
            summary_lines.append("**Key Bullish Factors** (multi-model agreement):")
            for factor in consensus.common_bullish_factors[:3]:
                summary_lines.append(f"  • {factor}")
            summary_lines.append("")

        if consensus.common_bearish_factors:
            summary_lines.append("**Key Risk Factors** (multi-model agreement):")
            for factor in consensus.common_bearish_factors[:3]:
                summary_lines.append(f"  • {factor}")
            summary_lines.append("")

        # Add timing
        summary_lines.append(
            f"*Analysis based on {consensus.total_models_queried} AI models, "
            f"completed in {consensus.total_latency_ms/1000:.1f}s*"
        )

        return "\n".join(summary_lines)

    @classmethod
    def generate_discord_embed_data(cls, consensus: ConsensusScore) -> dict:
        """
        Generate data suitable for Discord embed.

        Args:
            consensus: The consensus score

        Returns:
            Dictionary with embed field data
        """
        asset = consensus.asset
        los = consensus.los_score
        rec = consensus.recommendation

        # Determine color based on recommendation
        color_map = {
            "STRONG BUY": 0x00FF00,  # Green
            "BUY": 0x90EE90,  # Light green
            "HOLD": 0xFFFF00,  # Yellow
            "SELL": 0xFFA500,  # Orange
            "STRONG SELL": 0xFF0000,  # Red
        }
        color = color_map.get(rec, 0x808080)

        # Build fields
        fields = [
            {
                "name": "LLM Optimization Score",
                "value": f"**{los:.1f}**/100",
                "inline": True,
            },
            {
                "name": "Recommendation",
                "value": f"**{rec}**",
                "inline": True,
            },
            {
                "name": "Consensus",
                "value": f"{consensus.consensus_strength:.0f}%",
                "inline": True,
            },
            {
                "name": "Model Votes",
                "value": f"🟢 {consensus.bullish_models} | ⚪ {consensus.neutral_models} | 🔴 {consensus.bearish_models}",
                "inline": True,
            },
        ]

        # Add category scores
        if consensus.category_scores:
            scores_text = " | ".join(
                f"{k[:3].upper()}: {v:.1f}"
                for k, v in list(consensus.category_scores.items())[:4]
            )
            fields.append(
                {"name": "Scores", "value": scores_text, "inline": False}
            )

        # Add bullish factors
        if consensus.common_bullish_factors:
            bullish_text = "\n".join(f"• {f}" for f in consensus.common_bullish_factors[:3])
            fields.append(
                {"name": "🟢 Bullish Factors", "value": bullish_text, "inline": True}
            )

        # Add bearish factors
        if consensus.common_bearish_factors:
            bearish_text = "\n".join(f"• {f}" for f in consensus.common_bearish_factors[:3])
            fields.append(
                {"name": "🔴 Risk Factors", "value": bearish_text, "inline": True}
            )

        return {
            "title": f"{asset.name} ({asset.symbol})",
            "description": f"Multi-LLM consensus analysis across {consensus.total_models_queried} AI models",
            "color": color,
            "fields": fields,
            "footer": {
                "text": f"Analysis completed in {consensus.total_latency_ms/1000:.1f}s | Not financial advice"
            },
        }

    @classmethod
    def get_model_disagreements(cls, consensus: ConsensusScore) -> list[dict]:
        """
        Identify significant disagreements between models.

        Returns:
            List of disagreement insights
        """
        disagreements = []
        responses = consensus.responses

        if len(responses) < 2:
            return disagreements

        # Find the most bullish and bearish models
        sorted_by_overall = sorted(
            responses, key=lambda r: r.rating.overall_score
        )

        most_bearish = sorted_by_overall[0]
        most_bullish = sorted_by_overall[-1]

        diff = most_bullish.rating.overall_score - most_bearish.rating.overall_score

        if diff >= 3:  # Significant disagreement
            disagreements.append({
                "type": "overall_divergence",
                "description": f"Significant model disagreement on overall outlook",
                "bullish_model": most_bullish.provider,
                "bullish_score": most_bullish.rating.overall_score,
                "bearish_model": most_bearish.provider,
                "bearish_score": most_bearish.rating.overall_score,
                "spread": diff,
            })

        # Check for risk assessment disagreements
        sorted_by_risk = sorted(responses, key=lambda r: r.rating.risk_score)
        risk_diff = sorted_by_risk[-1].rating.risk_score - sorted_by_risk[0].rating.risk_score

        if risk_diff >= 4:
            disagreements.append({
                "type": "risk_divergence",
                "description": "Models disagree significantly on risk assessment",
                "low_risk_model": sorted_by_risk[0].provider,
                "low_risk_score": sorted_by_risk[0].rating.risk_score,
                "high_risk_model": sorted_by_risk[-1].provider,
                "high_risk_score": sorted_by_risk[-1].rating.risk_score,
                "spread": risk_diff,
            })

        return disagreements

    @classmethod
    def compare_assets(
        cls, consensus1: ConsensusScore, consensus2: ConsensusScore
    ) -> dict:
        """
        Compare two assets and provide relative insights.

        Args:
            consensus1: First asset consensus
            consensus2: Second asset consensus

        Returns:
            Comparison insights dictionary
        """
        asset1 = consensus1.asset
        asset2 = consensus2.asset

        los_diff = consensus1.los_score - consensus2.los_score
        cs_diff = consensus1.consensus_strength - consensus2.consensus_strength

        # Determine preferred asset
        if abs(los_diff) < 5:  # Close scores
            if cs_diff > 10:
                preferred = asset1.symbol
                reason = "Higher consensus among AI models"
            elif cs_diff < -10:
                preferred = asset2.symbol
                reason = "Higher consensus among AI models"
            else:
                preferred = "Neither (too close to call)"
                reason = "Scores are within margin of error"
        else:
            preferred = asset1.symbol if los_diff > 0 else asset2.symbol
            reason = "Higher LLM Optimization Score"

        return {
            "asset1": {
                "symbol": asset1.symbol,
                "los": consensus1.los_score,
                "consensus": consensus1.consensus_strength,
                "recommendation": consensus1.recommendation,
            },
            "asset2": {
                "symbol": asset2.symbol,
                "los": consensus2.los_score,
                "consensus": consensus2.consensus_strength,
                "recommendation": consensus2.recommendation,
            },
            "preferred": preferred,
            "reason": reason,
            "los_difference": abs(los_diff),
            "consensus_difference": abs(cs_diff),
        }
