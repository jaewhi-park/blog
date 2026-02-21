"""arXiv 논문 조회 및 PDF 다운로드 클라이언트."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from pathlib import Path

import arxiv

from core.exceptions import SourceError


@dataclass
class ArxivPaper:
    """arXiv 논문 메타데이터."""

    arxiv_id: str
    title: str
    authors: list[str]
    abstract: str
    categories: list[str]
    published: str
    pdf_url: str
    url: str


class ArxivClient:
    """arXiv API를 통해 논문을 조회하고 PDF를 다운로드한다."""

    def __init__(self, *, page_size: int = 50, num_retries: int = 3) -> None:
        """
        Args:
            page_size: API 페이지 크기.
            num_retries: API 재시도 횟수.
        """
        self._client = arxiv.Client(
            page_size=page_size,
            num_retries=num_retries,
        )

    async def fetch_recent(
        self,
        categories: list[str],
        max_results: int = 50,
    ) -> list[ArxivPaper]:
        """
        카테고리별 최신 논문을 조회한다.

        Args:
            categories: arXiv 카테고리 목록 (예: ["cs.AI", "cs.LG"]).
            max_results: 최대 결과 수.

        Returns:
            ArxivPaper 목록 (최신순).

        Raises:
            SourceError: API 호출 실패.
        """
        if not categories:
            raise SourceError("카테고리를 하나 이상 지정해야 합니다")

        query = " OR ".join(f"cat:{cat}" for cat in categories)
        search = arxiv.Search(
            query=query,
            max_results=max_results,
            sort_by=arxiv.SortCriterion.SubmittedDate,
            sort_order=arxiv.SortOrder.Descending,
        )

        try:
            results = await asyncio.to_thread(
                lambda: list(self._client.results(search))
            )
        except Exception as e:
            raise SourceError(f"arXiv API 호출 실패: {e}") from e

        return [self._to_paper(r) for r in results]

    async def fetch_by_id(self, arxiv_id: str) -> ArxivPaper:
        """
        특정 논문을 ID로 조회한다.

        Args:
            arxiv_id: arXiv 논문 ID (예: "2301.07041").

        Returns:
            논문 메타데이터.

        Raises:
            SourceError: 논문을 찾을 수 없거나 API 실패.
        """
        search = arxiv.Search(id_list=[arxiv_id])

        try:
            results = await asyncio.to_thread(
                lambda: list(self._client.results(search))
            )
        except Exception as e:
            raise SourceError(f"arXiv API 호출 실패: {e}") from e

        if not results:
            raise SourceError(f"논문을 찾을 수 없습니다: {arxiv_id}")

        return self._to_paper(results[0])

    async def download_pdf(self, arxiv_id: str, save_path: Path) -> Path:
        """
        논문 PDF를 다운로드한다.

        Args:
            arxiv_id: arXiv 논문 ID.
            save_path: 저장할 디렉토리 경로.

        Returns:
            다운로드된 PDF 파일 경로.

        Raises:
            SourceError: 다운로드 실패.
        """
        save_path = Path(save_path)
        save_path.mkdir(parents=True, exist_ok=True)

        search = arxiv.Search(id_list=[arxiv_id])

        try:
            results = await asyncio.to_thread(
                lambda: list(self._client.results(search))
            )
        except Exception as e:
            raise SourceError(f"arXiv API 호출 실패: {e}") from e

        if not results:
            raise SourceError(f"논문을 찾을 수 없습니다: {arxiv_id}")

        try:
            result = results[0]
            written_path = await asyncio.to_thread(
                result.download_pdf, dirpath=str(save_path)
            )
            return Path(written_path)
        except Exception as e:
            raise SourceError(f"PDF 다운로드 실패 ({arxiv_id}): {e}") from e

    def _to_paper(self, result: arxiv.Result) -> ArxivPaper:
        """arxiv.Result를 ArxivPaper로 변환한다."""
        return ArxivPaper(
            arxiv_id=result.get_short_id(),
            title=result.title,
            authors=[a.name for a in result.authors],
            abstract=result.summary,
            categories=result.categories,
            published=result.published.isoformat(),
            pdf_url=result.pdf_url or "",
            url=result.entry_id,
        )
