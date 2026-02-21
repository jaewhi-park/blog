"""OpenAI LLM 클라이언트."""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any

import openai

from core.exceptions import LLMAuthError, LLMError, LLMRateLimitError
from core.llm.base import LLMRequest, LLMResponse


class OpenAIClient:
    """OpenAI API 클라이언트."""

    def __init__(self, api_key: str, config: dict[str, Any]) -> None:
        """
        Args:
            api_key: OpenAI API 키.
            config: 프로바이더 설정 dict.
        """
        self._client = openai.AsyncOpenAI(api_key=api_key)
        self._config = config
        self._default_model = config.get("default_model", "gpt-4o")
        self._models: list[dict] = config.get("models", [])

    @property
    def provider_name(self) -> str:
        return "openai"

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
        """OpenAI API를 호출하여 응답을 생성한다."""
        model = request.model or self._default_model
        try:
            response = await self._client.chat.completions.create(
                model=model,
                max_tokens=request.max_tokens,
                temperature=request.temperature,
                messages=[
                    {"role": "system", "content": request.system_prompt},
                    {"role": "user", "content": request.user_prompt},
                ],
            )
            choice = response.choices[0]
            usage = response.usage
            return LLMResponse(
                content=choice.message.content or "",
                model=model,
                usage={
                    "input_tokens": usage.prompt_tokens if usage else 0,
                    "output_tokens": usage.completion_tokens if usage else 0,
                },
            )
        except openai.AuthenticationError as e:
            raise LLMAuthError(f"OpenAI 인증 실패: {e}") from e
        except openai.RateLimitError as e:
            raise LLMRateLimitError(f"OpenAI Rate Limit 초과: {e}") from e
        except openai.APIError as e:
            raise LLMError(f"OpenAI API 에러: {e}") from e

    async def generate_stream(self, request: LLMRequest) -> AsyncIterator[str]:
        """OpenAI API 스트리밍 응답을 생성한다."""
        model = request.model or self._default_model
        try:
            stream = await self._client.chat.completions.create(
                model=model,
                max_tokens=request.max_tokens,
                temperature=request.temperature,
                messages=[
                    {"role": "system", "content": request.system_prompt},
                    {"role": "user", "content": request.user_prompt},
                ],
                stream=True,
            )
            async for chunk in stream:
                if chunk.choices and chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
        except openai.AuthenticationError as e:
            raise LLMAuthError(f"OpenAI 인증 실패: {e}") from e
        except openai.RateLimitError as e:
            raise LLMRateLimitError(f"OpenAI Rate Limit 초과: {e}") from e
        except openai.APIError as e:
            raise LLMError(f"OpenAI API 에러: {e}") from e

    def count_tokens(self, text: str) -> int:
        """tiktoken을 사용하여 토큰을 카운트한다."""
        import tiktoken

        enc = tiktoken.encoding_for_model(self._default_model)
        return len(enc.encode(text))
