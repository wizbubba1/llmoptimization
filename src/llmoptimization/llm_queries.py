"""LLM querying utilities for standardized prompt execution."""

from __future__ import annotations

import asyncio
import dataclasses
from typing import Any, Iterable, List, Mapping

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from .config import Config


@dataclasses.dataclass(slots=True)
class PromptResult:
    """Represents a single LLM response."""

    model: str
    prompt_id: str
    asset: str
    iteration: int
    text: str
    usage: Mapping[str, Any]


class PromptRunner:
    """Execute standardized prompts across multiple LLM providers."""

    def __init__(self, config: Config) -> None:
        self.config = config
        self.model_configs = config.get("llm.models", [])
        if not self.model_configs:
            raise ValueError("No LLM models configured")

    async def run_prompts(
        self, prompts: Mapping[str, str], assets: Iterable[str], iterations: int = 5
    ) -> List[PromptResult]:
        tasks = []
        for model_cfg in self.model_configs:
            for prompt_id, template in prompts.items():
                for asset in assets:
                    for iteration in range(iterations):
                        tasks.append(
                            self._dispatch(model_cfg, prompt_id, template.format(asset=asset), asset, iteration)
                        )
        return await asyncio.gather(*tasks)

    @retry(wait=wait_exponential(multiplier=1, min=1, max=30), stop=stop_after_attempt(5))
    async def _dispatch(
        self, model_cfg: Mapping[str, Any], prompt_id: str, prompt: str, asset: str, iteration: int
    ) -> PromptResult:
        provider = model_cfg.get("provider")
        if provider == "openai":
            response = await self._call_openai(model_cfg, prompt)
        elif provider == "anthropic":
            response = await self._call_anthropic(model_cfg, prompt)
        elif provider == "google":
            response = await self._call_gemini(model_cfg, prompt)
        elif provider == "meta":
            response = await self._call_llama(model_cfg, prompt)
        else:
            raise ValueError(f"Unsupported provider: {provider}")
        return PromptResult(
            model=model_cfg.get("name", provider),
            prompt_id=prompt_id,
            asset=asset,
            iteration=iteration,
            text=response.get("text", ""),
            usage=response.get("usage", {}),
        )

    async def _call_openai(self, model_cfg: Mapping[str, Any], prompt: str) -> Mapping[str, Any]:
        import openai  # type: ignore

        client = openai.AsyncOpenAI(api_key=model_cfg.get("api_key"))
        completion = await client.chat.completions.create(
            model=model_cfg.get("name"),
            messages=[{"role": "user", "content": prompt}],
            temperature=self.config.get("llm.temperature", 0.3),
            max_tokens=self.config.get("llm.max_tokens", 1000),
            top_p=self.config.get("llm.top_p", 1.0),
            frequency_penalty=self.config.get("llm.frequency_penalty", 0),
            presence_penalty=self.config.get("llm.presence_penalty", 0),
        )
        choice = completion.choices[0]
        return {"text": choice.message.content, "usage": completion.usage or {}}

    async def _call_anthropic(self, model_cfg: Mapping[str, Any], prompt: str) -> Mapping[str, Any]:
        import anthropic  # type: ignore

        client = anthropic.AsyncAnthropic(api_key=model_cfg.get("api_key"))
        completion = await client.messages.create(
            model=model_cfg.get("name"),
            max_tokens=self.config.get("llm.max_tokens", 1000),
            temperature=self.config.get("llm.temperature", 0.3),
            system="You are an unbiased cryptocurrency analyst.",
            messages=[{"role": "user", "content": prompt}],
        )
        text = "".join(block.text for block in completion.content if getattr(block, "type", "") == "text")
        return {"text": text, "usage": getattr(completion, "usage", {})}

    async def _call_gemini(self, model_cfg: Mapping[str, Any], prompt: str) -> Mapping[str, Any]:
        from google.generativeai import GenerativeModel  # type: ignore

        model = GenerativeModel(model_cfg.get("name"), api_key=model_cfg.get("api_key"))
        response = await asyncio.to_thread(model.generate_content, prompt)
        text = "\n".join(part.text for part in response.candidates[0].content.parts)
        return {"text": text, "usage": getattr(response, "usage_metadata", {})}

    async def _call_llama(self, model_cfg: Mapping[str, Any], prompt: str) -> Mapping[str, Any]:
        endpoint = model_cfg.get("endpoint")
        if not endpoint:
            raise ValueError("LLaMA endpoint is required")
        headers = {"Authorization": f"Bearer {model_cfg.get('api_key')}"}
        payload = {
            "model": model_cfg.get("name"),
            "prompt": prompt,
            "temperature": self.config.get("llm.temperature", 0.3),
            "max_tokens": self.config.get("llm.max_tokens", 1000),
        }
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(endpoint, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()
        text = data.get("choices", [{}])[0].get("text", "")
        return {"text": text, "usage": data.get("usage", {})}

