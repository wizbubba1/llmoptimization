"""
OpenRouter Integration - Unified LLM Gateway

OpenRouter provides a single API endpoint to access 100+ LLM models from
various providers (OpenAI, Anthropic, Google, Meta, Mistral, etc.)

API: https://openrouter.ai/api/v1/chat/completions
Docs: https://openrouter.ai/docs
"""

import asyncio
import logging
import time
from dataclasses import dataclass
from typing import Optional

import httpx

logger = logging.getLogger(__name__)


@dataclass
class ModelConfig:
    """Configuration for an LLM model on OpenRouter."""

    id: str  # OpenRouter model ID
    name: str  # Human-readable name
    provider: str  # Company/lab that created it
    context_length: int  # Max context window
    cost_per_1k_input: float  # Cost per 1K input tokens
    cost_per_1k_output: float  # Cost per 1K output tokens


# =============================================================================
# LATEST MODELS (2024-2025) - 20 diverse models from top AI labs
# =============================================================================

AVAILABLE_MODELS = [
    # OpenAI
    ModelConfig(
        id="openai/gpt-4-turbo",
        name="GPT-4 Turbo",
        provider="OpenAI",
        context_length=128000,
        cost_per_1k_input=0.01,
        cost_per_1k_output=0.03,
    ),
    ModelConfig(
        id="openai/gpt-4o",
        name="GPT-4o",
        provider="OpenAI",
        context_length=128000,
        cost_per_1k_input=0.005,
        cost_per_1k_output=0.015,
    ),
    ModelConfig(
        id="openai/gpt-4o-mini",
        name="GPT-4o Mini",
        provider="OpenAI",
        context_length=128000,
        cost_per_1k_input=0.00015,
        cost_per_1k_output=0.0006,
    ),
    # Anthropic
    ModelConfig(
        id="anthropic/claude-3.5-sonnet",
        name="Claude 3.5 Sonnet",
        provider="Anthropic",
        context_length=200000,
        cost_per_1k_input=0.003,
        cost_per_1k_output=0.015,
    ),
    ModelConfig(
        id="anthropic/claude-3-opus",
        name="Claude 3 Opus",
        provider="Anthropic",
        context_length=200000,
        cost_per_1k_input=0.015,
        cost_per_1k_output=0.075,
    ),
    ModelConfig(
        id="anthropic/claude-3-haiku",
        name="Claude 3 Haiku",
        provider="Anthropic",
        context_length=200000,
        cost_per_1k_input=0.00025,
        cost_per_1k_output=0.00125,
    ),
    # Google
    ModelConfig(
        id="google/gemini-pro-1.5",
        name="Gemini Pro 1.5",
        provider="Google",
        context_length=1000000,
        cost_per_1k_input=0.00125,
        cost_per_1k_output=0.005,
    ),
    ModelConfig(
        id="google/gemini-flash-1.5",
        name="Gemini Flash 1.5",
        provider="Google",
        context_length=1000000,
        cost_per_1k_input=0.000075,
        cost_per_1k_output=0.0003,
    ),
    # Meta (Llama)
    ModelConfig(
        id="meta-llama/llama-3.1-405b-instruct",
        name="Llama 3.1 405B",
        provider="Meta",
        context_length=131072,
        cost_per_1k_input=0.003,
        cost_per_1k_output=0.003,
    ),
    ModelConfig(
        id="meta-llama/llama-3.1-70b-instruct",
        name="Llama 3.1 70B",
        provider="Meta",
        context_length=131072,
        cost_per_1k_input=0.0004,
        cost_per_1k_output=0.0004,
    ),
    ModelConfig(
        id="meta-llama/llama-3.1-8b-instruct",
        name="Llama 3.1 8B",
        provider="Meta",
        context_length=131072,
        cost_per_1k_input=0.00005,
        cost_per_1k_output=0.00005,
    ),
    # Mistral
    ModelConfig(
        id="mistralai/mistral-large",
        name="Mistral Large",
        provider="Mistral",
        context_length=128000,
        cost_per_1k_input=0.002,
        cost_per_1k_output=0.006,
    ),
    ModelConfig(
        id="mistralai/mixtral-8x22b-instruct",
        name="Mixtral 8x22B",
        provider="Mistral",
        context_length=65536,
        cost_per_1k_input=0.0009,
        cost_per_1k_output=0.0009,
    ),
    ModelConfig(
        id="mistralai/mistral-nemo",
        name="Mistral Nemo",
        provider="Mistral",
        context_length=128000,
        cost_per_1k_input=0.00013,
        cost_per_1k_output=0.00013,
    ),
    # Cohere
    ModelConfig(
        id="cohere/command-r-plus",
        name="Command R+",
        provider="Cohere",
        context_length=128000,
        cost_per_1k_input=0.003,
        cost_per_1k_output=0.015,
    ),
    ModelConfig(
        id="cohere/command-r",
        name="Command R",
        provider="Cohere",
        context_length=128000,
        cost_per_1k_input=0.0005,
        cost_per_1k_output=0.0015,
    ),
    # Qwen (Alibaba)
    ModelConfig(
        id="qwen/qwen-2.5-72b-instruct",
        name="Qwen 2.5 72B",
        provider="Alibaba",
        context_length=131072,
        cost_per_1k_input=0.0004,
        cost_per_1k_output=0.0004,
    ),
    # DeepSeek
    ModelConfig(
        id="deepseek/deepseek-chat",
        name="DeepSeek V2.5",
        provider="DeepSeek",
        context_length=65536,
        cost_per_1k_input=0.00014,
        cost_per_1k_output=0.00028,
    ),
    # Perplexity
    ModelConfig(
        id="perplexity/llama-3.1-sonar-large-128k-online",
        name="Sonar Large (Online)",
        provider="Perplexity",
        context_length=128000,
        cost_per_1k_input=0.001,
        cost_per_1k_output=0.001,
    ),
    # Nous Research
    ModelConfig(
        id="nousresearch/hermes-3-llama-3.1-405b",
        name="Hermes 3 405B",
        provider="Nous Research",
        context_length=131072,
        cost_per_1k_input=0.003,
        cost_per_1k_output=0.003,
    ),
]

# Quick lookup by ID
MODELS_BY_ID = {m.id: m for m in AVAILABLE_MODELS}


@dataclass
class ModelResponse:
    """Response from a single model query."""

    model_id: str
    model_name: str
    provider: str
    direction: str  # "BUY" or "SELL"
    confidence: int  # 1-100
    view: str  # One-line reasoning
    raw_response: str
    latency_ms: float
    tokens_used: int
    cost_usd: float
    success: bool
    error: Optional[str] = None


class OpenRouterClient:
    """
    Client for OpenRouter API.

    Provides unified access to multiple LLM providers through a single API.
    """

    BASE_URL = "https://openrouter.ai/api/v1"

    def __init__(
        self,
        api_key: str,
        site_url: str = "https://llm-asset-oracle.app",
        site_name: str = "LLM Asset Oracle",
        timeout: float = 60.0,
        max_concurrent: int = 10,
    ):
        """
        Initialize OpenRouter client.

        Args:
            api_key: OpenRouter API key
            site_url: Your app's URL (for rankings)
            site_name: Your app's name (for rankings)
            timeout: Request timeout in seconds
            max_concurrent: Max concurrent requests
        """
        self.api_key = api_key
        self.site_url = site_url
        self.site_name = site_name
        self.timeout = timeout
        self._semaphore = asyncio.Semaphore(max_concurrent)

    async def query_model(
        self,
        model_id: str,
        prompt: str,
        max_tokens: int = 150,
        temperature: float = 0.1,
    ) -> ModelResponse:
        """
        Query a single model.

        Args:
            model_id: OpenRouter model ID
            prompt: The prompt to send
            max_tokens: Maximum response tokens
            temperature: Sampling temperature (low for consistency)

        Returns:
            ModelResponse with parsed results
        """
        model_config = MODELS_BY_ID.get(model_id)
        if not model_config:
            return ModelResponse(
                model_id=model_id,
                model_name=model_id,
                provider="Unknown",
                direction="NEUTRAL",
                confidence=0,
                view="Unknown model",
                raw_response="",
                latency_ms=0,
                tokens_used=0,
                cost_usd=0,
                success=False,
                error=f"Unknown model: {model_id}",
            )

        start_time = time.time()

        async with self._semaphore:
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    response = await client.post(
                        f"{self.BASE_URL}/chat/completions",
                        headers={
                            "Authorization": f"Bearer {self.api_key}",
                            "HTTP-Referer": self.site_url,
                            "X-Title": self.site_name,
                            "Content-Type": "application/json",
                        },
                        json={
                            "model": model_id,
                            "messages": [{"role": "user", "content": prompt}],
                            "max_tokens": max_tokens,
                            "temperature": temperature,
                        },
                    )

                    latency_ms = (time.time() - start_time) * 1000

                    if response.status_code != 200:
                        error_text = response.text
                        return ModelResponse(
                            model_id=model_id,
                            model_name=model_config.name,
                            provider=model_config.provider,
                            direction="NEUTRAL",
                            confidence=0,
                            view="",
                            raw_response=error_text,
                            latency_ms=latency_ms,
                            tokens_used=0,
                            cost_usd=0,
                            success=False,
                            error=f"HTTP {response.status_code}: {error_text[:200]}",
                        )

                    data = response.json()

                    # Extract response
                    raw_text = data["choices"][0]["message"]["content"]
                    usage = data.get("usage", {})
                    input_tokens = usage.get("prompt_tokens", 0)
                    output_tokens = usage.get("completion_tokens", 0)
                    total_tokens = input_tokens + output_tokens

                    # Calculate cost
                    cost = (
                        input_tokens / 1000 * model_config.cost_per_1k_input
                        + output_tokens / 1000 * model_config.cost_per_1k_output
                    )

                    # Parse the structured response
                    direction, confidence, view = self._parse_response(raw_text)

                    return ModelResponse(
                        model_id=model_id,
                        model_name=model_config.name,
                        provider=model_config.provider,
                        direction=direction,
                        confidence=confidence,
                        view=view,
                        raw_response=raw_text,
                        latency_ms=latency_ms,
                        tokens_used=total_tokens,
                        cost_usd=cost,
                        success=True,
                    )

            except asyncio.TimeoutError:
                return ModelResponse(
                    model_id=model_id,
                    model_name=model_config.name,
                    provider=model_config.provider,
                    direction="NEUTRAL",
                    confidence=0,
                    view="",
                    raw_response="",
                    latency_ms=(time.time() - start_time) * 1000,
                    tokens_used=0,
                    cost_usd=0,
                    success=False,
                    error="Request timed out",
                )
            except Exception as e:
                return ModelResponse(
                    model_id=model_id,
                    model_name=model_config.name,
                    provider=model_config.provider,
                    direction="NEUTRAL",
                    confidence=0,
                    view="",
                    raw_response="",
                    latency_ms=(time.time() - start_time) * 1000,
                    tokens_used=0,
                    cost_usd=0,
                    success=False,
                    error=str(e),
                )

    def _parse_response(self, text: str) -> tuple[str, int, str]:
        """
        Parse model response into structured format.

        Expected format:
        DIRECTION: BUY
        CONFIDENCE: 75
        VIEW: Brief one-line view...

        Returns:
            Tuple of (direction, confidence, view)
        """
        import re

        text = text.strip()
        lines = text.split("\n")

        direction = "NEUTRAL"
        confidence = 50
        view = ""

        for line in lines:
            line = line.strip()

            # Parse DIRECTION
            if line.upper().startswith("DIRECTION"):
                match = re.search(r"(BUY|SELL|HOLD|NEUTRAL)", line.upper())
                if match:
                    dir_val = match.group(1)
                    direction = "BUY" if dir_val == "BUY" else "SELL" if dir_val == "SELL" else "NEUTRAL"

            # Parse CONFIDENCE
            elif line.upper().startswith("CONFIDENCE"):
                match = re.search(r"(\d+)", line)
                if match:
                    conf_val = int(match.group(1))
                    confidence = max(1, min(100, conf_val))

            # Parse VIEW
            elif line.upper().startswith("VIEW"):
                view = re.sub(r"^VIEW[:\s]*", "", line, flags=re.IGNORECASE).strip()

        # If no view found, use the whole response
        if not view:
            view = text[:200]

        return direction, confidence, view

    async def query_all_models(
        self,
        prompt: str,
        model_ids: Optional[list[str]] = None,
        max_tokens: int = 150,
    ) -> list[ModelResponse]:
        """
        Query multiple models concurrently.

        Args:
            prompt: The prompt to send to all models
            model_ids: List of model IDs (defaults to all available)
            max_tokens: Maximum response tokens

        Returns:
            List of ModelResponse from each model
        """
        if model_ids is None:
            model_ids = [m.id for m in AVAILABLE_MODELS]

        tasks = [
            self.query_model(model_id, prompt, max_tokens)
            for model_id in model_ids
        ]

        results = await asyncio.gather(*tasks)
        return list(results)

    async def get_available_models(self) -> list[dict]:
        """Fetch available models from OpenRouter."""
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    f"{self.BASE_URL}/models",
                    headers={"Authorization": f"Bearer {self.api_key}"},
                )
                response.raise_for_status()
                return response.json().get("data", [])
        except Exception as e:
            logger.error(f"Failed to fetch models: {e}")
            return []


def get_model_subset(
    count: int = 15,
    include_providers: Optional[list[str]] = None,
    exclude_providers: Optional[list[str]] = None,
    budget_mode: bool = False,
) -> list[str]:
    """
    Get a subset of model IDs based on criteria.

    Args:
        count: Number of models to return
        include_providers: Only include these providers
        exclude_providers: Exclude these providers
        budget_mode: Prefer cheaper models

    Returns:
        List of model IDs
    """
    models = AVAILABLE_MODELS.copy()

    if include_providers:
        models = [m for m in models if m.provider in include_providers]

    if exclude_providers:
        models = [m for m in models if m.provider not in exclude_providers]

    if budget_mode:
        # Sort by cost (input + output)
        models.sort(key=lambda m: m.cost_per_1k_input + m.cost_per_1k_output)

    # Return requested count
    return [m.id for m in models[:count]]
