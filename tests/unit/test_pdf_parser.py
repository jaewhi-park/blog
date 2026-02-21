"""PDFParser 단위 테스트."""

from pathlib import Path

import fitz
import pytest

from core.exceptions import SourceError
from core.sources.pdf_parser import PDFParser


@pytest.fixture
def parser() -> PDFParser:
    return PDFParser()


def _create_text_pdf(path: Path, pages: list[str]) -> Path:
    """테스트용 텍스트 PDF를 프로그래밍 방식으로 생성한다."""
    doc = fitz.open()
    for text in pages:
        page = doc.new_page()
        page.insert_text((72, 72), text, fontsize=12)
    doc.save(str(path))
    doc.close()
    return path


def _create_image_pdf(path: Path) -> Path:
    """테스트용 이미지 포함 PDF를 생성한다."""
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 72), "Page with image", fontsize=12)

    # 작은 빨간 사각형 이미지 삽입
    pix = fitz.Pixmap(fitz.csRGB, fitz.IRect(0, 0, 20, 20), 0)
    pix.set_rect(pix.irect, (255, 0, 0))
    img_bytes = pix.tobytes("png")
    page.insert_image(fitz.Rect(100, 100, 200, 200), stream=img_bytes)

    doc.save(str(path))
    doc.close()
    return path


class TestParseFullDocument:
    def test_extracts_all_pages_text(
        self,
        parser: PDFParser,
        tmp_path: Path,
    ) -> None:
        pdf = _create_text_pdf(tmp_path / "doc.pdf", ["Page 1", "Page 2", "Page 3"])
        result = parser.parse(pdf, extract_images=False)

        assert "Page 1" in result.text
        assert "Page 2" in result.text
        assert "Page 3" in result.text

    def test_extracted_range_is_none_for_full(
        self,
        parser: PDFParser,
        tmp_path: Path,
    ) -> None:
        pdf = _create_text_pdf(tmp_path / "doc.pdf", ["Hello"])
        result = parser.parse(pdf, extract_images=False)

        assert result.extracted_range is None


class TestParsePageRange:
    def test_extracts_specified_range(
        self,
        parser: PDFParser,
        tmp_path: Path,
    ) -> None:
        pdf = _create_text_pdf(
            tmp_path / "doc.pdf",
            ["Page 1", "Page 2", "Page 3"],
        )
        result = parser.parse(pdf, page_range=(2, 3), extract_images=False)

        assert "Page 1" not in result.text
        assert "Page 2" in result.text
        assert "Page 3" in result.text

    def test_extracted_range_matches_input(
        self,
        parser: PDFParser,
        tmp_path: Path,
    ) -> None:
        pdf = _create_text_pdf(
            tmp_path / "doc.pdf",
            ["A", "B", "C"],
        )
        result = parser.parse(pdf, page_range=(2, 3), extract_images=False)

        assert result.extracted_range == (2, 3)

    def test_single_page_range(
        self,
        parser: PDFParser,
        tmp_path: Path,
    ) -> None:
        pdf = _create_text_pdf(
            tmp_path / "doc.pdf",
            ["Only", "This", "Not this"],
        )
        result = parser.parse(pdf, page_range=(2, 2), extract_images=False)

        assert "This" in result.text
        assert "Only" not in result.text
        assert "Not this" not in result.text
        assert result.extracted_range == (2, 2)


class TestTotalPages:
    def test_reports_total_pages(
        self,
        parser: PDFParser,
        tmp_path: Path,
    ) -> None:
        pdf = _create_text_pdf(tmp_path / "doc.pdf", ["A", "B", "C", "D"])
        result = parser.parse(pdf, extract_images=False)

        assert result.total_pages == 4

    def test_total_pages_with_range(
        self,
        parser: PDFParser,
        tmp_path: Path,
    ) -> None:
        pdf = _create_text_pdf(tmp_path / "doc.pdf", ["A", "B", "C"])
        result = parser.parse(pdf, page_range=(1, 2), extract_images=False)

        assert result.total_pages == 3


class TestExtractImages:
    def test_extracts_images(
        self,
        parser: PDFParser,
        tmp_path: Path,
    ) -> None:
        pdf = _create_image_pdf(tmp_path / "img.pdf")
        result = parser.parse(pdf)

        assert len(result.images) >= 1
        img = result.images[0]
        assert img.source == "pdf_extract"
        assert img.page == 1
        assert img.filename in result.image_data
        assert len(result.image_data[img.filename]) > 0

    def test_extract_images_false(
        self,
        parser: PDFParser,
        tmp_path: Path,
    ) -> None:
        pdf = _create_image_pdf(tmp_path / "img.pdf")
        result = parser.parse(pdf, extract_images=False)

        assert result.images == []
        assert result.image_data == {}


class TestInvalidPageRange:
    def test_reversed_range(
        self,
        parser: PDFParser,
        tmp_path: Path,
    ) -> None:
        pdf = _create_text_pdf(tmp_path / "doc.pdf", ["A", "B"])
        with pytest.raises(SourceError, match="시작 페이지.*끝 페이지"):
            parser.parse(pdf, page_range=(2, 1), extract_images=False)

    def test_out_of_bounds(
        self,
        parser: PDFParser,
        tmp_path: Path,
    ) -> None:
        pdf = _create_text_pdf(tmp_path / "doc.pdf", ["A", "B"])
        with pytest.raises(SourceError, match="페이지 범위 초과"):
            parser.parse(pdf, page_range=(1, 10), extract_images=False)

    def test_zero_page(
        self,
        parser: PDFParser,
        tmp_path: Path,
    ) -> None:
        pdf = _create_text_pdf(tmp_path / "doc.pdf", ["A"])
        with pytest.raises(SourceError, match="1 이상"):
            parser.parse(pdf, page_range=(0, 1), extract_images=False)


class TestErrorHandling:
    def test_file_not_found(self, parser: PDFParser, tmp_path: Path) -> None:
        with pytest.raises(SourceError, match="찾을 수 없습니다"):
            parser.parse(tmp_path / "nonexistent.pdf")

    def test_corrupted_pdf(
        self,
        parser: PDFParser,
        tmp_path: Path,
    ) -> None:
        bad_pdf = tmp_path / "bad.pdf"
        bad_pdf.write_bytes(b"this is not a pdf")
        with pytest.raises(SourceError, match="열 수 없습니다"):
            parser.parse(bad_pdf)
