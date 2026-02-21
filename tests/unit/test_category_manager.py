"""CategoryManager 단위 테스트."""

from pathlib import Path

import pytest

from core.content.category_manager import CategoryManager


def _make_category(tmp_path: Path, path: str, title: str) -> None:
    """테스트용 카테고리 디렉토리 + _index.md 생성."""
    d = tmp_path / path
    d.mkdir(parents=True, exist_ok=True)
    (d / "_index.md").write_text(
        f'---\ntitle: "{title}"\nweight: 1\nbookCollapseSection: true\n---\n',
        encoding="utf-8",
    )


def _make_post(tmp_path: Path, path: str) -> None:
    """테스트용 게시글 파일 생성."""
    p = tmp_path / path
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("---\ntitle: test\n---\ncontent\n", encoding="utf-8")


class TestListAll:
    def test_empty_content(self, tmp_path: Path) -> None:
        mgr = CategoryManager(tmp_path)
        assert mgr.list_all() == []

    def test_single_category(self, tmp_path: Path) -> None:
        _make_category(tmp_path, "math", "Mathematics")
        mgr = CategoryManager(tmp_path)
        cats = mgr.list_all()

        assert len(cats) == 1
        assert cats[0].name == "Mathematics"
        assert cats[0].slug == "math"
        assert cats[0].parent is None

    def test_nested_categories(self, tmp_path: Path) -> None:
        _make_category(tmp_path, "math", "Mathematics")
        _make_category(tmp_path, "math/probability", "Probability")
        _make_category(tmp_path, "math/algebra", "Algebra")

        mgr = CategoryManager(tmp_path)
        cats = mgr.list_all()

        assert len(cats) == 1
        math = cats[0]
        assert math.name == "Mathematics"
        assert len(math.children) == 2

        child_names = {c.name for c in math.children}
        assert child_names == {"Algebra", "Probability"}

    def test_ignores_dirs_without_index(self, tmp_path: Path) -> None:
        (tmp_path / "no_index").mkdir()
        _make_category(tmp_path, "valid", "Valid")

        mgr = CategoryManager(tmp_path)
        cats = mgr.list_all()

        assert len(cats) == 1
        assert cats[0].slug == "valid"

    def test_category_path(self, tmp_path: Path) -> None:
        _make_category(tmp_path, "math", "Mathematics")
        _make_category(tmp_path, "math/probability", "Probability")

        mgr = CategoryManager(tmp_path)
        cats = mgr.list_all()
        prob = cats[0].children[0]

        assert prob.path == "math/probability"


class TestAdd:
    def test_add_top_level(self, tmp_path: Path) -> None:
        mgr = CategoryManager(tmp_path)
        cat = mgr.add("Mathematics")

        assert cat.slug == "mathematics"
        assert cat.parent is None
        assert (tmp_path / "mathematics" / "_index.md").exists()

    def test_add_nested(self, tmp_path: Path) -> None:
        _make_category(tmp_path, "math", "Mathematics")

        mgr = CategoryManager(tmp_path)
        cat = mgr.add("Probability", parent_path="math")

        assert cat.slug == "probability"
        assert cat.parent == "math"
        assert (tmp_path / "math" / "probability" / "_index.md").exists()

    def test_add_duplicate_raises(self, tmp_path: Path) -> None:
        _make_category(tmp_path, "math", "Mathematics")

        mgr = CategoryManager(tmp_path)
        with pytest.raises(FileExistsError):
            mgr.add("math")

    def test_index_md_content(self, tmp_path: Path) -> None:
        mgr = CategoryManager(tmp_path)
        mgr.add("My Category")

        content = (tmp_path / "my-category" / "_index.md").read_text(encoding="utf-8")
        assert 'title: "My Category"' in content
        assert "bookCollapseSection: true" in content


class TestRemove:
    def test_remove_empty_category(self, tmp_path: Path) -> None:
        _make_category(tmp_path, "math", "Mathematics")

        mgr = CategoryManager(tmp_path)
        assert mgr.remove("math") is True
        assert not (tmp_path / "math").exists()

    def test_remove_with_posts_raises(self, tmp_path: Path) -> None:
        _make_category(tmp_path, "math", "Mathematics")
        _make_post(tmp_path, "math/my-post.md")

        mgr = CategoryManager(tmp_path)
        with pytest.raises(ValueError, match="하위 게시글"):
            mgr.remove("math")

    def test_remove_nonexistent_raises(self, tmp_path: Path) -> None:
        mgr = CategoryManager(tmp_path)
        with pytest.raises(FileNotFoundError):
            mgr.remove("nonexistent")

    def test_remove_with_nested_posts_raises(self, tmp_path: Path) -> None:
        _make_category(tmp_path, "math", "Mathematics")
        _make_category(tmp_path, "math/probability", "Probability")
        _make_post(tmp_path, "math/probability/post.md")

        mgr = CategoryManager(tmp_path)
        with pytest.raises(ValueError):
            mgr.remove("math")

    def test_remove_nested_empty(self, tmp_path: Path) -> None:
        _make_category(tmp_path, "math", "Mathematics")
        _make_category(tmp_path, "math/probability", "Probability")

        mgr = CategoryManager(tmp_path)
        assert mgr.remove("math/probability") is True
        assert not (tmp_path / "math" / "probability").exists()
        assert (tmp_path / "math").exists()


class TestMove:
    def test_move_category(self, tmp_path: Path) -> None:
        _make_category(tmp_path, "math", "Mathematics")
        _make_category(tmp_path, "ai", "AI")
        _make_category(tmp_path, "math/algebra", "Algebra")

        mgr = CategoryManager(tmp_path)
        assert mgr.move("math/algebra", "ai") is True
        assert (tmp_path / "ai" / "algebra" / "_index.md").exists()
        assert not (tmp_path / "math" / "algebra").exists()

    def test_move_to_top_level(self, tmp_path: Path) -> None:
        _make_category(tmp_path, "math", "Mathematics")
        _make_category(tmp_path, "math/algebra", "Algebra")

        mgr = CategoryManager(tmp_path)
        assert mgr.move("math/algebra", "") is True
        assert (tmp_path / "algebra" / "_index.md").exists()

    def test_move_nonexistent_raises(self, tmp_path: Path) -> None:
        mgr = CategoryManager(tmp_path)
        with pytest.raises(FileNotFoundError):
            mgr.move("nonexistent", "somewhere")

    def test_move_to_existing_raises(self, tmp_path: Path) -> None:
        _make_category(tmp_path, "math", "Mathematics")
        _make_category(tmp_path, "ai", "AI")
        _make_category(tmp_path, "math/algebra", "Algebra")
        _make_category(tmp_path, "ai/algebra", "Algebra")

        mgr = CategoryManager(tmp_path)
        with pytest.raises(FileExistsError):
            mgr.move("math/algebra", "ai")
