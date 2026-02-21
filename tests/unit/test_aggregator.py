"""SourceAggregator 단위 테스트."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from core.content.image_manager import ImageInfo
from core.exceptions import SourceError
from core.sources.aggregator import AggregatedContent, SourceAggregator, SourceInput
from core.sources.arxiv_client import ArxivPaper
from core.sources.pdf_parser import PDFContent
from core.sources.url_crawler import CrawledContent


@pytest.fixture
def pdf_parser() -> MagicMock:
    return MagicMock()


@pytest.fixture
def url_crawler() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def arxiv_client() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def aggregator(
    pdf_parser: MagicMock,
    url_crawler: AsyncMock,
    arxiv_client: AsyncMock,
) -> SourceAggregator:
    return SourceAggregator(pdf_parser, url_crawler, arxiv_client)


class TestAggregateSingle:
    @pytest.mark.asyncio
    async def test_pdf_source(
        self,
        aggregator: SourceAggregator,
        pdf_parser: MagicMock,
    ) -> None:
        pdf_parser.parse.return_value = PDFContent(
            text="PDF content here",
            images=[ImageInfo(filename="img1.png", source="pdf_extract", page=1)],
            image_data={"img1.png": b"png-bytes"},
            total_pages=5,
        )
        sources = [SourceInput(source_type="pdf", path_or_url="/tmp/test.pdf")]
        result = await aggregator.aggregate(sources)

        assert "PDF content here" in result.combined_text
        assert len(result.images) == 1
        assert result.images[0].filename == "img1.png"
        assert result.image_data["img1.png"] == b"png-bytes"
        assert result.total_tokens_estimate > 0

    @pytest.mark.asyncio
    async def test_url_source(
        self,
        aggregator: SourceAggregator,
        url_crawler: AsyncMock,
    ) -> None:
        url_crawler.crawl.return_value = CrawledContent(
            url="https://example.com",
            title="Example",
            text="Web page content",
            fetched_at="2024-01-01T00:00:00",
        )
        sources = [SourceInput(source_type="url", path_or_url="https://example.com")]
        result = await aggregator.aggregate(sources)

        assert "Web page content" in result.combined_text
        assert result.images == []

    @pytest.mark.asyncio
    async def test_arxiv_source(
        self,
        aggregator: SourceAggregator,
        arxiv_client: AsyncMock,
    ) -> None:
        arxiv_client.fetch_by_id.return_value = ArxivPaper(
            arxiv_id="2301.07041",
            title="Test Paper",
            authors=["Alice", "Bob"],
            abstract="This is an abstract.",
            categories=["cs.AI"],
            published="2023-01-17T00:00:00+00:00",
            pdf_url="http://arxiv.org/pdf/2301.07041",
            url="http://arxiv.org/abs/2301.07041",
        )
        sources = [SourceInput(source_type="arxiv", path_or_url="2301.07041")]
        result = await aggregator.aggregate(sources)

        assert "Test Paper" in result.combined_text
        assert "Alice, Bob" in result.combined_text
        assert "This is an abstract." in result.combined_text


class TestAggregateMultiple:
    @pytest.mark.asyncio
    async def test_multiple_sources_combined(
        self,
        aggregator: SourceAggregator,
        pdf_parser: MagicMock,
        url_crawler: AsyncMock,
    ) -> None:
        pdf_parser.parse.return_value = PDFContent(
            text="PDF text",
            total_pages=1,
        )
        url_crawler.crawl.return_value = CrawledContent(
            url="https://example.com",
            title="Page",
            text="URL text",
            fetched_at="2024-01-01",
        )
        sources = [
            SourceInput(source_type="pdf", path_or_url="/tmp/a.pdf"),
            SourceInput(source_type="url", path_or_url="https://example.com"),
        ]
        result = await aggregator.aggregate(sources)

        assert "PDF text" in result.combined_text
        assert "URL text" in result.combined_text
        assert "Source 1" in result.combined_text
        assert "Source 2" in result.combined_text

    @pytest.mark.asyncio
    async def test_sources_separated_by_delimiter(
        self,
        aggregator: SourceAggregator,
        pdf_parser: MagicMock,
        url_crawler: AsyncMock,
    ) -> None:
        pdf_parser.parse.return_value = PDFContent(text="A", total_pages=1)
        url_crawler.crawl.return_value = CrawledContent(
            url="https://x.com",
            title="X",
            text="B",
            fetched_at="",
        )
        sources = [
            SourceInput(source_type="pdf", path_or_url="/tmp/a.pdf"),
            SourceInput(source_type="url", path_or_url="https://x.com"),
        ]
        result = await aggregator.aggregate(sources)

        assert "===" in result.combined_text


class TestLabels:
    @pytest.mark.asyncio
    async def test_custom_label(
        self,
        aggregator: SourceAggregator,
        pdf_parser: MagicMock,
    ) -> None:
        pdf_parser.parse.return_value = PDFContent(text="Text", total_pages=1)
        sources = [
            SourceInput(
                source_type="pdf",
                path_or_url="/tmp/a.pdf",
                label="Paper A",
            ),
        ]
        result = await aggregator.aggregate(sources)

        assert "Paper A" in result.combined_text

    @pytest.mark.asyncio
    async def test_page_range_in_label(
        self,
        aggregator: SourceAggregator,
        pdf_parser: MagicMock,
    ) -> None:
        pdf_parser.parse.return_value = PDFContent(text="Text", total_pages=10)
        sources = [
            SourceInput(
                source_type="pdf",
                path_or_url="/tmp/a.pdf",
                page_range=(3, 8),
            ),
        ]
        result = await aggregator.aggregate(sources)

        assert "pages 3-8" in result.combined_text


class TestTokenEstimate:
    @pytest.mark.asyncio
    async def test_estimates_tokens(
        self,
        aggregator: SourceAggregator,
        url_crawler: AsyncMock,
    ) -> None:
        url_crawler.crawl.return_value = CrawledContent(
            url="https://x.com",
            title="X",
            text="a" * 300,
            fetched_at="",
        )
        sources = [SourceInput(source_type="url", path_or_url="https://x.com")]
        result = await aggregator.aggregate(sources)

        # 300 chars of content + delimiter/label overhead
        assert result.total_tokens_estimate > 0


class TestErrorHandling:
    @pytest.mark.asyncio
    async def test_empty_sources_raises(
        self,
        aggregator: SourceAggregator,
    ) -> None:
        with pytest.raises(SourceError, match="소스를 하나 이상"):
            await aggregator.aggregate([])

    @pytest.mark.asyncio
    async def test_unknown_source_type_raises(
        self,
        aggregator: SourceAggregator,
    ) -> None:
        sources = [SourceInput(source_type="unknown", path_or_url="x")]
        with pytest.raises(SourceError, match="모든 소스 처리에 실패"):
            await aggregator.aggregate(sources)

    @pytest.mark.asyncio
    async def test_partial_failure_continues(
        self,
        aggregator: SourceAggregator,
        pdf_parser: MagicMock,
        url_crawler: AsyncMock,
    ) -> None:
        pdf_parser.parse.side_effect = SourceError("PDF 오류")
        url_crawler.crawl.return_value = CrawledContent(
            url="https://x.com",
            title="X",
            text="Good content",
            fetched_at="",
        )
        sources = [
            SourceInput(source_type="pdf", path_or_url="/tmp/bad.pdf"),
            SourceInput(source_type="url", path_or_url="https://x.com"),
        ]
        result = await aggregator.aggregate(sources)

        # 실패한 PDF는 건너뛰고 URL 결과만 포함
        assert "Good content" in result.combined_text
        assert "PDF 오류" not in result.combined_text

    @pytest.mark.asyncio
    async def test_all_failures_raises(
        self,
        aggregator: SourceAggregator,
        pdf_parser: MagicMock,
        url_crawler: AsyncMock,
    ) -> None:
        pdf_parser.parse.side_effect = SourceError("PDF fail")
        url_crawler.crawl.side_effect = SourceError("URL fail")

        sources = [
            SourceInput(source_type="pdf", path_or_url="/tmp/bad.pdf"),
            SourceInput(source_type="url", path_or_url="https://bad.com"),
        ]
        with pytest.raises(SourceError, match="모든 소스 처리에 실패"):
            await aggregator.aggregate(sources)


class TestReturnType:
    @pytest.mark.asyncio
    async def test_returns_aggregated_content(
        self,
        aggregator: SourceAggregator,
        url_crawler: AsyncMock,
    ) -> None:
        url_crawler.crawl.return_value = CrawledContent(
            url="https://x.com",
            title="X",
            text="Content",
            fetched_at="",
        )
        sources = [SourceInput(source_type="url", path_or_url="https://x.com")]
        result = await aggregator.aggregate(sources)

        assert isinstance(result, AggregatedContent)
        assert result.sources == sources
