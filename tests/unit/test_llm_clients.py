"""LLM 클라이언트 단위 테스트 (mock 기반)."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import httpx
import openai
import pytest

from core.exceptions import LLMAuthError, LLMError, LLMRateLimitError
from core.llm.base import LLMRequest, LLMResponse
from core.llm.claude_client import ClaudeClient
from core.llm.llama_client import LlamaClient
from core.llm.openai_client import OpenAIClient


# ── 공통 fixture ─────────────────────────────────────────────


@pytest.fixture()
def llm_request() -> LLMRequest:
    return LLMRequest(
        system_prompt="You are helpful.",
        user_prompt="Hello",
        model="test-model",
    )


CLAUDE_CONFIG: dict = {
    "default_model": "claude-sonnet-4-20250514",
    "models": [
        {"id": "claude-sonnet-4-20250514", "max_context_tokens": 200000},
    ],
}

OPENAI_CONFIG: dict = {
    "default_model": "gpt-4o",
    "models": [
        {"id": "gpt-4o", "max_context_tokens": 128000},
    ],
}

LLAMA_CONFIG: dict = {
    "default_model": "llama3.1",
    "endpoint": "http://localhost:11434",
    "models": [
        {"id": "llama3.1", "max_context_tokens": 128000},
    ],
}


# ── ClaudeClient ─────────────────────────────────────────────


class TestClaudeClient:
    """ClaudeClient 단위 테스트."""

    def test_provider_name(self) -> None:
        client = ClaudeClient(api_key="test", config=CLAUDE_CONFIG)
        assert client.provider_name == "claude"

    def test_max_context_tokens(self) -> None:
        client = ClaudeClient(api_key="test", config=CLAUDE_CONFIG)
        assert client.max_context_tokens == 200000

    def test_available_models(self) -> None:
        client = ClaudeClient(api_key="test", config=CLAUDE_CONFIG)
        assert len(client.available_models) == 1

    @pytest.mark.asyncio()
    async def test_generate_success(self, llm_request: LLMRequest) -> None:
        client = ClaudeClient(api_key="test", config=CLAUDE_CONFIG)

        mock_response = MagicMock()
        mock_response.content = [MagicMock(text="Hello back!")]
        mock_response.usage.input_tokens = 10
        mock_response.usage.output_tokens = 5

        client._client.messages.create = AsyncMock(return_value=mock_response)

        response = await client.generate(llm_request)
        assert isinstance(response, LLMResponse)
        assert response.content == "Hello back!"
        assert response.usage["input_tokens"] == 10

    @pytest.mark.asyncio()
    async def test_generate_auth_error(self, llm_request: LLMRequest) -> None:
        import anthropic

        client = ClaudeClient(api_key="bad-key", config=CLAUDE_CONFIG)
        client._client.messages.create = AsyncMock(
            side_effect=anthropic.AuthenticationError(
                message="invalid key",
                response=MagicMock(status_code=401),
                body=None,
            )
        )
        with pytest.raises(LLMAuthError):
            await client.generate(llm_request)

    @pytest.mark.asyncio()
    async def test_generate_rate_limit_error(self, llm_request: LLMRequest) -> None:
        import anthropic

        client = ClaudeClient(api_key="test", config=CLAUDE_CONFIG)
        client._client.messages.create = AsyncMock(
            side_effect=anthropic.RateLimitError(
                message="rate limited",
                response=MagicMock(status_code=429),
                body=None,
            )
        )
        # tenacity가 3회 재시도 후 LLMRateLimitError를 다시 던짐
        with pytest.raises(LLMRateLimitError):
            await client.generate(llm_request)
        assert client._client.messages.create.call_count == 3

    @pytest.mark.asyncio()
    async def test_generate_api_error(self, llm_request: LLMRequest) -> None:
        import anthropic

        client = ClaudeClient(api_key="test", config=CLAUDE_CONFIG)
        client._client.messages.create = AsyncMock(
            side_effect=anthropic.APIError(
                message="server error",
                request=MagicMock(),
                body=None,
            )
        )
        with pytest.raises(LLMError):
            await client.generate(llm_request)

    @pytest.mark.asyncio()
    async def test_generate_empty_response(self, llm_request: LLMRequest) -> None:
        client = ClaudeClient(api_key="test", config=CLAUDE_CONFIG)

        mock_response = MagicMock()
        mock_response.content = []

        client._client.messages.create = AsyncMock(return_value=mock_response)

        with pytest.raises(LLMError, match="빈 응답"):
            await client.generate(llm_request)


# ── OpenAIClient ─────────────────────────────────────────────


class TestOpenAIClient:
    """OpenAIClient 단위 테스트."""

    def test_provider_name(self) -> None:
        client = OpenAIClient(api_key="test", config=OPENAI_CONFIG)
        assert client.provider_name == "openai"

    def test_max_context_tokens(self) -> None:
        client = OpenAIClient(api_key="test", config=OPENAI_CONFIG)
        assert client.max_context_tokens == 128000

    @pytest.mark.asyncio()
    async def test_generate_success(self, llm_request: LLMRequest) -> None:
        client = OpenAIClient(api_key="test", config=OPENAI_CONFIG)

        mock_choice = MagicMock()
        mock_choice.message.content = "GPT says hi"
        mock_usage = MagicMock()
        mock_usage.prompt_tokens = 8
        mock_usage.completion_tokens = 4
        mock_response = MagicMock()
        mock_response.choices = [mock_choice]
        mock_response.usage = mock_usage

        client._client.chat.completions.create = AsyncMock(return_value=mock_response)

        response = await client.generate(llm_request)
        assert response.content == "GPT says hi"
        assert response.usage["input_tokens"] == 8
        assert response.usage["output_tokens"] == 4

    @pytest.mark.asyncio()
    async def test_generate_rate_limit_error(self, llm_request: LLMRequest) -> None:
        client = OpenAIClient(api_key="test", config=OPENAI_CONFIG)
        client._client.chat.completions.create = AsyncMock(
            side_effect=openai.RateLimitError(
                message="rate limited",
                response=MagicMock(status_code=429),
                body=None,
            )
        )
        with pytest.raises(LLMRateLimitError):
            await client.generate(llm_request)
        assert client._client.chat.completions.create.call_count == 3

    @pytest.mark.asyncio()
    async def test_generate_empty_choices(self, llm_request: LLMRequest) -> None:
        client = OpenAIClient(api_key="test", config=OPENAI_CONFIG)

        mock_response = MagicMock()
        mock_response.choices = []

        client._client.chat.completions.create = AsyncMock(return_value=mock_response)

        with pytest.raises(LLMError, match="빈 응답"):
            await client.generate(llm_request)


# ── LlamaClient ──────────────────────────────────────────────


class TestLlamaClient:
    """LlamaClient 단위 테스트."""

    def test_provider_name(self) -> None:
        client = LlamaClient(config=LLAMA_CONFIG)
        assert client.provider_name == "llama"

    def test_max_context_tokens(self) -> None:
        client = LlamaClient(config=LLAMA_CONFIG)
        assert client.max_context_tokens == 128000

    def test_count_tokens(self) -> None:
        client = LlamaClient(config=LLAMA_CONFIG)
        # "hello world" = 11 chars → 11 // 4 = 2
        assert client.count_tokens("hello world") == 2

    @pytest.mark.asyncio()
    async def test_generate_success(self, llm_request: LLMRequest) -> None:
        client = LlamaClient(config=LLAMA_CONFIG)

        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {
            "message": {"content": "Llama says hi"},
            "prompt_eval_count": 6,
            "eval_count": 3,
        }
        client._client.post = AsyncMock(return_value=mock_response)

        response = await client.generate(llm_request)
        assert response.content == "Llama says hi"
        assert response.usage["input_tokens"] == 6
        assert response.usage["output_tokens"] == 3

    @pytest.mark.asyncio()
    async def test_generate_empty_response(self, llm_request: LLMRequest) -> None:
        client = LlamaClient(config=LLAMA_CONFIG)

        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {}
        client._client.post = AsyncMock(return_value=mock_response)

        with pytest.raises(LLMError, match="빈 응답"):
            await client.generate(llm_request)

    @pytest.mark.asyncio()
    async def test_generate_http_error(self, llm_request: LLMRequest) -> None:
        client = LlamaClient(config=LLAMA_CONFIG)
        client._client.post = AsyncMock(
            side_effect=httpx.ConnectError("connection refused")
        )
        with pytest.raises(LLMError, match="Ollama API 에러"):
            await client.generate(llm_request)
