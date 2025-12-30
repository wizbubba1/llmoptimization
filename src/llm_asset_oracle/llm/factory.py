"""Factory for creating LLM providers."""

import logging
from typing import Optional

from llm_asset_oracle.core.config import Settings, get_settings
from llm_asset_oracle.llm.providers import (
    OpenAIProvider,
    AnthropicProvider,
    GoogleProvider,
    TogetherProvider,
    MistralProvider,
)

logger = logging.getLogger(__name__)

# Provider registry
PROVIDER_CLASSES = {
    "openai": OpenAIProvider,
    "anthropic": AnthropicProvider,
    "google": GoogleProvider,
    "together": TogetherProvider,
    "mistral": MistralProvider,
}

# Model options per provider
PROVIDER_MODELS = {
    "openai": [
        "gpt-4-turbo-preview",
        "gpt-4",
        "gpt-4-0125-preview",
        "gpt-3.5-turbo",
    ],
    "anthropic": [
        "claude-3-5-sonnet-20241022",
        "claude-3-opus-20240229",
        "claude-3-sonnet-20240229",
        "claude-3-haiku-20240307",
    ],
    "google": [
        "gemini-1.5-pro",
        "gemini-1.5-flash",
        "gemini-pro",
    ],
    "together": [
        "meta-llama/Llama-3-70b-chat-hf",
        "meta-llama/Llama-3-8b-chat-hf",
        "mistralai/Mixtral-8x7B-Instruct-v0.1",
        "mistralai/Mistral-7B-Instruct-v0.2",
    ],
    "mistral": [
        "mistral-large-latest",
        "mistral-medium-latest",
        "mistral-small-latest",
    ],
}


def create_provider(
    provider_name: str,
    api_key: Optional[str] = None,
    model: Optional[str] = None,
    settings: Optional[Settings] = None,
):
    """
    Create an LLM provider instance.

    Args:
        provider_name: Name of the provider (openai, anthropic, etc.)
        api_key: Optional API key (uses settings if not provided)
        model: Optional model name (uses provider default if not provided)
        settings: Optional settings instance

    Returns:
        Provider instance

    Raises:
        ValueError: If provider not found or no API key available
    """
    settings = settings or get_settings()
    provider_name = provider_name.lower()

    if provider_name not in PROVIDER_CLASSES:
        raise ValueError(
            f"Unknown provider: {provider_name}. "
            f"Available: {list(PROVIDER_CLASSES.keys())}"
        )

    # Get API key from settings if not provided
    if not api_key:
        key_map = {
            "openai": settings.openai_api_key,
            "anthropic": settings.anthropic_api_key,
            "google": settings.google_api_key,
            "together": settings.together_api_key,
            "mistral": settings.mistral_api_key,
        }
        api_key = key_map.get(provider_name)

    if not api_key:
        raise ValueError(f"No API key configured for provider: {provider_name}")

    provider_class = PROVIDER_CLASSES[provider_name]
    return provider_class(api_key=api_key, model=model)


def get_all_providers(settings: Optional[Settings] = None) -> list:
    """
    Get instances of all configured providers.

    Args:
        settings: Optional settings instance

    Returns:
        List of provider instances for all providers with API keys
    """
    settings = settings or get_settings()
    providers = []

    available = settings.get_available_providers()
    enabled = settings.enabled_provider_list

    for provider_name in enabled:
        if provider_name in available:
            try:
                provider = create_provider(provider_name, settings=settings)
                providers.append(provider)
                logger.info(f"Initialized provider: {provider_name} ({provider.model})")
            except Exception as e:
                logger.warning(f"Failed to initialize {provider_name}: {e}")

    if not providers:
        logger.warning("No LLM providers configured! Check your API keys in .env")

    return providers


def get_diverse_providers(count: int = 3, settings: Optional[Settings] = None) -> list:
    """
    Get a diverse set of providers for consensus analysis.

    Prioritizes variety across different companies/architectures.

    Args:
        count: Number of providers to return
        settings: Optional settings instance

    Returns:
        List of provider instances
    """
    all_providers = get_all_providers(settings)

    if len(all_providers) <= count:
        return all_providers

    # Prioritize diversity - one from each major provider
    priority_order = ["anthropic", "openai", "google", "together", "mistral"]
    selected = []

    for provider_name in priority_order:
        if len(selected) >= count:
            break
        for provider in all_providers:
            if provider.provider_name == provider_name:
                selected.append(provider)
                break

    return selected
