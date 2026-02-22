"""ReferenceManager 단위 테스트."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
import yaml

from core.content.reference_manager import ReferenceManager, StyleReference
from core.exceptions import ReferenceError, ReferenceNotFoundError
from core.sources.url_crawler import CrawledContent


def _write_index(tmp_path: Path, entries: list[dict]) -> None:
    """테스트용 index.yaml 작성."""
    with open(tmp_path / "index.yaml", "w", encoding="utf-8") as f:
        yaml.safe_dump(
            {"references": entries},
            f,
            allow_unicode=True,
            sort_keys=False,
        )


def _make_entry(
    ref_id: str = "test-ref",
    name: str = "테스트 레퍼런스",
    source_type: str = "file",
    source_path: str = "test-ref.md",
    content_cache: str | None = None,
    file_type: str | None = "md",
    created_at: str = "2026-01-01T00:00:00+00:00",
    updated_at: str = "2026-01-01T00:00:00+00:00",
) -> dict:
    """테스트용 index entry dict 생성."""
    return {
        "id": ref_id,
        "name": name,
        "source_type": source_type,
        "source_path": source_path,
        "content_cache": content_cache,
        "file_type": file_type,
        "created_at": created_at,
        "updated_at": updated_at,
    }


def _make_file_ref(
    tmp_path: Path,
    filename: str = "sample.md",
    content: str = "# Sample\n\nHello world.",
) -> Path:
    """테스트용 소스 파일 생성."""
    p = tmp_path / filename
    p.write_text(content, encoding="utf-8")
    return p


class TestStyleReference:
    def test_dataclass_creation(self) -> None:
        ref = StyleReference(
            id="test",
            name="Test",
            source_type="file",
            source_path="test.md",
            content_cache=None,
            file_type="md",
            created_at="2026-01-01",
            updated_at="2026-01-01",
        )
        assert ref.id == "test"
        assert ref.source_type == "file"
        assert ref.content_cache is None


class TestListAll:
    def test_empty_directory(self, tmp_path: Path) -> None:
        mgr = ReferenceManager(tmp_path)
        assert mgr.list_all() == []

    def test_nonexistent_directory(self, tmp_path: Path) -> None:
        mgr = ReferenceManager(tmp_path / "nonexistent")
        assert mgr.list_all() == []

    def test_multiple_references(self, tmp_path: Path) -> None:
        _write_index(
            tmp_path,
            [
                _make_entry("alpha", updated_at="2026-01-01T00:00:00+00:00"),
                _make_entry("beta", updated_at="2026-02-01T00:00:00+00:00"),
            ],
        )

        mgr = ReferenceManager(tmp_path)
        refs = mgr.list_all()

        assert len(refs) == 2
        assert refs[0].id == "beta"
        assert refs[1].id == "alpha"

    def test_sorted_by_updated_at_descending(self, tmp_path: Path) -> None:
        _write_index(
            tmp_path,
            [
                _make_entry("old", updated_at="2025-01-01T00:00:00+00:00"),
                _make_entry("mid", updated_at="2025-06-01T00:00:00+00:00"),
                _make_entry("new", updated_at="2026-01-01T00:00:00+00:00"),
            ],
        )

        mgr = ReferenceManager(tmp_path)
        refs = mgr.list_all()

        assert [r.id for r in refs] == ["new", "mid", "old"]


class TestGet:
    def test_get_existing(self, tmp_path: Path) -> None:
        _write_index(tmp_path, [_make_entry("my-ref", name="마이 레퍼런스")])

        mgr = ReferenceManager(tmp_path)
        ref = mgr.get("my-ref")

        assert ref.id == "my-ref"
        assert ref.name == "마이 레퍼런스"

    def test_nonexistent_raises(self, tmp_path: Path) -> None:
        mgr = ReferenceManager(tmp_path)
        with pytest.raises(ReferenceNotFoundError, match="찾을 수 없습니다"):
            mgr.get("nonexistent")


class TestAddFile:
    def test_add_md_file(self, tmp_path: Path) -> None:
        refs_dir = tmp_path / "refs"
        source_file = _make_file_ref(tmp_path, "my_style.md")

        mgr = ReferenceManager(refs_dir)
        ref = mgr.add_file("My Style", source_file)

        assert ref.id == "my-style"
        assert ref.source_type == "file"
        assert ref.file_type == "md"
        assert (refs_dir / "my-style.md").exists()

        # index.yaml에 등록되었는지 확인
        loaded = mgr.get("my-style")
        assert loaded.name == "My Style"

    def test_add_txt_file(self, tmp_path: Path) -> None:
        refs_dir = tmp_path / "refs"
        source_file = _make_file_ref(tmp_path, "sample.txt", "plain text")

        mgr = ReferenceManager(refs_dir)
        ref = mgr.add_file("Plain Text Ref", source_file)

        assert ref.file_type == "txt"
        assert (refs_dir / "plain-text-ref.txt").exists()

    def test_file_not_found_raises(self, tmp_path: Path) -> None:
        mgr = ReferenceManager(tmp_path)
        with pytest.raises(FileNotFoundError, match="찾을 수 없습니다"):
            mgr.add_file("test", tmp_path / "nonexistent.md")

    def test_unsupported_extension_raises(self, tmp_path: Path) -> None:
        source_file = _make_file_ref(tmp_path, "data.csv", "a,b,c")

        mgr = ReferenceManager(tmp_path / "refs")
        with pytest.raises(ReferenceError, match="지원하지 않는 파일 형식"):
            mgr.add_file("CSV Data", source_file)

    def test_duplicate_id_raises(self, tmp_path: Path) -> None:
        refs_dir = tmp_path / "refs"
        source_file = _make_file_ref(tmp_path, "style.md")

        mgr = ReferenceManager(refs_dir)
        mgr.add_file("My Style", source_file)

        source_file2 = _make_file_ref(tmp_path, "style2.md", "different")
        with pytest.raises(FileExistsError, match="이미 존재합니다"):
            mgr.add_file("My Style", source_file2)

    def test_auto_sets_timestamps(self, tmp_path: Path) -> None:
        refs_dir = tmp_path / "refs"
        source_file = _make_file_ref(tmp_path, "style.md")

        mgr = ReferenceManager(refs_dir)
        ref = mgr.add_file("Test Timestamps", source_file)

        assert ref.created_at != ""
        assert ref.updated_at != ""


class TestAddUrl:
    def test_add_url_success(self, tmp_path: Path) -> None:
        mock_crawled = CrawledContent(
            url="https://example.com/blog",
            title="Example Blog",
            text="This is the crawled blog content.",
            fetched_at="2026-01-01T00:00:00+00:00",
        )

        mgr = ReferenceManager(tmp_path)
        with patch.object(
            mgr._crawler, "crawl", new_callable=AsyncMock, return_value=mock_crawled
        ):
            ref = mgr.add_url("Example Blog Style", "https://example.com/blog")

        assert ref.id == "example-blog-style"
        assert ref.source_type == "url"
        assert ref.source_path == "https://example.com/blog"
        assert ref.content_cache == "This is the crawled blog content."
        assert ref.file_type is None

        # index.yaml에 등록 확인
        loaded = mgr.get("example-blog-style")
        assert loaded.content_cache == "This is the crawled blog content."

    def test_crawl_failure_raises(self, tmp_path: Path) -> None:
        mgr = ReferenceManager(tmp_path)
        with patch.object(
            mgr._crawler,
            "crawl",
            new_callable=AsyncMock,
            side_effect=Exception("timeout"),
        ):
            with pytest.raises(ReferenceError, match="URL 크롤링 실패"):
                mgr.add_url("Bad URL", "https://example.com/404")

    def test_duplicate_id_raises(self, tmp_path: Path) -> None:
        mock_crawled = CrawledContent(
            url="https://example.com",
            title="Ex",
            text="content",
            fetched_at="2026-01-01",
        )

        mgr = ReferenceManager(tmp_path)
        with patch.object(
            mgr._crawler, "crawl", new_callable=AsyncMock, return_value=mock_crawled
        ):
            mgr.add_url("My Blog", "https://example.com/1")

        with patch.object(
            mgr._crawler, "crawl", new_callable=AsyncMock, return_value=mock_crawled
        ):
            with pytest.raises(FileExistsError, match="이미 존재합니다"):
                mgr.add_url("My Blog", "https://example.com/2")


class TestRemove:
    def test_remove_file_ref(self, tmp_path: Path) -> None:
        refs_dir = tmp_path / "refs"
        source_file = _make_file_ref(tmp_path, "style.md")

        mgr = ReferenceManager(refs_dir)
        mgr.add_file("My Style", source_file)

        assert mgr.remove("my-style") is True
        assert not (refs_dir / "my-style.md").exists()
        assert mgr.list_all() == []

    def test_remove_url_ref(self, tmp_path: Path) -> None:
        _write_index(
            tmp_path,
            [
                _make_entry(
                    "blog-style",
                    source_type="url",
                    source_path="https://example.com",
                    content_cache="cached",
                ),
            ],
        )

        mgr = ReferenceManager(tmp_path)
        assert mgr.remove("blog-style") is True
        assert mgr.list_all() == []

    def test_nonexistent_raises(self, tmp_path: Path) -> None:
        mgr = ReferenceManager(tmp_path)
        with pytest.raises(ReferenceNotFoundError, match="찾을 수 없습니다"):
            mgr.remove("nonexistent")


class TestGetContent:
    def test_file_md_content(self, tmp_path: Path) -> None:
        refs_dir = tmp_path / "refs"
        source_file = _make_file_ref(tmp_path, "style.md", "# Hello\n\nWorld.")

        mgr = ReferenceManager(refs_dir)
        mgr.add_file("My Style", source_file)

        content = mgr.get_content("my-style")
        assert "# Hello" in content
        assert "World." in content

    def test_file_txt_content(self, tmp_path: Path) -> None:
        refs_dir = tmp_path / "refs"
        source_file = _make_file_ref(tmp_path, "note.txt", "plain text content")

        mgr = ReferenceManager(refs_dir)
        mgr.add_file("My Note", source_file)

        content = mgr.get_content("my-note")
        assert content == "plain text content"

    def test_url_returns_cache(self, tmp_path: Path) -> None:
        _write_index(
            tmp_path,
            [
                _make_entry(
                    "blog-style",
                    source_type="url",
                    source_path="https://example.com",
                    content_cache="This is cached content.",
                    file_type=None,
                ),
            ],
        )

        mgr = ReferenceManager(tmp_path)
        content = mgr.get_content("blog-style")
        assert content == "This is cached content."

    def test_url_empty_cache_raises(self, tmp_path: Path) -> None:
        _write_index(
            tmp_path,
            [
                _make_entry(
                    "no-cache",
                    source_type="url",
                    source_path="https://example.com",
                    content_cache=None,
                    file_type=None,
                ),
            ],
        )

        mgr = ReferenceManager(tmp_path)
        with pytest.raises(ReferenceError, match="캐시가 비어 있습니다"):
            mgr.get_content("no-cache")

    def test_missing_file_raises(self, tmp_path: Path) -> None:
        _write_index(
            tmp_path,
            [
                _make_entry("missing", source_path="missing.md"),
            ],
        )

        mgr = ReferenceManager(tmp_path)
        with pytest.raises(ReferenceError, match="파일을 찾을 수 없습니다"):
            mgr.get_content("missing")

    def test_nonexistent_ref_raises(self, tmp_path: Path) -> None:
        mgr = ReferenceManager(tmp_path)
        with pytest.raises(ReferenceNotFoundError):
            mgr.get_content("nonexistent")

    def test_pdf_content(self, tmp_path: Path) -> None:
        """PDF 레퍼런스의 텍스트 추출을 검증한다."""
        refs_dir = tmp_path / "refs"
        refs_dir.mkdir()

        # PyMuPDF로 테스트 PDF 생성
        import fitz

        doc = fitz.open()
        page = doc.new_page()
        page.insert_text((72, 72), "PDF reference content")
        pdf_path = tmp_path / "test.pdf"
        doc.save(str(pdf_path))
        doc.close()

        mgr = ReferenceManager(refs_dir)
        mgr.add_file("PDF Ref", pdf_path)

        content = mgr.get_content("pdf-ref")
        assert "PDF reference content" in content
