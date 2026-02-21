"""Claude (Anthropic) LLM 클라이언트."""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any

import anthropic
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from core.exceptions import LLMAuthError, LLMError, LLMRateLimitError
from core.llm.base import LLMRequest, LLMResponse

_RETRY_DECORATOR = retry(
    retry=retry_if_exception_type(LLMRateLimitError),
    wait=wait_exponential(multiplier=1, min=2, max=60),
    stop=stop_after_attempt(3),
    reraise=True,
)


class ClaudeClient:
    """Anthropic Claude API 클라이언트."""

    def __init__(self, api_key: str, config: dict[str, Any]) -> None:
        """
        Args:
            api_key: Anthropic API 키.
            config: 프로바이더 설정 dict (models, default_model 등).
        """
        self._client = anthropic.AsyncAnthropic(api_key=api_key)
        self._config = config
        self._default_model = config.get("default_model", "claude-sonnet-4-20250514")
        self._models: list[dict] = config.get("models", [])

    @property
    def provider_name(self) -> str:
        return "claude"

    @property
    def max_context_tokens(self) -> int:
        for m in self._models:
            if m["id"] == self._default_model:
                return m.get("max_context_tokens", 200000)
        return 200000

    @property
    def available_models(self) -> list[dict]:
        return self._models

    @_RETRY_DECORATOR
    async def generate(self, request: LLMRequest) -> LLMResponse:
        """Claude API를 호출하여 응답을 생성한다."""
        model = request.model or self._default_model
        try:
            response = await self._client.messages.create(
                model=model,
                max_tokens=request.max_tokens,
                temperature=request.temperature,
                system=request.system_prompt,
                messages=[{"role": "user", "content": request.user_prompt}],
            )
            if not response.content:
                raise LLMError("Claude API가 빈 응답을 반환했습니다.")
            return LLMResponse(
                content=response.content[0].text,
                model=model,
                usage={
                    "input_tokens": response.usage.input_tokens,
                    "output_tokens": response.usage.output_tokens,
                },
            )
        except anthropic.AuthenticationError as e:
            raise LLMAuthError(f"Claude 인증 실패: {e}") from e
        except anthropic.RateLimitError as e:
            raise LLMRateLimitError(f"Claude Rate Limit 초과: {e}") from e
        except anthropic.APIError as e:
            raise LLMError(f"Claude API 에러: {e}") from e

    async def generate_stream(self, request: LLMRequest) -> AsyncIterator[str]:
        """Claude API 스트리밍 응답을 생성한다."""
        model = request.model or self._default_model
        try:
            async with self._client.messages.stream(
                model=model,
                max_tokens=request.max_tokens,
                temperature=request.temperature,
                system=request.system_prompt,
                messages=[{"role": "user", "content": request.user_prompt}],
            ) as stream:
                async for text in stream.text_stream:
                    yield text
        except anthropic.AuthenticationError as e:
            raise LLMAuthError(f"Claude 인증 실패: {e}") from e
        except anthropic.RateLimitError as e:
            raise LLMRateLimitError(f"Claude Rate Limit 초과: {e}") from e
        except anthropic.APIError as e:
            raise LLMError(f"Claude API 에러: {e}") from e

    def count_tokens(self, text: str) -> int:
        """anthropic 토큰 카운팅을 사용한다."""
        return self._client.count_tokens(text)
