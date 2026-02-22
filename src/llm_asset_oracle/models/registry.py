"""
Model Registry - Curated list of 18 frontier LLM models available via OpenRouter.

Each model is tagged with vision support for Mode D (Technical Analyst).
Users can select up to 8 models per query.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class LLMModel:
    """A curated LLM model available for queries."""

    id: str  # OpenRouter model ID
    name: str  # Display name (shown in Discord selects)
    provider: str  # Company name
    supports_vision: bool  # Can process images


# =============================================================================
# 18 CURATED MODELS (February 2026)
# =============================================================================

ALL_MODELS: list[LLMModel] = [
    # OpenAI
    LLMModel(id="openai/gpt-5.2-chat", name="ChatGPT 5.2", provider="OpenAI", supports_vision=True),
    LLMModel(id="openai/gpt-5.2-pro", name="ChatGPT 5.2 Pro", provider="OpenAI", supports_vision=True),

    # Anthropic
    LLMModel(id="anthropic/claude-opus-4.6", name="Claude Opus 4.6", provider="Anthropic", supports_vision=True),
    LLMModel(id="anthropic/claude-opus-4.5", name="Claude Opus 4.5", provider="Anthropic", supports_vision=True),
    LLMModel(id="anthropic/claude-sonnet-4.5", name="Claude Sonnet 4.5", provider="Anthropic", supports_vision=True),
    LLMModel(id="anthropic/claude-sonnet-4.6", name="Claude Sonnet 4.6", provider="Anthropic", supports_vision=True),

    # Google
    LLMModel(id="google/gemini-3-flash-preview", name="Gemini 3 Flash Preview", provider="Google", supports_vision=True),
    LLMModel(id="google/gemini-3-pro-preview", name="Gemini 3 Pro Preview", provider="Google", supports_vision=True),
    LLMModel(id="google/gemini-3.1-pro-preview", name="Gemini 3.1 Pro Preview", provider="Google", supports_vision=True),

    # xAI
    LLMModel(id="x-ai/grok-4.1-fast", name="Grok 4.1 Fast", provider="xAI", supports_vision=True),
    LLMModel(id="x-ai/grok-4", name="Grok 4", provider="xAI", supports_vision=True),
    LLMModel(id="x-ai/grok-4-fast", name="Grok 4 Fast", provider="xAI", supports_vision=True),

    # Moonshot
    LLMModel(id="moonshotai/kimi-k2.5", name="Kimi K2.5", provider="Moonshot", supports_vision=True),

    # Zhipu AI
    LLMModel(id="z-ai/glm-5", name="GLM 5", provider="Zhipu AI", supports_vision=False),

    # DeepSeek
    LLMModel(id="deepseek/deepseek-v3.2", name="Deepseek v3.2", provider="DeepSeek", supports_vision=False),

    # Qwen (Alibaba)
    LLMModel(id="qwen/qwen3.5-397b-a17b", name="Qwen 3.5", provider="Alibaba", supports_vision=True),
    LLMModel(id="qwen/qwen3.5-plus-02-15", name="Qwen 3.5 Plus", provider="Alibaba", supports_vision=True),
    LLMModel(id="qwen/qwen3-max-thinking", name="Qwen 3 Max Thinking", provider="Alibaba", supports_vision=False),
]

# Lookup helpers
MODELS_BY_ID: dict[str, LLMModel] = {m.id: m for m in ALL_MODELS}
VISION_MODELS: list[LLMModel] = [m for m in ALL_MODELS if m.supports_vision]
TEXT_ONLY_MODELS: list[LLMModel] = [m for m in ALL_MODELS if not m.supports_vision]

ALL_MODEL_IDS: list[str] = [m.id for m in ALL_MODELS]
VISION_MODEL_IDS: list[str] = [m.id for m in VISION_MODELS]

MAX_MODEL_SELECTION = 8


def get_model_name(model_id: str) -> str:
    """Get display name for a model ID."""
    model = MODELS_BY_ID.get(model_id)
    return model.name if model else model_id
