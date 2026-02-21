"""ArxivClient 단위 테스트."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

import arxiv
import pytest

from core.exceptions import SourceError
from core.sources.arxiv_client import ArxivClient, ArxivPaper


def _make_result(
    entry_id: str = "http://arxiv.org/abs/2301.07041v1",
    title: str = "Test Paper",
    authors: list[str] | None = None,
    summary: str = "Abstract text",
    categories: list[str] | None = None,
    published: datetime | None = None,
    pdf_url: str = "http://arxiv.org/pdf/2301.07041v1",
) -> arxiv.Result:
    """테스트용 arxiv.Result 객체를 생성한다."""
    if authors is None:
        authors = ["Alice", "Bob"]
    if categories is None:
        categories = ["cs.AI"]
    if published is None:
        published = datetime(2023, 1, 17, tzinfo=timezone.utc)

    result = arxiv.Result(
        entry_id=entry_id,
        title=title,
        authors=[arxiv.Result.Author(name) for name in authors],
        summary=summary,
        categories=categories,
        published=published,
    )
    result.pdf_url = pdf_url
    return result


@pytest.fixture
def client() -> ArxivClient:
    return ArxivClient()


class TestFetchRecent:
    @pytest.mark.asyncio
    async def test_returns_papers(self, client: ArxivClient) -> None:
        results = [
            _make_result(title="Paper A"),
            _make_result(
                entry_id="http://arxiv.org/abs/2301.08000v1",
                title="Paper B",
            ),
        ]
        with patch.object(client._client, "results", return_value=iter(results)):
            papers = await client.fetch_recent(["cs.AI"], max_results=10)

        assert len(papers) == 2
        assert papers[0].title == "Paper A"
        assert papers[1].title == "Paper B"

    @pytest.mark.asyncio
    async def test_returns_arxiv_paper_dataclass(self, client: ArxivClient) -> None:
        results = [_make_result()]
        with patch.object(client._client, "results", return_value=iter(results)):
            papers = await client.fetch_recent(["cs.AI"])

        paper = papers[0]
        assert isinstance(paper, ArxivPaper)
        assert paper.arxiv_id == "2301.07041v1"
        assert paper.authors == ["Alice", "Bob"]
        assert paper.abstract == "Abstract text"
        assert paper.categories == ["cs.AI"]
        assert paper.pdf_url == "http://arxiv.org/pdf/2301.07041v1"
        assert "2023" in paper.published

    @pytest.mark.asyncio
    async def test_multiple_categories(self, client: ArxivClient) -> None:
        with patch.object(client._client, "results", return_value=iter([])) as mock:
            await client.fetch_recent(["cs.AI", "cs.LG"])

        # Search 객체의 query에 두 카테고리가 모두 포함되어야 함
        call_args = mock.call_args
        search = call_args[0][0]
        assert "cs.AI" in search.query
        assert "cs.LG" in search.query

    @pytest.mark.asyncio
    async def test_empty_categories_raises(self, client: ArxivClient) -> None:
        with pytest.raises(SourceError, match="카테고리를 하나 이상"):
            await client.fetch_recent([])

    @pytest.mark.asyncio
    async def test_api_failure_raises(self, client: ArxivClient) -> None:
        with patch.object(
            client._client, "results", side_effect=Exception("network error")
        ):
            with pytest.raises(SourceError, match="arXiv API 호출 실패"):
                await client.fetch_recent(["cs.AI"])


class TestFetchById:
    @pytest.mark.asyncio
    async def test_returns_paper(self, client: ArxivClient) -> None:
        result = _make_result(title="Specific Paper")
        with patch.object(client._client, "results", return_value=iter([result])):
            paper = await client.fetch_by_id("2301.07041")

        assert paper.title == "Specific Paper"

    @pytest.mark.asyncio
    async def test_not_found_raises(self, client: ArxivClient) -> None:
        with patch.object(client._client, "results", return_value=iter([])):
            with pytest.raises(SourceError, match="논문을 찾을 수 없습니다"):
                await client.fetch_by_id("0000.00000")

    @pytest.mark.asyncio
    async def test_api_failure_raises(self, client: ArxivClient) -> None:
        with patch.object(client._client, "results", side_effect=Exception("timeout")):
            with pytest.raises(SourceError, match="arXiv API 호출 실패"):
                await client.fetch_by_id("2301.07041")


class TestDownloadPdf:
    @pytest.mark.asyncio
    async def test_downloads_to_path(self, client: ArxivClient, tmp_path: Path) -> None:
        result = _make_result()
        # download_pdf가 파일 경로를 반환하도록 설정
        expected_file = tmp_path / "2301.07041v1.Test_Paper.pdf"
        expected_file.write_bytes(b"%PDF-fake")
        result.download_pdf = MagicMock(return_value=str(expected_file))

        with patch.object(client._client, "results", return_value=iter([result])):
            path = await client.download_pdf("2301.07041", tmp_path)

        assert path == expected_file
        assert path.exists()

    @pytest.mark.asyncio
    async def test_creates_directory(self, client: ArxivClient, tmp_path: Path) -> None:
        new_dir = tmp_path / "subdir" / "papers"
        result = _make_result()
        expected_file = new_dir / "paper.pdf"

        def mock_download(dirpath: str) -> str:
            Path(dirpath).mkdir(parents=True, exist_ok=True)
            expected_file.write_bytes(b"%PDF")
            return str(expected_file)

        result.download_pdf = MagicMock(side_effect=mock_download)

        with patch.object(client._client, "results", return_value=iter([result])):
            path = await client.download_pdf("2301.07041", new_dir)

        assert path.exists()

    @pytest.mark.asyncio
    async def test_download_failure_raises(
        self, client: ArxivClient, tmp_path: Path
    ) -> None:
        result = _make_result()
        result.download_pdf = MagicMock(side_effect=Exception("download failed"))

        with patch.object(client._client, "results", return_value=iter([result])):
            with pytest.raises(SourceError, match="PDF 다운로드 실패"):
                await client.download_pdf("2301.07041", tmp_path)


class TestToPaper:
    def test_converts_result_to_paper(self, client: ArxivClient) -> None:
        result = _make_result(
            entry_id="http://arxiv.org/abs/2401.12345v2",
            title="Conversion Test",
            authors=["Charlie"],
            summary="Test abstract",
            categories=["cs.CL", "cs.AI"],
            published=datetime(2024, 1, 15, 12, 0, tzinfo=timezone.utc),
            pdf_url="http://arxiv.org/pdf/2401.12345v2",
        )
        paper = client._to_paper(result)

        assert paper.arxiv_id == "2401.12345v2"
        assert paper.title == "Conversion Test"
        assert paper.authors == ["Charlie"]
        assert paper.abstract == "Test abstract"
        assert paper.categories == ["cs.CL", "cs.AI"]
        assert paper.pdf_url == "http://arxiv.org/pdf/2401.12345v2"
        assert paper.url == "http://arxiv.org/abs/2401.12345v2"
        assert "2024-01-15" in paper.published
