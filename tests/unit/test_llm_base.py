"""LLM base 모듈 단위 테스트."""

from __future__ import annotations

from core.llm.base import LLMRequest, LLMResponse


class TestLLMRequest:
    """LLMRequest 데이터클래스 테스트."""

    def test_defaults(self) -> None:
        req = LLMRequest(system_prompt="sys", user_prompt="user")
        assert req.model is None
        assert req.temperature == 0.7
        assert req.max_tokens == 4096

    def test_custom_values(self) -> None:
        req = LLMRequest(
            system_prompt="sys",
            user_prompt="user",
            model="gpt-4o",
            temperature=0.3,
            max_tokens=2048,
        )
        assert req.model == "gpt-4o"
        assert req.temperature == 0.3
        assert req.max_tokens == 2048


class TestLLMResponse:
    """LLMResponse 데이터클래스 테스트."""

    def test_defaults(self) -> None:
        resp = LLMResponse(content="hello", model="test")
        assert resp.usage == {}

    def test_with_usage(self) -> None:
        resp = LLMResponse(
            content="hello",
            model="test",
            usage={"input_tokens": 10, "output_tokens": 20},
        )
        assert resp.usage["input_tokens"] == 10
        assert resp.usage["output_tokens"] == 20
