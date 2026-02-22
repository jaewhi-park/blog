"""ContentPipeline 통합 테스트 — 모든 의존성을 모킹하여 파이프라인 흐름을 검증."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, PropertyMock

import pytest

from core.content.image_manager import ImageInfo
from core.content.reference_manager import ReferenceManager
from core.content.template_manager import PromptTemplate, TemplateManager
from core.llm.base import LLMResponse
from core.llm.chunking import ChunkingConfig, ChunkingEngine
from core.pipeline import ContentPipeline, WriteRequest, WriteResult
from core.sources.aggregator import AggregatedContent, SourceAggregator, SourceInput


def _mock_llm_client(
    response_content: str = "Generated blog post",
    max_context_tokens: int = 200000,
) -> MagicMock:
    """모의 LLMClient를 생성한다."""
    client = MagicMock()
    type(client).max_context_tokens = PropertyMock(return_value=max_context_tokens)
    client.count_tokens = MagicMock(side_effect=lambda text: len(text) // 4)
    client.generate = AsyncMock(
        return_value=LLMResponse(
            content=response_content,
            model="test-model",
            usage={"input_tokens": 100, "output_tokens": 200},
        )
    )
    return client


def _mock_factory(client: MagicMock | None = None) -> MagicMock:
    """모의 LLMFactory를 생성한다."""
    factory = MagicMock()
    factory.create.return_value = client or _mock_llm_client()
    return factory


def _mock_aggregator() -> AsyncMock:
    """모의 SourceAggregator를 생성한다."""
    aggregator = AsyncMock(spec=SourceAggregator)
    aggregator.aggregate.return_value = AggregatedContent(
        combined_text="Aggregated source text",
        sources=[],
        images=[ImageInfo(filename="fig1.png", source="pdf_extract", page=1)],
        image_data={"fig1.png": b"png-bytes"},
        total_tokens_estimate=100,
    )
    return aggregator


@pytest.fixture
def client() -> MagicMock:
    return _mock_llm_client()


@pytest.fixture
def factory(client: MagicMock) -> MagicMock:
    return _mock_factory(client)


@pytest.fixture
def aggregator() -> AsyncMock:
    return _mock_aggregator()


@pytest.fixture
def pipeline(factory: MagicMock, aggregator: AsyncMock) -> ContentPipeline:
    return ContentPipeline(
        llm_factory=factory,
        source_aggregator=aggregator,
    )


class TestDirectMode:
    @pytest.mark.asyncio
    async def test_returns_content_as_is(self, pipeline: ContentPipeline) -> None:
        request = WriteRequest(
            mode="direct",
            content="My blog post content",
            title="Test Post",
            tags=["test"],
        )
        result = await pipeline.execute(request)

        assert result.content == "My blog post content"
        assert result.metadata.title == "Test Post"
        assert result.llm_usage is None

    @pytest.mark.asyncio
    async def test_no_llm_call(
        self,
        pipeline: ContentPipeline,
        client: MagicMock,
    ) -> None:
        request = WriteRequest(mode="direct", content="Text", title="T")
        await pipeline.execute(request)

        client.generate.assert_not_called()

    @pytest.mark.asyncio
    async def test_metadata_no_llm_flags(self, pipeline: ContentPipeline) -> None:
        request = WriteRequest(mode="direct", content="Text", title="T")
        result = await pipeline.execute(request)

        assert result.metadata.llm_assisted is False
        assert result.metadata.llm_generated is False


class TestAutoMode:
    @pytest.mark.asyncio
    async def test_generates_content(
        self,
        pipeline: ContentPipeline,
        client: MagicMock,
    ) -> None:
        request = WriteRequest(
            mode="auto",
            title="AI Overview",
            prompt="Write about transformers",
            provider="claude",
            model="test-model",
        )
        result = await pipeline.execute(request)

        assert result.content == "Generated blog post"
        assert result.llm_usage is not None
        client.generate.assert_called_once()

    @pytest.mark.asyncio
    async def test_with_sources(
        self,
        pipeline: ContentPipeline,
        aggregator: AsyncMock,
        client: MagicMock,
    ) -> None:
        sources = [SourceInput(source_type="url", path_or_url="https://example.com")]
        request = WriteRequest(
            mode="auto",
            sources=sources,
            title="Summary",
            prompt="Summarize this",
        )
        result = await pipeline.execute(request)

        aggregator.aggregate.assert_called_once_with(sources)
        assert len(result.images) == 1
        assert result.image_data["fig1.png"] == b"png-bytes"

        # user_prompt에 소스 텍스트가 포함되어야 함
        call_args = client.generate.call_args[0][0]
        assert "Aggregated source text" in call_args.user_prompt

    @pytest.mark.asyncio
    async def test_metadata_llm_generated(self, pipeline: ContentPipeline) -> None:
        request = WriteRequest(
            mode="auto",
            title="T",
            prompt="P",
            model="test-model",
        )
        result = await pipeline.execute(request)

        assert result.metadata.llm_generated is True
        assert result.metadata.llm_assisted is False

    @pytest.mark.asyncio
    async def test_uses_specified_provider(
        self,
        pipeline: ContentPipeline,
        factory: MagicMock,
    ) -> None:
        request = WriteRequest(
            mode="auto",
            title="T",
            prompt="P",
            provider="openai",
        )
        await pipeline.execute(request)

        factory.create.assert_called_with("openai")


class TestPairMode:
    @pytest.mark.asyncio
    async def test_get_feedback(
        self,
        pipeline: ContentPipeline,
        client: MagicMock,
    ) -> None:
        client.generate.return_value = LLMResponse(
            content="Feedback: improve structure",
            model="test-model",
            usage={"input_tokens": 50, "output_tokens": 100},
        )
        request = WriteRequest(
            mode="pair",
            content="My draft",
            title="Draft Post",
            provider="claude",
        )
        result = await pipeline.get_feedback(request)

        assert "Feedback" in result.content
        assert result.metadata.llm_assisted is True
        assert result.llm_usage is not None

    @pytest.mark.asyncio
    async def test_feedback_prompt_includes_content(
        self,
        pipeline: ContentPipeline,
        client: MagicMock,
    ) -> None:
        request = WriteRequest(
            mode="pair",
            content="Draft text here",
            title="T",
        )
        await pipeline.get_feedback(request)

        call_args = client.generate.call_args[0][0]
        assert "Draft text here" in call_args.user_prompt


class TestMapReduceIntegration:
    @pytest.mark.asyncio
    async def test_uses_map_reduce_for_long_content(
        self,
        factory: MagicMock,
        aggregator: AsyncMock,
    ) -> None:
        client = _mock_llm_client(max_context_tokens=100)
        # count_tokens returns len/4, threshold=0.7 → limit=70 tokens → 280 chars
        factory.create.return_value = client

        chunking = ChunkingEngine(
            client,
            ChunkingConfig(
                chunk_size_tokens=50,
                context_threshold=0.7,
            ),
        )
        pipeline = ContentPipeline(
            llm_factory=factory,
            source_aggregator=aggregator,
            chunking_engine=chunking,
        )

        # 긴 프롬프트 → map_reduce 경로
        # 300 chars → 75 tokens > 70 threshold → needs_chunking
        long_prompt = "x " * 150

        # map(2) + reduce(1) = 3 calls
        client.generate.side_effect = [
            LLMResponse(content="Map 1", model="m"),
            LLMResponse(content="Map 2", model="m"),
            LLMResponse(content="Final result", model="r"),
        ]

        request = WriteRequest(mode="auto", title="T", prompt=long_prompt)
        result = await pipeline.execute(request)

        assert result.content == "Final result"
        assert client.generate.call_count >= 2  # at least map + reduce

    @pytest.mark.asyncio
    async def test_skips_map_reduce_for_short_content(
        self,
        factory: MagicMock,
        aggregator: AsyncMock,
    ) -> None:
        client = _mock_llm_client(max_context_tokens=200000)
        factory.create.return_value = client

        chunking = ChunkingEngine(client)
        pipeline = ContentPipeline(
            llm_factory=factory,
            source_aggregator=aggregator,
            chunking_engine=chunking,
        )

        request = WriteRequest(mode="auto", title="T", prompt="Short prompt")
        await pipeline.execute(request)

        # 직접 호출 1회
        assert client.generate.call_count == 1


class TestReturnTypes:
    @pytest.mark.asyncio
    async def test_execute_returns_write_result(
        self,
        pipeline: ContentPipeline,
    ) -> None:
        request = WriteRequest(mode="auto", title="T", prompt="P")
        result = await pipeline.execute(request)

        assert isinstance(result, WriteResult)

    @pytest.mark.asyncio
    async def test_get_feedback_returns_write_result(
        self,
        pipeline: ContentPipeline,
    ) -> None:
        request = WriteRequest(mode="pair", content="Draft", title="T")
        result = await pipeline.get_feedback(request)

        assert isinstance(result, WriteResult)


class TestMetadata:
    @pytest.mark.asyncio
    async def test_category_and_tags(self, pipeline: ContentPipeline) -> None:
        request = WriteRequest(
            mode="direct",
            content="Text",
            title="T",
            category_path="math/probability",
            tags=["random-matrix", "eigenvalue"],
        )
        result = await pipeline.execute(request)

        assert result.metadata.categories == ["math/probability"]
        assert result.metadata.tags == ["random-matrix", "eigenvalue"]

    @pytest.mark.asyncio
    async def test_empty_category(self, pipeline: ContentPipeline) -> None:
        request = WriteRequest(mode="direct", content="Text", title="T")
        result = await pipeline.execute(request)

        assert result.metadata.categories == []


class TestTemplateIntegration:
    """템플릿 + 레퍼런스 연동 통합 테스트."""

    @pytest.fixture
    def tpl_mgr(self, tmp_path: Path) -> TemplateManager:
        """tmp_path 기반 TemplateManager를 생성한다."""
        tpl_dir = tmp_path / "templates"
        mgr = TemplateManager(tpl_dir)
        mgr.create(
            PromptTemplate(
                id="test-tpl",
                name="테스트 템플릿",
                description="테스트용",
                system_prompt="당신은 논문 리뷰 전문가입니다.",
                user_prompt_template=(
                    "다음 내용을 리뷰하세요:\n\n{content}\n\n"
                    "스타일 참고:\n{style_reference}"
                ),
                created_at="",
                updated_at="",
            )
        )
        return mgr

    @pytest.fixture
    def ref_mgr(self, tmp_path: Path) -> ReferenceManager:
        """tmp_path 기반 ReferenceManager를 생성한다."""
        ref_dir = tmp_path / "references"
        ref_dir.mkdir(parents=True, exist_ok=True)
        # 파일 레퍼런스 추가
        sample = tmp_path / "sample_style.md"
        sample.write_text("문체 예시: 간결하고 학술적인 톤")
        mgr = ReferenceManager(ref_dir)
        mgr.add_file("sample-style", sample)
        return mgr

    @pytest.fixture
    def pipeline_with_tpl(
        self,
        factory: MagicMock,
        aggregator: AsyncMock,
        tpl_mgr: TemplateManager,
        ref_mgr: ReferenceManager,
    ) -> ContentPipeline:
        return ContentPipeline(
            llm_factory=factory,
            source_aggregator=aggregator,
            template_manager=tpl_mgr,
            reference_manager=ref_mgr,
        )

    @pytest.mark.asyncio
    async def test_auto_with_template(
        self,
        pipeline_with_tpl: ContentPipeline,
        client: MagicMock,
    ) -> None:
        """template_id 지정 → 템플릿 system_prompt가 LLM에 전달된다."""
        request = WriteRequest(
            mode="auto",
            title="T",
            prompt="P",
            template_id="test-tpl",
        )
        await pipeline_with_tpl.execute(request)

        call_args = client.generate.call_args[0][0]
        assert "논문 리뷰 전문가" in call_args.system_prompt

    @pytest.mark.asyncio
    async def test_auto_with_template_and_reference(
        self,
        pipeline_with_tpl: ContentPipeline,
        client: MagicMock,
    ) -> None:
        """template_id + reference_id → style_reference가 rendered prompt에 포함된다."""
        request = WriteRequest(
            mode="auto",
            title="T",
            prompt="P",
            template_id="test-tpl",
            reference_id="sample-style",
        )
        await pipeline_with_tpl.execute(request)

        call_args = client.generate.call_args[0][0]
        assert "논문 리뷰 전문가" in call_args.system_prompt
        assert "간결하고 학술적인 톤" in call_args.user_prompt

    @pytest.mark.asyncio
    async def test_auto_without_template_unchanged(
        self,
        pipeline_with_tpl: ContentPipeline,
        client: MagicMock,
    ) -> None:
        """template_id 미지정 → 기존 _SYSTEM_PROMPT_AUTO가 사용된다."""
        request = WriteRequest(
            mode="auto",
            title="T",
            prompt="P",
        )
        await pipeline_with_tpl.execute(request)

        call_args = client.generate.call_args[0][0]
        assert "기술 블로그 글을 작성하는 전문 작가" in call_args.system_prompt

    @pytest.mark.asyncio
    async def test_pair_with_template(
        self,
        pipeline_with_tpl: ContentPipeline,
        client: MagicMock,
    ) -> None:
        """페어 모드에서 template_id → system_prompt에 템플릿 스타일 컨텍스트가 포함된다."""
        request = WriteRequest(
            mode="pair",
            content="초안 내용",
            title="T",
            template_id="test-tpl",
        )
        await pipeline_with_tpl.get_feedback(request)

        call_args = client.generate.call_args[0][0]
        assert "편집자" in call_args.system_prompt
        assert "논문 리뷰 전문가" in call_args.system_prompt
