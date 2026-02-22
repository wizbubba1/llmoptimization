"""
Query Engine - Core async engine for querying LLMs via OpenRouter.

Supports:
- Text-only queries (all modes)
- Vision queries with image (Mode D)
- Multi-model concurrent queries
- Same-model repeated queries (Mode C)
"""

import asyncio
import base64
import logging
import time
from dataclasses import dataclass
from typing import Optional, Callable, Awaitable

import httpx

from llm_asset_oracle.models.registry import MODELS_BY_ID, get_model_name

logger = logging.getLogger(__name__)


@dataclass
class QueryResult:
    """Result from a single LLM query."""

    model_id: str
    model_name: str
    content: str  # Raw response text
    success: bool
    error: Optional[str] = None
    latency_ms: float = 0
    run_index: int = 0  # For Mode C (which run number)


# Callback for streaming progress
ProgressCallback = Callable[[QueryResult], Awaitable[None]]


class QueryEngine:
    """
    Async engine for querying LLMs via OpenRouter.

    Usage:
        engine = QueryEngine(api_key="sk-or-...")
        results = await engine.query_multiple(model_ids, prompt)
    """

    BASE_URL = "https://openrouter.ai/api/v1"

    def __init__(
        self,
        api_key: str,
        timeout: float = 120.0,
        max_concurrent: int = 8,
    ):
        self.api_key = api_key
        self.timeout = timeout
        self._semaphore = asyncio.Semaphore(max_concurrent)

    async def query_text(
        self,
        model_id: str,
        prompt: str,
        max_tokens: int = 500,
        run_index: int = 0,
    ) -> QueryResult:
        """Query a model with a text-only prompt."""
        model_name = get_model_name(model_id)
        start = time.time()

        async with self._semaphore:
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    resp = await client.post(
                        f"{self.BASE_URL}/chat/completions",
                        headers={
                            "Authorization": f"Bearer {self.api_key}",
                            "HTTP-Referer": "https://llm-asset-oracle.app",
                            "X-Title": "LLM Optimization Agent",
                            "Content-Type": "application/json",
                        },
                        json={
                            "model": model_id,
                            "messages": [{"role": "user", "content": prompt}],
                            "max_tokens": max_tokens,
                        },
                    )

                    latency = (time.time() - start) * 1000

                    if resp.status_code != 200:
                        return QueryResult(
                            model_id=model_id,
                            model_name=model_name,
                            content="",
                            success=False,
                            error=f"HTTP {resp.status_code}",
                            latency_ms=latency,
                            run_index=run_index,
                        )

                    data = resp.json()
                    content = data["choices"][0]["message"]["content"]

                    return QueryResult(
                        model_id=model_id,
                        model_name=model_name,
                        content=content,
                        success=True,
                        latency_ms=latency,
                        run_index=run_index,
                    )

            except asyncio.TimeoutError:
                return QueryResult(
                    model_id=model_id,
                    model_name=model_name,
                    content="",
                    success=False,
                    error="Timeout",
                    latency_ms=(time.time() - start) * 1000,
                    run_index=run_index,
                )
            except Exception as e:
                return QueryResult(
                    model_id=model_id,
                    model_name=model_name,
                    content="",
                    success=False,
                    error=str(e),
                    latency_ms=(time.time() - start) * 1000,
                    run_index=run_index,
                )

    async def query_vision(
        self,
        model_id: str,
        prompt: str,
        image_base64: str,
        image_media_type: str = "image/png",
        max_tokens: int = 500,
    ) -> QueryResult:
        """Query a vision model with text + image."""
        model_name = get_model_name(model_id)
        start = time.time()

        async with self._semaphore:
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    resp = await client.post(
                        f"{self.BASE_URL}/chat/completions",
                        headers={
                            "Authorization": f"Bearer {self.api_key}",
                            "HTTP-Referer": "https://llm-asset-oracle.app",
                            "X-Title": "LLM Optimization Agent",
                            "Content-Type": "application/json",
                        },
                        json={
                            "model": model_id,
                            "messages": [{
                                "role": "user",
                                "content": [
                                    {"type": "text", "text": prompt},
                                    {
                                        "type": "image_url",
                                        "image_url": {
                                            "url": f"data:{image_media_type};base64,{image_base64}",
                                        },
                                    },
                                ],
                            }],
                            "max_tokens": max_tokens,
                        },
                    )

                    latency = (time.time() - start) * 1000

                    if resp.status_code != 200:
                        return QueryResult(
                            model_id=model_id,
                            model_name=model_name,
                            content="",
                            success=False,
                            error=f"HTTP {resp.status_code}",
                            latency_ms=latency,
                        )

                    data = resp.json()
                    content = data["choices"][0]["message"]["content"]

                    return QueryResult(
                        model_id=model_id,
                        model_name=model_name,
                        content=content,
                        success=True,
                        latency_ms=latency,
                    )

            except asyncio.TimeoutError:
                return QueryResult(
                    model_id=model_id,
                    model_name=model_name,
                    content="",
                    success=False,
                    error="Timeout",
                    latency_ms=(time.time() - start) * 1000,
                )
            except Exception as e:
                return QueryResult(
                    model_id=model_id,
                    model_name=model_name,
                    content="",
                    success=False,
                    error=str(e),
                    latency_ms=(time.time() - start) * 1000,
                )

    async def query_multiple(
        self,
        model_ids: list[str],
        prompt: str,
        max_tokens: int = 500,
        on_result: Optional[ProgressCallback] = None,
    ) -> list[QueryResult]:
        """Query multiple models concurrently with the same prompt."""

        async def _query_with_callback(model_id: str) -> QueryResult:
            result = await self.query_text(model_id, prompt, max_tokens)
            if on_result:
                await on_result(result)
            return result

        tasks = [_query_with_callback(mid) for mid in model_ids]
        return list(await asyncio.gather(*tasks))

    async def query_multiple_vision(
        self,
        model_ids: list[str],
        prompt: str,
        image_base64: str,
        image_media_type: str = "image/png",
        max_tokens: int = 500,
        on_result: Optional[ProgressCallback] = None,
    ) -> list[QueryResult]:
        """Query multiple vision models concurrently with text + image."""

        async def _query_with_callback(model_id: str) -> QueryResult:
            result = await self.query_vision(
                model_id, prompt, image_base64, image_media_type, max_tokens
            )
            if on_result:
                await on_result(result)
            return result

        tasks = [_query_with_callback(mid) for mid in model_ids]
        return list(await asyncio.gather(*tasks))

    async def query_repeated(
        self,
        model_id: str,
        prompt: str,
        runs: int = 5,
        max_tokens: int = 500,
        on_result: Optional[ProgressCallback] = None,
    ) -> list[QueryResult]:
        """Query the same model multiple times (for Mode C consistency testing)."""

        async def _query_with_callback(run_idx: int) -> QueryResult:
            result = await self.query_text(model_id, prompt, max_tokens, run_index=run_idx)
            if on_result:
                await on_result(result)
            return result

        tasks = [_query_with_callback(i) for i in range(runs)]
        return list(await asyncio.gather(*tasks))
