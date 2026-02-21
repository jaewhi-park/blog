"""PDF 파싱 모듈 — PyMuPDF 기반 텍스트/이미지 추출."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import fitz

from core.content.image_manager import ImageInfo
from core.exceptions import SourceError


@dataclass
class PDFContent:
    """PDF에서 추출한 컨텐츠."""

    text: str
    images: list[ImageInfo] = field(default_factory=list)
    image_data: dict[str, bytes] = field(default_factory=dict)
    total_pages: int = 0
    extracted_range: tuple[int, int] | None = None


class PDFParser:
    """PyMuPDF로 PDF 텍스트와 이미지를 추출한다."""

    def parse(
        self,
        pdf_path: Path,
        page_range: tuple[int, int] | None = None,
        *,
        extract_images: bool = True,
    ) -> PDFContent:
        """
        PDF 파일을 파싱하여 텍스트와 이미지를 추출한다.

        Args:
            pdf_path: PDF 파일 경로.
            page_range: 추출할 페이지 범위 (1-indexed, inclusive). None이면 전체.
            extract_images: True이면 이미지도 추출.

        Returns:
            추출된 텍스트, 이미지 메타데이터, 이미지 바이트 데이터.

        Raises:
            SourceError: 파일을 찾을 수 없거나, PDF를 열 수 없거나,
                         page_range가 잘못된 경우.
        """
        pdf_path = Path(pdf_path)
        if not pdf_path.exists():
            raise SourceError(f"PDF 파일을 찾을 수 없습니다: {pdf_path}")

        try:
            doc = fitz.open(pdf_path)
        except Exception as e:
            raise SourceError(f"PDF 파일을 열 수 없습니다: {pdf_path}") from e

        try:
            total_pages = len(doc)
            start, end = self._resolve_range(page_range, total_pages)

            pages_text: list[str] = []
            images: list[ImageInfo] = []
            image_data: dict[str, bytes] = {}

            for page_num in range(start, end + 1):
                page = doc[page_num]
                pages_text.append(page.get_text())

                if extract_images:
                    self._extract_page_images(
                        doc,
                        page,
                        page_num,
                        images,
                        image_data,
                    )

            extracted_range = (start + 1, end + 1) if page_range is not None else None

            return PDFContent(
                text="\n\n".join(pages_text),
                images=images,
                image_data=image_data,
                total_pages=total_pages,
                extracted_range=extracted_range,
            )
        finally:
            doc.close()

    def _resolve_range(
        self,
        page_range: tuple[int, int] | None,
        total_pages: int,
    ) -> tuple[int, int]:
        """1-indexed inclusive page_range를 0-indexed inclusive로 변환한다."""
        if page_range is None:
            return 0, total_pages - 1

        start, end = page_range
        if start < 1:
            raise SourceError(f"페이지 번호는 1 이상이어야 합니다 (입력: {start})")
        if start > end:
            raise SourceError(f"시작 페이지({start})가 끝 페이지({end})보다 큽니다")
        if end > total_pages:
            raise SourceError(f"페이지 범위 초과: {end} > 총 {total_pages}페이지")

        return start - 1, end - 1

    def _extract_page_images(
        self,
        doc: fitz.Document,
        page: fitz.Page,
        page_num: int,
        images: list[ImageInfo],
        image_data: dict[str, bytes],
    ) -> None:
        """페이지에서 이미지를 추출하여 리스트에 추가한다."""
        for img_index, img in enumerate(page.get_images(full=True)):
            xref = img[0]
            try:
                pix = fitz.Pixmap(doc, xref)
                # CMYK 등 비-RGB → RGB로 변환
                if pix.n - pix.alpha > 3:
                    pix = fitz.Pixmap(fitz.csRGB, pix)

                filename = f"page{page_num + 1}_img{img_index + 1}.png"
                png_bytes = pix.tobytes("png")

                images.append(
                    ImageInfo(
                        filename=filename,
                        source="pdf_extract",
                        page=page_num + 1,
                    )
                )
                image_data[filename] = png_bytes
            except Exception:
                # 추출 실패한 이미지는 건너뜀
                continue
