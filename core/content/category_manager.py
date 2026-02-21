"""Hugo 계층형 카테고리 관리."""

from __future__ import annotations

import re
import shutil
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class Category:
    """카테고리 노드."""

    name: str
    slug: str
    children: list[Category] = field(default_factory=list)
    parent: str | None = None

    @property
    def path(self) -> str:
        """부모 경로를 포함한 전체 경로."""
        if self.parent:
            return f"{self.parent}/{self.slug}"
        return self.slug


def _slugify(text: str) -> str:
    """카테고리 이름을 slug로 변환."""
    text = unicodedata.normalize("NFC", text)
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_]+", "-", text)
    text = re.sub(r"-+", "-", text)
    return text.strip("-")


def _read_title(index_path: Path) -> str:
    """_index.md에서 title을 읽는다."""
    if not index_path.exists():
        return index_path.parent.name
    for line in index_path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if stripped.startswith("title:"):
            title = stripped[len("title:") :].strip()
            return title.strip("\"'")
    return index_path.parent.name


class CategoryManager:
    """Hugo의 디렉토리 기반 계층형 카테고리를 관리한다."""

    def __init__(self, hugo_content_path: Path) -> None:
        """
        Args:
            hugo_content_path: Hugo content 디렉토리 경로 (예: hugo-site/content).
        """
        self._content_path = hugo_content_path

    def list_all(self) -> list[Category]:
        """현재 카테고리 트리를 반환한다."""
        return self._scan_dir(self._content_path, parent_path=None)

    def _scan_dir(self, dir_path: Path, parent_path: str | None) -> list[Category]:
        """디렉토리를 재귀 탐색하여 카테고리 트리를 구성한다."""
        categories: list[Category] = []

        for child in sorted(dir_path.iterdir()):
            if not child.is_dir() or child.name.startswith((".", "_")):
                continue

            index_file = child / "_index.md"
            if not index_file.exists():
                continue

            name = _read_title(index_file)
            slug = child.name
            cat = Category(name=name, slug=slug, parent=parent_path)

            cat_path = f"{parent_path}/{slug}" if parent_path else slug
            cat.children = self._scan_dir(child, parent_path=cat_path)

            categories.append(cat)

        return categories

    def add(self, name: str, parent_path: str | None = None) -> Category:
        """
        카테고리를 추가한다.

        Args:
            name: 카테고리 표시명 (예: "Probability").
            parent_path: 부모 카테고리 경로 (예: "math"). None이면 최상위.

        Returns:
            생성된 Category.

        Raises:
            FileExistsError: 동일 slug의 카테고리가 이미 존재하는 경우.
        """
        slug = _slugify(name)

        if parent_path:
            dir_path = self._content_path / parent_path / slug
        else:
            dir_path = self._content_path / slug

        if dir_path.exists():
            raise FileExistsError(f"카테고리가 이미 존재합니다: {dir_path}")

        dir_path.mkdir(parents=True, exist_ok=False)

        index_content = (
            f'---\ntitle: "{name}"\nweight: 1\nbookCollapseSection: true\n---\n'
        )
        (dir_path / "_index.md").write_text(index_content, encoding="utf-8")

        return Category(name=name, slug=slug, parent=parent_path)

    def remove(self, category_path: str) -> bool:
        """
        카테고리를 삭제한다. 하위에 게시글(.md, _index.md 제외)이 없는 경우만 가능.

        Args:
            category_path: 카테고리 경로 (예: "math/algebra").

        Returns:
            삭제 성공 여부.

        Raises:
            ValueError: 하위 게시글이 존재하는 경우.
            FileNotFoundError: 카테고리가 존재하지 않는 경우.
        """
        dir_path = self._content_path / category_path

        if not dir_path.exists():
            raise FileNotFoundError(f"카테고리를 찾을 수 없습니다: {category_path}")

        posts = self._find_posts(dir_path)
        if posts:
            raise ValueError(
                f"하위 게시글이 존재하여 삭제할 수 없습니다: {[str(p) for p in posts]}"
            )

        shutil.rmtree(dir_path)
        return True

    def move(self, category_path: str, new_parent_path: str) -> bool:
        """
        카테고리를 다른 부모 아래로 이동한다.

        Args:
            category_path: 이동할 카테고리 경로 (예: "math/algebra").
            new_parent_path: 새 부모 경로 (예: "ai"). 빈 문자열이면 최상위.

        Returns:
            이동 성공 여부.

        Raises:
            FileNotFoundError: 카테고리가 존재하지 않는 경우.
            FileExistsError: 대상 위치에 동일 slug가 이미 존재하는 경우.
        """
        src_path = self._content_path / category_path

        if not src_path.exists():
            raise FileNotFoundError(f"카테고리를 찾을 수 없습니다: {category_path}")

        slug = src_path.name

        if new_parent_path:
            dest_path = self._content_path / new_parent_path / slug
        else:
            dest_path = self._content_path / slug

        if dest_path.exists():
            raise FileExistsError(
                f"대상 위치에 카테고리가 이미 존재합니다: {dest_path}"
            )

        dest_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(src_path), str(dest_path))
        return True

    def _find_posts(self, dir_path: Path) -> list[Path]:
        """디렉토리 내 게시글 파일(_index.md 제외)을 재귀적으로 찾는다."""
        posts: list[Path] = []
        for md_file in dir_path.rglob("*.md"):
            if md_file.name != "_index.md":
                posts.append(md_file)
        return posts
