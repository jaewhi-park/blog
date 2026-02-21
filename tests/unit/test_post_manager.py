"""PostManager 단위 테스트."""

from __future__ import annotations

from pathlib import Path

import pytest

from core.content.markdown_generator import PostMetadata
from core.content.post_manager import PostManager


@pytest.fixture()
def content_dir(tmp_path: Path) -> Path:
    """Hugo content 디렉토리 구조를 생성한다."""
    # _index.md (제외 대상)
    (tmp_path / "_index.md").write_text("---\ntitle: Home\n---\n", encoding="utf-8")

    # 카테고리 _index.md (제외 대상)
    math_dir = tmp_path / "math"
    math_dir.mkdir()
    (math_dir / "_index.md").write_text('---\ntitle: "Math"\n---\n', encoding="utf-8")

    # 게시글 1
    (math_dir / "post-a.md").write_text(
        '---\ntitle: "Post A"\ndate: 2026-02-20T10:00:00+09:00\n'
        'categories: ["math"]\ntags: ["algebra"]\ndraft: false\nmath: true\n---\n\n'
        "Post A body\n",
        encoding="utf-8",
    )

    # 게시글 2 (더 최신)
    (math_dir / "post-b.md").write_text(
        '---\ntitle: "Post B"\ndate: 2026-02-21T10:00:00+09:00\n'
        'categories: ["math"]\ntags: ["probability"]\ndraft: true\nmath: true\n---\n\n'
        "{{< disclaimer >}}\n\nPost B body with **bold**\n",
        encoding="utf-8",
    )

    # 게시글 3 (최상위)
    (tmp_path / "hello.md").write_text(
        '---\ntitle: "Hello World"\ndate: 2026-01-01T00:00:00+09:00\n---\n\n'
        "Hello content\n",
        encoding="utf-8",
    )

    return tmp_path


class TestListPosts:
    """list_posts 테스트."""

    def test_list_posts(self, content_dir: Path) -> None:
        """_index.md를 제외하고 올바른 PostInfo를 반환한다."""
        mgr = PostManager(content_dir)
        posts = mgr.list_posts()

        assert len(posts) == 3

        titles = {p.title for p in posts}
        assert titles == {"Post A", "Post B", "Hello World"}

        # _index.md는 포함되지 않아야 한다
        filenames = {p.file_path.name for p in posts}
        assert "_index.md" not in filenames

    def test_list_posts_sorted_by_date(self, content_dir: Path) -> None:
        """날짜 역순으로 정렬된다."""
        mgr = PostManager(content_dir)
        posts = mgr.list_posts()

        dates = [p.date for p in posts]
        assert dates == sorted(dates, reverse=True)
        assert posts[0].title == "Post B"
        assert posts[-1].title == "Hello World"

    def test_list_posts_fields(self, content_dir: Path) -> None:
        """PostInfo 필드가 올바르게 매핑된다."""
        mgr = PostManager(content_dir)
        posts = mgr.list_posts()

        post_b = next(p for p in posts if p.title == "Post B")
        assert post_b.categories == ["math"]
        assert post_b.tags == ["probability"]
        assert post_b.draft is True


class TestLoadPost:
    """load_post 테스트."""

    def test_load_post(self, content_dir: Path) -> None:
        """front matter 파싱 + 본문 분리 + disclaimer 줄 제거."""
        mgr = PostManager(content_dir)
        file_path = content_dir / "math" / "post-b.md"

        metadata, body = mgr.load_post(file_path)

        assert metadata.title == "Post B"
        assert metadata.draft is True
        assert metadata.categories == ["math"]
        assert metadata.tags == ["probability"]

        # disclaimer shortcode가 제거되어야 한다
        assert "{{< disclaimer >}}" not in body
        assert "Post B body with **bold**" in body

    def test_load_post_minimal_front_matter(self, tmp_path: Path) -> None:
        """필수 필드만 있을 때 기본값 처리."""
        post = tmp_path / "minimal.md"
        post.write_text(
            '---\ntitle: "Minimal"\n---\n\nMinimal body\n', encoding="utf-8"
        )

        mgr = PostManager(tmp_path)
        metadata, body = mgr.load_post(post)

        assert metadata.title == "Minimal"
        assert metadata.categories == []
        assert metadata.tags == []
        assert metadata.draft is False
        assert metadata.math is True  # 기본값
        assert "Minimal body" in body

    def test_load_post_not_found(self, tmp_path: Path) -> None:
        """존재하지 않는 파일은 FileNotFoundError."""
        mgr = PostManager(tmp_path)
        with pytest.raises(FileNotFoundError):
            mgr.load_post(tmp_path / "nonexistent.md")


class TestSavePost:
    """save_post 테스트."""

    def test_save_post(self, content_dir: Path) -> None:
        """파일 덮어쓰기 확인."""
        mgr = PostManager(content_dir)
        file_path = content_dir / "math" / "post-a.md"

        metadata = PostMetadata(
            title="Post A Updated",
            date="2026-02-20T10:00:00+09:00",
            categories=["math"],
            tags=["algebra", "linear"],
            math=True,
        )

        result = mgr.save_post(file_path, metadata, "Updated body content")
        assert result == file_path

        # 파일이 덮어써졌는지 확인
        text = file_path.read_text(encoding="utf-8")
        assert "Post A Updated" in text
        assert "Updated body content" in text
        assert "linear" in text


class TestDeletePost:
    """delete_post 테스트."""

    def test_delete_post(self, content_dir: Path) -> None:
        """파일 삭제 확인."""
        mgr = PostManager(content_dir)
        file_path = content_dir / "hello.md"
        assert file_path.exists()

        mgr.delete_post(file_path)
        assert not file_path.exists()

    def test_delete_post_not_found(self, tmp_path: Path) -> None:
        """존재하지 않는 파일은 FileNotFoundError."""
        mgr = PostManager(tmp_path)
        with pytest.raises(FileNotFoundError):
            mgr.delete_post(tmp_path / "nonexistent.md")
