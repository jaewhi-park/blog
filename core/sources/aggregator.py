"""소스 어그리게이터 — 복수 소스를 파싱/크롤링하여 병합."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from pathlib import Path

from core.content.image_manager import ImageInfo
from core.exceptions import SourceError
from core.sources.arxiv_client import ArxivClient
from core.sources.pdf_parser import PDFParser
from core.sources.url_crawler import URLCrawler

# 토큰 추정: 영문 기준 ~4글자/토큰, 한글 기준 ~2글자/토큰
# 보수적으로 3글자/토큰 사용
_CHARS_PER_TOKEN = 3


@dataclass
class SourceInput:
    """소스 입력 정보."""

    source_type: str  # "pdf", "url", "arxiv"
    path_or_url: str
    page_range: tuple[int, int] | None = None  # PDF 전용
    label: str | None = None


@dataclass
class AggregatedContent:
    """병합된 소스 컨텐츠."""

    combined_text: str
    sources: list[SourceInput]
    images: list[ImageInfo] = field(default_factory=list)
    image_data: dict[str, bytes] = field(default_factory=dict)
    total_tokens_estimate: int = 0


class SourceAggregator:
    """복수 소스를 파싱/크롤링하여 하나의 AggregatedContent로 병합한다."""

    def __init__(
        self,
        pdf_parser: PDFParser,
        url_crawler: URLCrawler,
        arxiv_client: ArxivClient,
    ) -> None:
        """
        Args:
            pdf_parser: PDF 파서.
            url_crawler: URL 크롤러.
            arxiv_client: arXiv 클라이언트.
        """
        self._pdf_parser = pdf_parser
        self._url_crawler = url_crawler
        self._arxiv_client = arxiv_client

    async def aggregate(self, sources: list[SourceInput]) -> AggregatedContent:
        """
        복수 소스를 파싱/크롤링하여 하나의 AggregatedContent로 병합한다.

        각 소스 텍스트는 구분자로 분리하여 LLM이 출처를 구분할 수 있게 한다.

        Args:
            sources: 소스 입력 목록.

        Returns:
            병합된 컨텐츠.

        Raises:
            SourceError: 소스 목록이 비어있거나, 개별 소스 처리 실패.
        """
        if not sources:
            raise SourceError("소스를 하나 이상 지정해야 합니다")

        tasks = [self._process_source(src) for src in sources]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        text_parts: list[str] = []
        all_images: list[ImageInfo] = []
        all_image_data: dict[str, bytes] = {}
        errors: list[str] = []

        for i, result in enumerate(results):
            if isinstance(result, Exception):
                errors.append(f"소스 {i + 1} ({sources[i].path_or_url}): {result}")
                continue

            text, images, image_data = result
            label = self._make_label(sources[i], i + 1)
            text_parts.append(f"=== {label} ===\n{text}")
            all_images.extend(images)
            all_image_data.update(image_data)

        if errors and not text_parts:
            raise SourceError("모든 소스 처리에 실패했습니다:\n" + "\n".join(errors))

        combined_text = "\n\n".join(text_parts)

        return AggregatedContent(
            combined_text=combined_text,
            sources=sources,
            images=all_images,
            image_data=all_image_data,
            total_tokens_estimate=len(combined_text) // _CHARS_PER_TOKEN,
        )

    async def _process_source(
        self,
        source: SourceInput,
    ) -> tuple[str, list[ImageInfo], dict[str, bytes]]:
        """개별 소스를 처리하여 (텍스트, 이미지목록, 이미지데이터)를 반환한다."""
        if source.source_type == "pdf":
            return await self._process_pdf(source)
        if source.source_type == "url":
            return await self._process_url(source)
        if source.source_type == "arxiv":
            return await self._process_arxiv(source)

        raise SourceError(f"지원하지 않는 소스 타입: {source.source_type}")

    async def _process_pdf(
        self,
        source: SourceInput,
    ) -> tuple[str, list[ImageInfo], dict[str, bytes]]:
        """PDF 소스를 처리한다."""
        content = await asyncio.to_thread(
            self._pdf_parser.parse,
            Path(source.path_or_url),
            source.page_range,
        )
        return content.text, content.images, content.image_data

    async def _process_url(
        self,
        source: SourceInput,
    ) -> tuple[str, list[ImageInfo], dict[str, bytes]]:
        """URL 소스를 처리한다."""
        content = await self._url_crawler.crawl(source.path_or_url)
        return content.text, [], {}

    async def _process_arxiv(
        self,
        source: SourceInput,
    ) -> tuple[str, list[ImageInfo], dict[str, bytes]]:
        """arXiv 소스를 처리한다. 논문 메타데이터 + abstract를 텍스트로 반환."""
        paper = await self._arxiv_client.fetch_by_id(source.path_or_url)
        text_parts = [
            f"Title: {paper.title}",
            f"Authors: {', '.join(paper.authors)}",
            f"Published: {paper.published}",
            f"Categories: {', '.join(paper.categories)}",
            "",
            paper.abstract,
        ]
        return "\n".join(text_parts), [], {}

    def _make_label(self, source: SourceInput, index: int) -> str:
        """소스 구분자 라벨을 생성한다."""
        if source.label:
            return f"Source {index}: {source.label}"

        label = f"Source {index}: {source.path_or_url}"
        if source.page_range:
            start, end = source.page_range
            label += f" (pages {start}-{end})"

        return label
