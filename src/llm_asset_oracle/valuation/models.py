"""
Valuation Models Configuration

The 15 reliable frontier models for market cap valuation analysis.
Updated December 2025 - focuses on stable, working models from OpenRouter.
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
# THE 15 VALUATION MODELS - Tested & Reliable (December 2025)
# =============================================================================

VALUATION_MODELS = [
    # OpenAI - Confirmed Working
    ValuationModel(
        id="openai/gpt-5.2",
        name="GPT-5.2",
        provider="OpenAI",
        tier="flagship",
    ),
    ValuationModel(
        id="openai/gpt-4o",
        name="GPT-4o",
        provider="OpenAI",
        tier="flagship",
    ),

    # Anthropic - Confirmed Working
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

    # xAI - Confirmed Working
    ValuationModel(
        id="x-ai/grok-4",
        name="Grok 4",
        provider="xAI",
        tier="flagship",
    ),

    # DeepSeek - Confirmed Working
    ValuationModel(
        id="deepseek/deepseek-chat-v3.1",
        name="DeepSeek V3.1",
        provider="DeepSeek",
        tier="flagship",
    ),

    # Meta - Confirmed Working
    ValuationModel(
        id="meta-llama/llama-3.1-405b-instruct",
        name="Llama 3.1 405B",
        provider="Meta",
        tier="flagship",
    ),
    ValuationModel(
        id="meta-llama/llama-3.3-70b-instruct",
        name="Llama 3.3 70B",
        provider="Meta",
        tier="standard",
    ),

    # Cohere - Stable & Reliable
    ValuationModel(
        id="cohere/command-r-plus-08-2024",
        name="Command R+",
        provider="Cohere",
        tier="flagship",
    ),

    # Perplexity - Reliable
    ValuationModel(
        id="perplexity/sonar-pro",
        name="Sonar Pro",
        provider="Perplexity",
        tier="flagship",
    ),

    # Mistral - Stable Release
    ValuationModel(
        id="mistralai/mistral-large-latest",
        name="Mistral Large",
        provider="Mistral",
        tier="flagship",
    ),

    # Qwen - Stable Version
    ValuationModel(
        id="qwen/qwen-2.5-72b-instruct",
        name="Qwen 2.5 72B",
        provider="Alibaba",
        tier="standard",
    ),

    # Google - Stable Release (not preview)
    ValuationModel(
        id="google/gemini-2.0-flash",
        name="Gemini 2.0 Flash",
        provider="Google",
        tier="fast",
    ),

    # AI21 - Reliable
    ValuationModel(
        id="ai21/jamba-1.5-large",
        name="Jamba 1.5 Large",
        provider="AI21",
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
