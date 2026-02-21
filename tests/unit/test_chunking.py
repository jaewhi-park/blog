"""ChunkingEngine 단위 테스트."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, PropertyMock

import pytest

from core.llm.base import LLMResponse
from core.llm.chunking import ChunkingConfig, ChunkingEngine


def _make_client(
    max_context_tokens: int = 10000,
    chars_per_token: int = 4,
) -> MagicMock:
    """토큰 카운팅을 시뮬레이션하는 모의 LLMClient를 생성한다."""
    client = MagicMock()
    type(client).max_context_tokens = PropertyMock(return_value=max_context_tokens)
    client.count_tokens = MagicMock(
        side_effect=lambda text: len(text) // chars_per_token
    )
    client.generate = AsyncMock()
    return client


@pytest.fixture
def config() -> ChunkingConfig:
    return ChunkingConfig(
        chunk_size_tokens=100,
        context_threshold=0.7,
        map_model="test-map-model",
        reduce_model="test-reduce-model",
    )


@pytest.fixture
def client() -> MagicMock:
    return _make_client()


@pytest.fixture
def engine(client: MagicMock, config: ChunkingConfig) -> ChunkingEngine:
    return ChunkingEngine(client, config)


class TestChunkingConfig:
    def test_defaults(self) -> None:
        cfg = ChunkingConfig()
        assert cfg.chunk_size_tokens == 4000
        assert cfg.context_threshold == 0.7
        assert cfg.map_model == "claude-haiku-4-5-20251001"
        assert cfg.reduce_model == "claude-sonnet-4-20250514"


class TestNeedsChunking:
    def test_short_text_no_chunking(self, engine: ChunkingEngine) -> None:
        # max_context=10000, threshold=0.7 → limit=7000 tokens
        # 100 chars → 25 tokens (chars_per_token=4) → 아래
        assert engine.needs_chunking("x" * 100) is False

    def test_long_text_needs_chunking(self, engine: ChunkingEngine) -> None:
        # 7001*4=28004 chars → 7001 tokens → 초과
        assert engine.needs_chunking("x" * 28004) is True

    def test_exact_threshold_no_chunking(self, engine: ChunkingEngine) -> None:
        # 7000*4=28000 chars → 7000 tokens → 정확히 threshold이므로 False
        assert engine.needs_chunking("x" * 28000) is False


class TestSplitChunks:
    def test_short_text_single_chunk(self, engine: ChunkingEngine) -> None:
        text = "Short text"
        chunks = engine.split_chunks(text)
        assert len(chunks) == 1
        assert chunks[0] == text

    def test_long_text_multiple_chunks(self, engine: ChunkingEngine) -> None:
        # chunk_size=100 tokens, 4 chars/token → 400 chars per chunk
        text = "word " * 200  # 1000 chars → 250 tokens → 3+ chunks
        chunks = engine.split_chunks(text)
        assert len(chunks) >= 2

    def test_splits_at_paragraph_boundary(self, engine: ChunkingEngine) -> None:
        # 빈 줄(문단 경계)에서 분할되어야 함
        para1 = "A" * 300
        para2 = "B" * 300
        text = f"{para1}\n\n{para2}"
        chunks = engine.split_chunks(text)

        assert len(chunks) >= 2
        # 첫 청크가 문단 경계에서 끝나야 함
        assert chunks[0].strip().endswith("A" * 10)

    def test_splits_at_heading_boundary(self, engine: ChunkingEngine) -> None:
        section1 = "Content A. " * 30
        section2 = "Content B. " * 30
        text = f"{section1}\n## Section 2\n{section2}"
        chunks = engine.split_chunks(text)

        assert len(chunks) >= 2

    def test_no_empty_chunks(self, engine: ChunkingEngine) -> None:
        text = "word " * 200
        chunks = engine.split_chunks(text)
        assert all(chunk.strip() for chunk in chunks)

    def test_all_content_preserved(self, engine: ChunkingEngine) -> None:
        words = [f"word{i}" for i in range(200)]
        text = " ".join(words)
        chunks = engine.split_chunks(text)
        combined = " ".join(c.strip() for c in chunks)

        # 모든 단어가 보존되어야 함
        for word in words:
            assert word in combined


class TestMapReduce:
    @pytest.mark.asyncio
    async def test_map_reduce_pipeline(
        self,
        engine: ChunkingEngine,
        client: MagicMock,
    ) -> None:
        # 짧은 텍스트 → 1 청크 → map 1회 + reduce 1회
        client.generate.side_effect = [
            LLMResponse(content="Map result 1", model="map-model"),
            LLMResponse(content="Final result", model="reduce-model"),
        ]
        result = await engine.map_reduce(
            content="Short text",
            map_prompt="Summarize this",
            reduce_prompt="Combine summaries",
        )

        assert result.content == "Final result"
        assert client.generate.call_count == 2

    @pytest.mark.asyncio
    async def test_map_uses_map_model(
        self,
        engine: ChunkingEngine,
        client: MagicMock,
    ) -> None:
        client.generate.side_effect = [
            LLMResponse(content="map", model="m"),
            LLMResponse(content="reduce", model="r"),
        ]
        await engine.map_reduce("Short", "map_prompt", "reduce_prompt")

        map_call = client.generate.call_args_list[0]
        request = map_call[0][0]
        assert request.model == "test-map-model"

    @pytest.mark.asyncio
    async def test_reduce_uses_reduce_model(
        self,
        engine: ChunkingEngine,
        client: MagicMock,
    ) -> None:
        client.generate.side_effect = [
            LLMResponse(content="map", model="m"),
            LLMResponse(content="reduce", model="r"),
        ]
        await engine.map_reduce("Short", "map_prompt", "reduce_prompt")

        reduce_call = client.generate.call_args_list[1]
        request = reduce_call[0][0]
        assert request.model == "test-reduce-model"

    @pytest.mark.asyncio
    async def test_reduce_receives_combined_maps(
        self,
        engine: ChunkingEngine,
        client: MagicMock,
    ) -> None:
        # 긴 텍스트 → 여러 청크 → 여러 map 결과가 reduce에 전달
        long_text = "word " * 200  # 여러 청크
        chunks = engine.split_chunks(long_text)
        n_chunks = len(chunks)

        map_responses = [
            LLMResponse(content=f"Summary {i}", model="m") for i in range(n_chunks)
        ]
        reduce_response = LLMResponse(content="Final", model="r")
        client.generate.side_effect = [*map_responses, reduce_response]

        await engine.map_reduce(long_text, "map", "reduce")

        # reduce 호출의 user_prompt에 모든 map 결과가 포함되어야 함
        reduce_call = client.generate.call_args_list[-1]
        reduce_request = reduce_call[0][0]
        for i in range(n_chunks):
            assert f"Summary {i}" in reduce_request.user_prompt

    @pytest.mark.asyncio
    async def test_map_prompts_passed_correctly(
        self,
        engine: ChunkingEngine,
        client: MagicMock,
    ) -> None:
        client.generate.side_effect = [
            LLMResponse(content="map", model="m"),
            LLMResponse(content="reduce", model="r"),
        ]
        await engine.map_reduce("Short", "My map prompt", "My reduce prompt")

        map_call = client.generate.call_args_list[0]
        assert map_call[0][0].system_prompt == "My map prompt"

        reduce_call = client.generate.call_args_list[1]
        assert reduce_call[0][0].system_prompt == "My reduce prompt"

    @pytest.mark.asyncio
    async def test_returns_llm_response(
        self,
        engine: ChunkingEngine,
        client: MagicMock,
    ) -> None:
        client.generate.side_effect = [
            LLMResponse(content="map", model="m"),
            LLMResponse(content="final", model="reduce-model", usage={"total": 100}),
        ]
        result = await engine.map_reduce("Short", "map", "reduce")

        assert isinstance(result, LLMResponse)
        assert result.model == "reduce-model"
