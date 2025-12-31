"""
Valuation Models Configuration

The 15 cutting-edge frontier models for market cap valuation analysis.
Updated December 2025 with latest model IDs from OpenRouter.
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
# THE 15 VALUATION MODELS - Latest Frontier Models (December 2025)
# =============================================================================

VALUATION_MODELS = [
    # OpenAI - Latest GPT-5 series
    ValuationModel(
        id="openai/gpt-5.2",
        name="GPT-5.2",
        provider="OpenAI",
        tier="flagship",
    ),
    ValuationModel(
        id="openai/gpt-5.1",
        name="GPT-5.1",
        provider="OpenAI",
        tier="flagship",
    ),
    ValuationModel(
        id="openai/gpt-4o",
        name="GPT-4o",
        provider="OpenAI",
        tier="standard",
    ),

    # Anthropic - Latest Claude 4.5 series
    ValuationModel(
        id="anthropic/claude-opus-4.5",
        name="Claude Opus 4.5",
        provider="Anthropic",
        tier="flagship",
    ),
    ValuationModel(
        id="anthropic/claude-sonnet-4.5",
        name="Claude Sonnet 4.5",
        provider="Anthropic",
        tier="standard",
    ),
    ValuationModel(
        id="anthropic/claude-opus-4",
        name="Claude Opus 4",
        provider="Anthropic",
        tier="flagship",
    ),

    # Google - Gemini 3 and 2.5
    ValuationModel(
        id="google/gemini-3-pro-preview",
        name="Gemini 3 Pro",
        provider="Google",
        tier="flagship",
    ),
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

    # xAI - Grok 4
    ValuationModel(
        id="x-ai/grok-4",
        name="Grok 4",
        provider="xAI",
        tier="flagship",
    ),

    # DeepSeek - R1 and V3.1
    ValuationModel(
        id="deepseek/deepseek-r1",
        name="DeepSeek R1",
        provider="DeepSeek",
        tier="flagship",
    ),
    ValuationModel(
        id="deepseek/deepseek-chat-v3.1",
        name="DeepSeek V3.1",
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

    # Meta - Llama
    ValuationModel(
        id="meta-llama/llama-3.1-405b-instruct",
        name="Llama 3.1 405B",
        provider="Meta",
        tier="flagship",
    ),

    # Mistral
    ValuationModel(
        id="mistralai/mistral-large-latest",
        name="Mistral Large",
        provider="Mistral",
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
