"""
Valuation Models Configuration

The 15 cutting-edge models for market cap valuation analysis.
These are the latest frontier models from top AI labs.
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class ValuationModel:
    """Configuration for a valuation model."""

    id: str  # OpenRouter model ID
    name: str  # Display name
    provider: str  # Company
    tier: str  # "flagship", "standard", "fast"


# =============================================================================
# THE 15 VALUATION MODELS (User's Selection)
# =============================================================================

VALUATION_MODELS = [
    # xAI
    ValuationModel(
        id="x-ai/grok-4",
        name="Grok 4",
        provider="xAI",
        tier="flagship",
    ),

    # Google
    ValuationModel(
        id="google/gemini-2.5-pro-preview",
        name="Gemini 2.5 Pro",
        provider="Google",
        tier="flagship",
    ),
    ValuationModel(
        id="google/gemini-2.5-flash-preview",
        name="Gemini 2.5 Flash",
        provider="Google",
        tier="fast",
    ),

    # OpenAI
    ValuationModel(
        id="openai/gpt-4o",
        name="GPT-4o",
        provider="OpenAI",
        tier="flagship",
    ),
    ValuationModel(
        id="openai/gpt-4.1",
        name="GPT-4.1",
        provider="OpenAI",
        tier="flagship",
    ),
    ValuationModel(
        id="openai/o3-mini",
        name="o3-mini",
        provider="OpenAI",
        tier="standard",
    ),

    # Anthropic
    ValuationModel(
        id="anthropic/claude-opus-4",
        name="Opus 4",
        provider="Anthropic",
        tier="flagship",
    ),
    ValuationModel(
        id="anthropic/claude-sonnet-4",
        name="Sonnet 4",
        provider="Anthropic",
        tier="standard",
    ),
    ValuationModel(
        id="anthropic/claude-3.5-sonnet",
        name="Claude 3.5 Sonnet",
        provider="Anthropic",
        tier="standard",
    ),

    # Moonshot (Kimi)
    ValuationModel(
        id="moonshotai/kimi-vl-a3b-thinking",
        name="Kimi K2 Thinking",
        provider="Moonshot",
        tier="flagship",
    ),

    # DeepSeek
    ValuationModel(
        id="deepseek/deepseek-r1",
        name="DeepSeek R1",
        provider="DeepSeek",
        tier="flagship",
    ),
    ValuationModel(
        id="deepseek/deepseek-chat",
        name="DeepSeek V3",
        provider="DeepSeek",
        tier="standard",
    ),

    # Qwen (Alibaba)
    ValuationModel(
        id="qwen/qwen3-235b-a22b",
        name="Qwen 3 235B",
        provider="Alibaba",
        tier="flagship",
    ),
    ValuationModel(
        id="qwen/qwen-2.5-72b-instruct",
        name="Qwen 2.5 72B",
        provider="Alibaba",
        tier="standard",
    ),

    # Meta
    ValuationModel(
        id="meta-llama/llama-3.1-405b-instruct",
        name="Llama 3.1 405B",
        provider="Meta",
        tier="flagship",
    ),
]

# Quick lookup by ID
MODELS_BY_ID = {m.id: m for m in VALUATION_MODELS}

# Get all model IDs
ALL_MODEL_IDS = [m.id for m in VALUATION_MODELS]


def get_model_ids(
    tier: Optional[str] = None,
    providers: Optional[list[str]] = None,
    exclude: Optional[list[str]] = None,
) -> list[str]:
    """
    Get filtered list of model IDs.

    Args:
        tier: Filter by tier ("flagship", "standard", "fast")
        providers: Only include these providers
        exclude: Exclude these model IDs

    Returns:
        List of model IDs
    """
    models = VALUATION_MODELS

    if tier:
        models = [m for m in models if m.tier == tier]

    if providers:
        models = [m for m in models if m.provider in providers]

    if exclude:
        models = [m for m in models if m.id not in exclude]

    return [m.id for m in models]


def get_flagship_models() -> list[str]:
    """Get only flagship tier models."""
    return get_model_ids(tier="flagship")


def format_model_list() -> str:
    """Format model list for display."""
    lines = ["**Active Valuation Models (15):**\n"]

    by_provider = {}
    for m in VALUATION_MODELS:
        if m.provider not in by_provider:
            by_provider[m.provider] = []
        by_provider[m.provider].append(m)

    for provider, models in by_provider.items():
        lines.append(f"**{provider}**")
        for m in models:
            tier_icon = "🏆" if m.tier == "flagship" else "⚡" if m.tier == "fast" else "📊"
            lines.append(f"  {tier_icon} {m.name}")
        lines.append("")

    return "\n".join(lines)
