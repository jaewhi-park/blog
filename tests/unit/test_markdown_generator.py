"""MarkdownGenerator 단위 테스트."""

from pathlib import Path

from core.content.markdown_generator import MarkdownGenerator, PostMetadata, _slugify


class TestPostMetadata:
    def test_default_date_is_set(self) -> None:
        meta = PostMetadata(title="Test")
        assert meta.date != ""
        assert "T" in meta.date

    def test_llm_generated_sets_disclaimer(self) -> None:
        meta = PostMetadata(title="Test", llm_generated=True)
        assert meta.llm_disclaimer is True

    def test_llm_assisted_sets_disclaimer(self) -> None:
        meta = PostMetadata(title="Test", llm_assisted=True)
        assert meta.llm_disclaimer is True

    def test_no_llm_no_disclaimer(self) -> None:
        meta = PostMetadata(title="Test")
        assert meta.llm_disclaimer is False


class TestSlugify:
    def test_basic(self) -> None:
        assert _slugify("Hello World") == "hello-world"

    def test_special_characters(self) -> None:
        assert _slugify("Wigner의 반원 법칙") == "wigner의-반원-법칙"

    def test_multiple_spaces(self) -> None:
        assert _slugify("a   b   c") == "a-b-c"

    def test_empty_string(self) -> None:
        assert _slugify("") == ""


class TestMarkdownGenerator:
    def setup_method(self) -> None:
        self.gen = MarkdownGenerator()

    def test_generate_basic(self) -> None:
        meta = PostMetadata(
            title="테스트 게시글",
            date="2026-02-21T09:00:00+09:00",
            categories=["math", "probability"],
            tags=["test"],
        )
        result = self.gen.generate(meta, "본문 내용입니다.")

        assert "---" in result
        assert 'title: "테스트 게시글"' in result
        assert "date: 2026-02-21T09:00:00+09:00" in result
        assert 'categories: ["math", "probability"]' in result
        assert 'tags: ["test"]' in result
        assert "math: true" in result
        assert "본문 내용입니다." in result

    def test_generate_no_disclaimer_without_llm(self) -> None:
        meta = PostMetadata(
            title="Test",
            date="2026-01-01T00:00:00+09:00",
        )
        result = self.gen.generate(meta, "content")

        assert "llm_disclaimer" not in result
        assert "{{< disclaimer >}}" not in result

    def test_generate_llm_generated_includes_disclaimer(self) -> None:
        meta = PostMetadata(
            title="Test",
            date="2026-01-01T00:00:00+09:00",
            llm_generated=True,
            llm_model="claude-sonnet",
        )
        result = self.gen.generate(meta, "content")

        assert "llm_generated: true" in result
        assert "llm_disclaimer: true" in result
        assert "{{< disclaimer >}}" in result
        assert 'llm_model: "claude-sonnet"' in result

    def test_generate_llm_assisted_includes_disclaimer(self) -> None:
        meta = PostMetadata(
            title="Test",
            date="2026-01-01T00:00:00+09:00",
            llm_assisted=True,
        )
        result = self.gen.generate(meta, "content")

        assert "llm_assisted: true" in result
        assert "llm_disclaimer: true" in result
        assert "{{< disclaimer >}}" in result

    def test_generate_with_sources(self) -> None:
        meta = PostMetadata(
            title="Test",
            date="2026-01-01T00:00:00+09:00",
            sources=["paper.pdf", "https://example.com"],
        )
        result = self.gen.generate(meta, "content")

        assert 'sources: ["paper.pdf", "https://example.com"]' in result

    def test_generate_draft(self) -> None:
        meta = PostMetadata(
            title="Draft Post",
            date="2026-01-01T00:00:00+09:00",
            draft=True,
        )
        result = self.gen.generate(meta, "content")

        assert "draft: true" in result

    def test_save_creates_file(self, tmp_path: Path) -> None:
        meta = PostMetadata(
            title="Save Test",
            date="2026-01-01T00:00:00+09:00",
            categories=["math"],
        )
        file_path = self.gen.save(meta, "본문", tmp_path, "math/probability")

        assert file_path.exists()
        assert file_path.name == "save-test.md"
        assert file_path.parent == tmp_path / "math" / "probability"

        content = file_path.read_text(encoding="utf-8")
        assert 'title: "Save Test"' in content
        assert "본문" in content

    def test_save_without_category(self, tmp_path: Path) -> None:
        meta = PostMetadata(
            title="No Category",
            date="2026-01-01T00:00:00+09:00",
        )
        file_path = self.gen.save(meta, "content", tmp_path)

        assert file_path.exists()
        assert file_path.parent == tmp_path
