"""Llama (Ollama) LLM 클라이언트."""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any

import httpx

from core.exceptions import LLMError
from core.llm.base import LLMRequest, LLMResponse


class LlamaClient:
    """Ollama REST API 클라이언트."""

    def __init__(self, config: dict[str, Any]) -> None:
        """
        Args:
            config: 프로바이더 설정 dict (endpoint, models 등).
        """
        self._endpoint = config.get("endpoint", "http://localhost:11434")
        self._config = config
        self._default_model = config.get("default_model", "llama3.1")
        self._models: list[dict] = config.get("models", [])

    @property
    def provider_name(self) -> str:
        return "llama"

    @property
    def max_context_tokens(self) -> int:
        for m in self._models:
            if m["id"] == self._default_model:
                return m.get("max_context_tokens", 128000)
        return 128000

    @property
    def available_models(self) -> list[dict]:
        return self._models

    async def generate(self, request: LLMRequest) -> LLMResponse:
        """Ollama API를 호출하여 응답을 생성한다."""
        model = request.model or self._default_model
        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                response = await client.post(
                    f"{self._endpoint}/api/chat",
                    json={
                        "model": model,
                        "messages": [
                            {"role": "system", "content": request.system_prompt},
                            {"role": "user", "content": request.user_prompt},
                        ],
                        "stream": False,
                        "options": {
                            "temperature": request.temperature,
                            "num_predict": request.max_tokens,
                        },
                    },
                )
                response.raise_for_status()
                data = response.json()
                return LLMResponse(
                    content=data["message"]["content"],
                    model=model,
                    usage={
                        "input_tokens": data.get("prompt_eval_count", 0),
                        "output_tokens": data.get("eval_count", 0),
                    },
                )
        except httpx.HTTPError as e:
            raise LLMError(f"Ollama API 에러: {e}") from e

    async def generate_stream(self, request: LLMRequest) -> AsyncIterator[str]:
        """Ollama API 스트리밍 응답을 생성한다."""
        model = request.model or self._default_model
        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                async with client.stream(
                    "POST",
                    f"{self._endpoint}/api/chat",
                    json={
                        "model": model,
                        "messages": [
                            {"role": "system", "content": request.system_prompt},
                            {"role": "user", "content": request.user_prompt},
                        ],
                        "stream": True,
                        "options": {
                            "temperature": request.temperature,
                            "num_predict": request.max_tokens,
                        },
                    },
                ) as response:
                    import json

                    async for line in response.aiter_lines():
                        if line.strip():
                            data = json.loads(line)
                            if "message" in data and "content" in data["message"]:
                                yield data["message"]["content"]
        except httpx.HTTPError as e:
            raise LLMError(f"Ollama API 에러: {e}") from e

    def count_tokens(self, text: str) -> int:
        """근사치로 토큰을 카운트한다 (4자당 1토큰)."""
        return len(text) // 4
