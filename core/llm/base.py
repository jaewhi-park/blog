"""LLM 클라이언트 인터페이스."""

from __future__ import annotations

from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable


@dataclass
class LLMRequest:
    """LLM 요청."""

    system_prompt: str
    user_prompt: str
    messages: list[dict[str, str]] | None = None
    model: str | None = None
    temperature: float = 0.7
    max_tokens: int = 4096


@dataclass
class LLMResponse:
    """LLM 응답."""

    content: str
    model: str
    usage: dict[str, int] = field(default_factory=dict)


@runtime_checkable
class LLMClient(Protocol):
    """LLM 프로바이더 통합 인터페이스."""

    @property
    def provider_name(self) -> str: ...

    @property
    def max_context_tokens(self) -> int: ...

    @property
    def available_models(self) -> list[dict]: ...

    async def generate(self, request: LLMRequest) -> LLMResponse: ...

    async def generate_stream(self, request: LLMRequest) -> AsyncIterator[str]: ...

    def count_tokens(self, text: str) -> int: ...
