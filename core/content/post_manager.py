"""기존 게시글 조회·수정·삭제 관리."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml

from core.content.markdown_generator import MarkdownGenerator, PostMetadata


@dataclass
class PostInfo:
    """글 목록 표시용 요약 정보."""

    file_path: Path
    title: str
    date: str
    categories: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    draft: bool = False


class PostManager:
    """Hugo content 디렉토리의 게시글을 관리한다."""

    def __init__(self, content_path: Path) -> None:
        """
        Args:
            content_path: Hugo content 디렉토리 경로 (예: hugo-site/content).
        """
        self._content_path = content_path

    def list_posts(self) -> list[PostInfo]:
        """content 디렉토리의 모든 .md 파일(_index.md 제외)을 스캔.

        YAML front matter에서 title, date, categories, tags, draft를 추출.
        date 역순 정렬.

        Returns:
            PostInfo 리스트 (date 역순).
        """
        posts: list[PostInfo] = []

        for md_file in self._content_path.rglob("*.md"):
            if md_file.name == "_index.md":
                continue

            front_matter = self._parse_front_matter(md_file)
            if front_matter is None:
                continue

            posts.append(
                PostInfo(
                    file_path=md_file,
                    title=front_matter.get("title", md_file.stem),
                    date=str(front_matter.get("date", "")),
                    categories=_ensure_list(front_matter.get("categories", [])),
                    tags=_ensure_list(front_matter.get("tags", [])),
                    draft=bool(front_matter.get("draft", False)),
                )
            )

        posts.sort(key=lambda p: p.date, reverse=True)
        return posts

    def load_post(self, file_path: Path) -> tuple[PostMetadata, str]:
        """파일을 읽어 (PostMetadata, 본문) 튜플 반환.

        Args:
            file_path: 게시글 파일 경로.

        Returns:
            (PostMetadata, 본문 문자열) 튜플.
            disclaimer shortcode 줄({{< disclaimer >}})은 본문에서 제거된다.

        Raises:
            FileNotFoundError: 파일이 존재하지 않는 경우.
        """
        text = file_path.read_text(encoding="utf-8")
        front_matter, body = self._split_front_matter(text)

        # disclaimer shortcode 줄 제거
        body_lines = body.splitlines()
        body_lines = [ln for ln in body_lines if ln.strip() != "{{< disclaimer >}}"]
        body = "\n".join(body_lines).strip()

        fm = front_matter or {}
        metadata = PostMetadata(
            title=fm.get("title", ""),
            date=str(fm.get("date", "")),
            categories=_ensure_list(fm.get("categories", [])),
            tags=_ensure_list(fm.get("tags", [])),
            draft=bool(fm.get("draft", False)),
            math=bool(fm.get("math", True)),
            llm_generated=bool(fm.get("llm_generated", False)),
            llm_assisted=bool(fm.get("llm_assisted", False)),
            llm_disclaimer=bool(fm.get("llm_disclaimer", False)),
            llm_model=fm.get("llm_model"),
            sources=fm.get("sources"),
        )

        return metadata, body

    def save_post(self, file_path: Path, metadata: PostMetadata, content: str) -> Path:
        """기존 파일 덮어쓰기.

        MarkdownGenerator.generate()로 재생성 후 저장한다.

        Args:
            file_path: 저장할 파일 경로.
            metadata: 게시글 메타데이터.
            content: 마크다운 본문.

        Returns:
            저장된 파일 경로.
        """
        gen = MarkdownGenerator()
        markdown = gen.generate(metadata, content)
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(markdown, encoding="utf-8")
        return file_path

    def delete_post(self, file_path: Path) -> None:
        """파일 삭제.

        Args:
            file_path: 삭제할 파일 경로.

        Raises:
            FileNotFoundError: 파일이 존재하지 않는 경우.
        """
        if not file_path.exists():
            raise FileNotFoundError(f"파일을 찾을 수 없습니다: {file_path}")
        file_path.unlink()

    # ── private helpers ──────────────────────────────────────

    def _parse_front_matter(self, file_path: Path) -> dict | None:
        """파일에서 YAML front matter를 파싱한다."""
        try:
            text = file_path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            return None

        fm, _ = self._split_front_matter(text)
        return fm

    @staticmethod
    def _split_front_matter(text: str) -> tuple[dict | None, str]:
        """--- 구분자로 front matter와 본문을 분리한다."""
        if not text.startswith("---"):
            return None, text

        parts = text.split("---", 2)
        if len(parts) < 3:
            return None, text

        yaml_str = parts[1]
        body = parts[2]

        try:
            fm = yaml.safe_load(yaml_str)
        except yaml.YAMLError:
            return None, text

        if not isinstance(fm, dict):
            return None, text

        return fm, body


def _ensure_list(value: object) -> list[str]:
    """값이 리스트가 아니면 빈 리스트를 반환한다."""
    if isinstance(value, list):
        return [str(v) for v in value]
    return []
