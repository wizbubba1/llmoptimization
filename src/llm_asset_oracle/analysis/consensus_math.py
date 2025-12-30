"""
Statistical Consensus Engine

This module implements the mathematical framework for aggregating
LLM responses into meaningful consensus metrics.

Key Concepts:
- Directional Consensus: % of models agreeing on BUY vs SELL
- Confidence-Weighted Score: Aggregate score accounting for model certainty
- Signal Strength: Combined measure of agreement + confidence
- Heatmap Data: Per-model visualization for pattern analysis

Mathematical Framework:
1. Raw Direction: Simple majority vote
2. Weighted Direction: Each vote weighted by model's confidence
3. Consensus Score (0-100): Measures strength of agreement
4. Signal Grade (A+ to F): Final letter grade for actionability
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional
import math
from statistics import mean, stdev, median

from llm_asset_oracle.llm.openrouter import ModelResponse


class Direction(Enum):
    """Trading direction signal."""
    STRONG_BUY = "STRONG_BUY"
    BUY = "BUY"
    NEUTRAL = "NEUTRAL"
    SELL = "SELL"
    STRONG_SELL = "STRONG_SELL"


class SignalGrade(Enum):
    """Letter grade for signal quality."""
    A_PLUS = "A+"
    A = "A"
    B = "B"
    C = "C"
    D = "D"
    F = "F"


@dataclass
class ModelVote:
    """Processed vote from a single model."""
    model_id: str
    model_name: str
    provider: str
    direction: int  # +1 for BUY, -1 for SELL, 0 for NEUTRAL
    confidence: int  # 1-100
    view: str
    latency_ms: float

    @property
    def weighted_vote(self) -> float:
        """Vote weighted by confidence (-100 to +100)."""
        return self.direction * self.confidence

    @property
    def direction_label(self) -> str:
        """Human-readable direction."""
        if self.direction > 0:
            return "BUY"
        elif self.direction < 0:
            return "SELL"
        else:
            return "NEUTRAL"


@dataclass
class ConsensusResult:
    """
    Complete consensus analysis result.

    Contains all metrics needed for decision-making and visualization.
    """
    # Asset info
    symbol: str
    name: str

    # Individual votes
    votes: list[ModelVote] = field(default_factory=list)

    # Core metrics
    total_models: int = 0
    successful_queries: int = 0
    failed_queries: int = 0

    # Direction metrics
    buy_votes: int = 0
    sell_votes: int = 0
    neutral_votes: int = 0

    buy_pct: float = 0.0
    sell_pct: float = 0.0
    neutral_pct: float = 0.0

    # Weighted metrics
    weighted_score: float = 0.0  # -100 to +100
    normalized_score: float = 0.0  # 0 to 100

    # Confidence metrics
    avg_confidence: float = 0.0
    confidence_std: float = 0.0
    min_confidence: int = 0
    max_confidence: int = 0

    # Consensus metrics
    consensus_strength: float = 0.0  # 0-100, how much models agree
    signal_clarity: float = 0.0  # 0-100, clarity of the signal

    # Final outputs
    direction: Direction = Direction.NEUTRAL
    grade: SignalGrade = SignalGrade.C
    grade_score: float = 0.0  # 0-100 for numerical representation

    # Costs
    total_cost_usd: float = 0.0
    total_tokens: int = 0
    total_latency_ms: float = 0.0

    # Provider breakdown (for heatmap)
    provider_breakdown: dict = field(default_factory=dict)

    # Views summary
    common_views: list[str] = field(default_factory=list)


def direction_to_int(direction_str: str) -> int:
    """Convert direction string to integer."""
    d = direction_str.upper().strip()
    if d == "BUY":
        return 1
    elif d == "SELL":
        return -1
    else:
        return 0


def calculate_consensus(
    symbol: str,
    name: str,
    responses: list[ModelResponse],
) -> ConsensusResult:
    """
    Calculate comprehensive consensus from model responses.

    Args:
        symbol: Asset symbol
        name: Asset name
        responses: List of model responses

    Returns:
        ConsensusResult with all metrics
    """
    result = ConsensusResult(symbol=symbol, name=name)

    # Filter successful responses
    successful = [r for r in responses if r.success]
    failed = [r for r in responses if not r.success]

    result.total_models = len(responses)
    result.successful_queries = len(successful)
    result.failed_queries = len(failed)

    if not successful:
        result.grade = SignalGrade.F
        return result

    # Convert to votes
    votes = []
    for r in successful:
        vote = ModelVote(
            model_id=r.model_id,
            model_name=r.model_name,
            provider=r.provider,
            direction=direction_to_int(r.direction),
            confidence=r.confidence,
            view=r.view,
            latency_ms=r.latency_ms,
        )
        votes.append(vote)
        result.total_cost_usd += r.cost_usd
        result.total_tokens += r.tokens_used
        result.total_latency_ms += r.latency_ms

    result.votes = votes

    # Count directions
    result.buy_votes = sum(1 for v in votes if v.direction > 0)
    result.sell_votes = sum(1 for v in votes if v.direction < 0)
    result.neutral_votes = sum(1 for v in votes if v.direction == 0)

    n = len(votes)
    result.buy_pct = (result.buy_votes / n) * 100 if n > 0 else 0
    result.sell_pct = (result.sell_votes / n) * 100 if n > 0 else 0
    result.neutral_pct = (result.neutral_votes / n) * 100 if n > 0 else 0

    # Calculate weighted score
    # Sum of (direction * confidence) / sum of max possible
    weighted_sum = sum(v.weighted_vote for v in votes)
    max_possible = n * 100  # If all voted same direction with 100% confidence

    result.weighted_score = weighted_sum / n if n > 0 else 0  # Average weighted vote
    result.normalized_score = ((result.weighted_score + 100) / 200) * 100  # 0-100 scale

    # Confidence metrics
    confidences = [v.confidence for v in votes]
    result.avg_confidence = mean(confidences) if confidences else 0
    result.confidence_std = stdev(confidences) if len(confidences) > 1 else 0
    result.min_confidence = min(confidences) if confidences else 0
    result.max_confidence = max(confidences) if confidences else 0

    # Consensus strength: How much do models agree?
    # Based on how concentrated votes are in one direction
    # Max consensus = 100% same direction
    max_votes = max(result.buy_votes, result.sell_votes, result.neutral_votes)
    result.consensus_strength = (max_votes / n) * 100 if n > 0 else 0

    # Signal clarity: Combines consensus + confidence
    # High clarity = strong agreement + high confidence
    result.signal_clarity = (result.consensus_strength * result.avg_confidence) / 100

    # Determine direction
    result.direction = _determine_direction(result)

    # Calculate grade
    result.grade, result.grade_score = _calculate_grade(result)

    # Provider breakdown for heatmap
    result.provider_breakdown = _build_provider_breakdown(votes)

    # Extract common views
    result.common_views = [v.view for v in votes if v.view][:5]

    return result


def _determine_direction(result: ConsensusResult) -> Direction:
    """Determine the final direction signal."""
    ws = result.weighted_score
    cs = result.consensus_strength

    # Strong signals require both direction AND consensus
    if ws > 30 and cs >= 70:
        return Direction.STRONG_BUY
    elif ws > 15 and cs >= 50:
        return Direction.BUY
    elif ws < -30 and cs >= 70:
        return Direction.STRONG_SELL
    elif ws < -15 and cs >= 50:
        return Direction.SELL
    else:
        return Direction.NEUTRAL


def _calculate_grade(result: ConsensusResult) -> tuple[SignalGrade, float]:
    """
    Calculate signal grade based on multiple factors.

    Grading criteria:
    - A+: Strong consensus (>80%) + Strong direction (>50 weighted) + High confidence (>70)
    - A: Good consensus (>70%) + Clear direction (>30 weighted) + Good confidence (>60)
    - B: Moderate consensus (>60%) + Some direction (>15 weighted)
    - C: Weak consensus or mixed signals
    - D: Very weak or conflicting
    - F: No clear signal or mostly failed

    Returns:
        Tuple of (grade, numerical_score)
    """
    if result.successful_queries == 0:
        return SignalGrade.F, 0.0

    # Calculate component scores
    consensus_score = result.consensus_strength
    direction_score = abs(result.weighted_score)  # 0-100
    confidence_score = result.avg_confidence

    # Weighted combination
    # Consensus is most important, then direction clarity, then confidence
    composite = (
        consensus_score * 0.4 +
        direction_score * 0.35 +
        confidence_score * 0.25
    )

    # Apply penalties
    if result.failed_queries > result.successful_queries:
        composite *= 0.7  # Many failures

    if result.neutral_votes > result.buy_votes + result.sell_votes:
        composite *= 0.8  # Mostly neutral is less useful

    # Map to grade
    if composite >= 85:
        return SignalGrade.A_PLUS, composite
    elif composite >= 75:
        return SignalGrade.A, composite
    elif composite >= 60:
        return SignalGrade.B, composite
    elif composite >= 45:
        return SignalGrade.C, composite
    elif composite >= 30:
        return SignalGrade.D, composite
    else:
        return SignalGrade.F, composite


def _build_provider_breakdown(votes: list[ModelVote]) -> dict:
    """
    Build provider-level breakdown for heatmap visualization.

    Returns dict like:
    {
        "OpenAI": {"buy": 2, "sell": 0, "neutral": 0, "avg_conf": 75},
        "Anthropic": {"buy": 1, "sell": 1, "neutral": 0, "avg_conf": 80},
        ...
    }
    """
    providers: dict = {}

    for vote in votes:
        if vote.provider not in providers:
            providers[vote.provider] = {
                "buy": 0,
                "sell": 0,
                "neutral": 0,
                "confidences": [],
                "models": [],
            }

        p = providers[vote.provider]
        p["models"].append(vote.model_name)
        p["confidences"].append(vote.confidence)

        if vote.direction > 0:
            p["buy"] += 1
        elif vote.direction < 0:
            p["sell"] += 1
        else:
            p["neutral"] += 1

    # Calculate averages
    for provider, data in providers.items():
        data["avg_conf"] = mean(data["confidences"]) if data["confidences"] else 0
        data["count"] = len(data["confidences"])
        del data["confidences"]  # Clean up

    return providers


# =============================================================================
# HEATMAP GENERATION
# =============================================================================

@dataclass
class HeatmapCell:
    """Single cell in the model heatmap."""
    model_name: str
    provider: str
    direction: str  # "BUY", "SELL", "NEUTRAL"
    confidence: int
    intensity: float  # 0-1 for color mapping


def generate_heatmap_data(result: ConsensusResult) -> list[HeatmapCell]:
    """
    Generate heatmap visualization data.

    Returns list of cells that can be rendered as a visual heatmap.
    """
    cells = []

    for vote in result.votes:
        # Calculate intensity (for color mapping)
        # Buy = positive intensity, Sell = negative intensity
        if vote.direction > 0:
            intensity = vote.confidence / 100
        elif vote.direction < 0:
            intensity = -vote.confidence / 100
        else:
            intensity = 0

        cells.append(HeatmapCell(
            model_name=vote.model_name,
            provider=vote.provider,
            direction=vote.direction_label,
            confidence=vote.confidence,
            intensity=intensity,
        ))

    # Sort by provider, then by confidence
    cells.sort(key=lambda c: (c.provider, -abs(c.intensity)))

    return cells


def format_heatmap_text(cells: list[HeatmapCell]) -> str:
    """
    Format heatmap as ASCII text for Discord/CLI.

    Example output:
    ┌─────────────────────────────────────────────┐
    │ MODEL HEATMAP                               │
    ├─────────────────────────────────────────────┤
    │ OpenAI                                      │
    │  GPT-4 Turbo     [██████████] BUY  85%     │
    │  GPT-4o          [████████░░] BUY  72%     │
    │ Anthropic                                   │
    │  Claude 3.5      [██████████] BUY  90%     │
    │  Claude 3 Opus   [░░░░░░████] SELL 65%     │
    └─────────────────────────────────────────────┘
    """
    lines = []
    lines.append("```")
    lines.append("MODEL HEATMAP")
    lines.append("─" * 50)

    current_provider = None

    for cell in cells:
        if cell.provider != current_provider:
            if current_provider is not None:
                lines.append("")  # Blank line between providers
            lines.append(f"▸ {cell.provider}")
            current_provider = cell.provider

        # Create bar visualization
        bar_length = 10
        filled = int(abs(cell.intensity) * bar_length)
        empty = bar_length - filled

        if cell.direction == "BUY":
            bar = "█" * filled + "░" * empty
            emoji = "🟢"
        elif cell.direction == "SELL":
            bar = "░" * empty + "█" * filled
            emoji = "🔴"
        else:
            bar = "░" * 5 + "│" + "░" * 4
            emoji = "⚪"

        name = cell.model_name[:18].ljust(18)
        lines.append(f"  {name} [{bar}] {cell.direction:4} {cell.confidence:3}% {emoji}")

    lines.append("```")
    return "\n".join(lines)


# =============================================================================
# SUMMARY GENERATION
# =============================================================================

def format_consensus_summary(result: ConsensusResult) -> str:
    """Generate human-readable summary of consensus."""
    lines = []

    # Header
    dir_emoji = {
        Direction.STRONG_BUY: "🚀",
        Direction.BUY: "📈",
        Direction.NEUTRAL: "➡️",
        Direction.SELL: "📉",
        Direction.STRONG_SELL: "⚠️",
    }
    emoji = dir_emoji.get(result.direction, "📊")

    lines.append(f"## {emoji} {result.symbol} - {result.direction.value.replace('_', ' ')}")
    lines.append("")

    # Grade
    lines.append(f"**Signal Grade: {result.grade.value}** ({result.grade_score:.0f}/100)")
    lines.append("")

    # Vote breakdown
    lines.append(f"**Model Votes:** {result.successful_queries} models")
    lines.append(f"  🟢 BUY: {result.buy_votes} ({result.buy_pct:.0f}%)")
    lines.append(f"  🔴 SELL: {result.sell_votes} ({result.sell_pct:.0f}%)")
    lines.append(f"  ⚪ NEUTRAL: {result.neutral_votes} ({result.neutral_pct:.0f}%)")
    lines.append("")

    # Scores
    lines.append(f"**Weighted Score:** {result.weighted_score:+.1f}")
    lines.append(f"**Consensus Strength:** {result.consensus_strength:.0f}%")
    lines.append(f"**Avg Confidence:** {result.avg_confidence:.0f}%")
    lines.append("")

    # Top views
    if result.common_views:
        lines.append("**Model Views:**")
        for i, view in enumerate(result.common_views[:3], 1):
            lines.append(f"  {i}. {view}")
        lines.append("")

    # Cost
    lines.append(f"*Cost: ${result.total_cost_usd:.4f} | {result.total_tokens} tokens | {result.total_latency_ms/1000:.1f}s*")

    return "\n".join(lines)
