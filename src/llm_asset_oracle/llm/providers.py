"""Concrete LLM provider implementations."""

import logging
from typing import Optional

import httpx

logger = logging.getLogger(__name__)


# =============================================================================
# OpenAI Provider (GPT-4, GPT-3.5)
# =============================================================================

class OpenAIProvider:
    """OpenAI API provider for GPT models."""

    provider_name = "openai"
    default_model = "gpt-4-turbo-preview"

    def __init__(self, api_key: str, model: Optional[str] = None):
        self.api_key = api_key
        self.model = model or self.default_model
        self.base_url = "https://api.openai.com/v1"

    async def query(self, prompt: str, system_prompt: Optional[str] = None) -> tuple[str, int]:
        """Query OpenAI API."""
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{self.base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": self.model,
                    "messages": messages,
                    "temperature": 0.3,
                    "max_tokens": 2000,
                },
            )
            response.raise_for_status()
            data = response.json()

            content = data["choices"][0]["message"]["content"]
            tokens = data.get("usage", {}).get("total_tokens", 0)
            return content, tokens

    async def analyze_asset(self, asset, prompt_template: str):
        """Analyze asset - delegated to base implementation."""
        from llm_asset_oracle.llm.base import LLMProvider

        # Create a temporary instance with base class methods
        import time
        import json
        import re
        from llm_asset_oracle.core.models import LLMResponse, SentimentRating

        start_time = time.time()
        raw_response, tokens = await self.query(prompt_template)
        latency_ms = (time.time() - start_time) * 1000

        rating = self._parse_rating(raw_response)

        return LLMResponse(
            provider=self.provider_name,
            model=self.model,
            asset_symbol=asset.symbol,
            rating=rating,
            raw_response=raw_response,
            latency_ms=latency_ms,
            tokens_used=tokens,
        )

    def _parse_rating(self, response: str):
        """Parse rating from response."""
        import json
        import re
        from llm_asset_oracle.core.models import SentimentRating

        json_match = re.search(r"\{[\s\S]*\}", response)
        if json_match:
            try:
                data = json.loads(json_match.group())
                return self._create_rating_from_dict(data)
            except json.JSONDecodeError:
                pass
        return self._create_default_rating(response)

    def _create_rating_from_dict(self, data: dict):
        """Create rating from dict."""
        from llm_asset_oracle.core.models import SentimentRating

        def get_score(keys, default=5.0):
            for key in keys:
                if key in data:
                    val = data[key]
                    if isinstance(val, (int, float)):
                        return max(1, min(10, float(val)))
            return default

        def get_list(keys):
            for key in keys:
                if key in data and isinstance(data[key], list):
                    return [str(item) for item in data[key][:5]]
            return []

        return SentimentRating(
            overall_score=get_score(["overall_score", "overall", "rating"]),
            bullish_score=get_score(["bullish_score", "bullish"]),
            risk_score=get_score(["risk_score", "risk"]),
            short_term_outlook=get_score(["short_term_outlook", "short_term"]),
            medium_term_outlook=get_score(["medium_term_outlook", "medium_term"]),
            long_term_outlook=get_score(["long_term_outlook", "long_term"]),
            fundamentals_score=get_score(["fundamentals_score", "fundamentals"]),
            momentum_score=get_score(["momentum_score", "momentum"]),
            sentiment_score=get_score(["sentiment_score", "sentiment"]),
            key_bullish_factors=get_list(["key_bullish_factors", "bullish_factors"]),
            key_bearish_factors=get_list(["key_bearish_factors", "bearish_factors"]),
            summary=data.get("summary", "Analysis completed."),
        )

    def _create_default_rating(self, response: str):
        """Create default rating from unstructured response."""
        from llm_asset_oracle.core.models import SentimentRating
        return SentimentRating(
            overall_score=5.0,
            bullish_score=5.0,
            risk_score=5.0,
            short_term_outlook=5.0,
            medium_term_outlook=5.0,
            long_term_outlook=5.0,
            fundamentals_score=5.0,
            momentum_score=5.0,
            sentiment_score=5.0,
            key_bullish_factors=[],
            key_bearish_factors=[],
            summary=response[:500] if len(response) > 500 else response,
        )


# =============================================================================
# Anthropic Provider (Claude)
# =============================================================================

class AnthropicProvider:
    """Anthropic API provider for Claude models."""

    provider_name = "anthropic"
    default_model = "claude-3-5-sonnet-20241022"

    def __init__(self, api_key: str, model: Optional[str] = None):
        self.api_key = api_key
        self.model = model or self.default_model
        self.base_url = "https://api.anthropic.com/v1"

    async def query(self, prompt: str, system_prompt: Optional[str] = None) -> tuple[str, int]:
        """Query Anthropic API."""
        async with httpx.AsyncClient(timeout=60.0) as client:
            request_body = {
                "model": self.model,
                "max_tokens": 2000,
                "messages": [{"role": "user", "content": prompt}],
            }
            if system_prompt:
                request_body["system"] = system_prompt

            response = await client.post(
                f"{self.base_url}/messages",
                headers={
                    "x-api-key": self.api_key,
                    "anthropic-version": "2023-06-01",
                    "Content-Type": "application/json",
                },
                json=request_body,
            )
            response.raise_for_status()
            data = response.json()

            content = data["content"][0]["text"]
            tokens = data.get("usage", {}).get("input_tokens", 0) + data.get("usage", {}).get(
                "output_tokens", 0
            )
            return content, tokens

    async def analyze_asset(self, asset, prompt_template: str):
        """Analyze asset."""
        import time
        from llm_asset_oracle.core.models import LLMResponse

        start_time = time.time()
        raw_response, tokens = await self.query(prompt_template)
        latency_ms = (time.time() - start_time) * 1000

        rating = OpenAIProvider._parse_rating(self, raw_response)

        return LLMResponse(
            provider=self.provider_name,
            model=self.model,
            asset_symbol=asset.symbol,
            rating=rating,
            raw_response=raw_response,
            latency_ms=latency_ms,
            tokens_used=tokens,
        )

    _parse_rating = OpenAIProvider._parse_rating
    _create_rating_from_dict = OpenAIProvider._create_rating_from_dict
    _create_default_rating = OpenAIProvider._create_default_rating


# =============================================================================
# Google Provider (Gemini)
# =============================================================================

class GoogleProvider:
    """Google AI provider for Gemini models."""

    provider_name = "google"
    default_model = "gemini-1.5-pro"

    def __init__(self, api_key: str, model: Optional[str] = None):
        self.api_key = api_key
        self.model = model or self.default_model
        self.base_url = "https://generativelanguage.googleapis.com/v1beta"

    async def query(self, prompt: str, system_prompt: Optional[str] = None) -> tuple[str, int]:
        """Query Google Gemini API."""
        full_prompt = f"{system_prompt}\n\n{prompt}" if system_prompt else prompt

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{self.base_url}/models/{self.model}:generateContent",
                params={"key": self.api_key},
                headers={"Content-Type": "application/json"},
                json={
                    "contents": [{"parts": [{"text": full_prompt}]}],
                    "generationConfig": {
                        "temperature": 0.3,
                        "maxOutputTokens": 2000,
                    },
                },
            )
            response.raise_for_status()
            data = response.json()

            content = data["candidates"][0]["content"]["parts"][0]["text"]
            # Gemini doesn't always return token counts
            tokens = data.get("usageMetadata", {}).get("totalTokenCount", 0)
            return content, tokens

    async def analyze_asset(self, asset, prompt_template: str):
        """Analyze asset."""
        import time
        from llm_asset_oracle.core.models import LLMResponse

        start_time = time.time()
        raw_response, tokens = await self.query(prompt_template)
        latency_ms = (time.time() - start_time) * 1000

        rating = OpenAIProvider._parse_rating(self, raw_response)

        return LLMResponse(
            provider=self.provider_name,
            model=self.model,
            asset_symbol=asset.symbol,
            rating=rating,
            raw_response=raw_response,
            latency_ms=latency_ms,
            tokens_used=tokens,
        )

    _parse_rating = OpenAIProvider._parse_rating
    _create_rating_from_dict = OpenAIProvider._create_rating_from_dict
    _create_default_rating = OpenAIProvider._create_default_rating


# =============================================================================
# Together AI Provider (Llama, Mixtral, etc.)
# =============================================================================

class TogetherProvider:
    """Together AI provider for open-source models."""

    provider_name = "together"
    default_model = "meta-llama/Llama-3-70b-chat-hf"

    def __init__(self, api_key: str, model: Optional[str] = None):
        self.api_key = api_key
        self.model = model or self.default_model
        self.base_url = "https://api.together.xyz/v1"

    async def query(self, prompt: str, system_prompt: Optional[str] = None) -> tuple[str, int]:
        """Query Together AI API."""
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{self.base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": self.model,
                    "messages": messages,
                    "temperature": 0.3,
                    "max_tokens": 2000,
                },
            )
            response.raise_for_status()
            data = response.json()

            content = data["choices"][0]["message"]["content"]
            tokens = data.get("usage", {}).get("total_tokens", 0)
            return content, tokens

    async def analyze_asset(self, asset, prompt_template: str):
        """Analyze asset."""
        import time
        from llm_asset_oracle.core.models import LLMResponse

        start_time = time.time()
        raw_response, tokens = await self.query(prompt_template)
        latency_ms = (time.time() - start_time) * 1000

        rating = OpenAIProvider._parse_rating(self, raw_response)

        return LLMResponse(
            provider=self.provider_name,
            model=self.model,
            asset_symbol=asset.symbol,
            rating=rating,
            raw_response=raw_response,
            latency_ms=latency_ms,
            tokens_used=tokens,
        )

    _parse_rating = OpenAIProvider._parse_rating
    _create_rating_from_dict = OpenAIProvider._create_rating_from_dict
    _create_default_rating = OpenAIProvider._create_default_rating


# =============================================================================
# Mistral Provider
# =============================================================================

class MistralProvider:
    """Mistral AI provider."""

    provider_name = "mistral"
    default_model = "mistral-large-latest"

    def __init__(self, api_key: str, model: Optional[str] = None):
        self.api_key = api_key
        self.model = model or self.default_model
        self.base_url = "https://api.mistral.ai/v1"

    async def query(self, prompt: str, system_prompt: Optional[str] = None) -> tuple[str, int]:
        """Query Mistral API."""
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{self.base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": self.model,
                    "messages": messages,
                    "temperature": 0.3,
                    "max_tokens": 2000,
                },
            )
            response.raise_for_status()
            data = response.json()

            content = data["choices"][0]["message"]["content"]
            tokens = data.get("usage", {}).get("total_tokens", 0)
            return content, tokens

    async def analyze_asset(self, asset, prompt_template: str):
        """Analyze asset."""
        import time
        from llm_asset_oracle.core.models import LLMResponse

        start_time = time.time()
        raw_response, tokens = await self.query(prompt_template)
        latency_ms = (time.time() - start_time) * 1000

        rating = OpenAIProvider._parse_rating(self, raw_response)

        return LLMResponse(
            provider=self.provider_name,
            model=self.model,
            asset_symbol=asset.symbol,
            rating=rating,
            raw_response=raw_response,
            latency_ms=latency_ms,
            tokens_used=tokens,
        )

    _parse_rating = OpenAIProvider._parse_rating
    _create_rating_from_dict = OpenAIProvider._create_rating_from_dict
    _create_default_rating = OpenAIProvider._create_default_rating
