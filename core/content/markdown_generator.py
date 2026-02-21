"""Hugo 호환 마크다운 파일 생성기."""

from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from pathlib import Path

KST = timezone(timedelta(hours=9))


@dataclass
class PostMetadata:
    """게시글 메타데이터 (Hugo front matter)."""

    title: str
    date: str = ""
    categories: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    draft: bool = False
    math: bool = True
    llm_generated: bool = False
    llm_assisted: bool = False
    llm_disclaimer: bool = False
    llm_model: str | None = None
    sources: list[str] | None = None

    def __post_init__(self) -> None:
        if not self.date:
            self.date = datetime.now(KST).strftime("%Y-%m-%dT%H:%M:%S+09:00")
        if self.llm_generated or self.llm_assisted:
            self.llm_disclaimer = True


def slugify(text: str) -> str:
    """제목을 URL-safe 슬러그로 변환. 한글을 보존한다."""
    import re
    import unicodedata

    text = unicodedata.normalize("NFC", text)
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_]+", "-", text)
    text = re.sub(r"-+", "-", text)
    return text.strip("-")


class MarkdownGenerator:
    """Hugo 호환 마크다운 파일을 생성한다."""

    def generate(self, metadata: PostMetadata, content: str) -> str:
        """front matter + content 마크다운 문자열 생성."""
        lines: list[str] = ["---"]

        lines.append(f'title: "{metadata.title}"')
        lines.append(f"date: {metadata.date}")

        if metadata.categories:
            cats = ", ".join(f'"{c}"' for c in metadata.categories)
            lines.append(f"categories: [{cats}]")

        if metadata.tags:
            tags = ", ".join(f'"{t}"' for t in metadata.tags)
            lines.append(f"tags: [{tags}]")

        if metadata.draft:
            lines.append("draft: true")

        if metadata.math:
            lines.append("math: true")

        if metadata.llm_generated:
            lines.append("llm_generated: true")

        if metadata.llm_assisted:
            lines.append("llm_assisted: true")

        if metadata.llm_disclaimer:
            lines.append("llm_disclaimer: true")

        if metadata.llm_model:
            lines.append(f'llm_model: "{metadata.llm_model}"')

        if metadata.sources:
            srcs = ", ".join(f'"{s}"' for s in metadata.sources)
            lines.append(f"sources: [{srcs}]")

        lines.append("---")
        lines.append("")

        # 면책 조항 shortcode 자동 삽입
        if metadata.llm_disclaimer:
            lines.append("{{< disclaimer >}}")
            lines.append("")

        lines.append(content)
        lines.append("")

        return "\n".join(lines)

    def save(
        self,
        metadata: PostMetadata,
        content: str,
        base_path: Path,
        category_path: str = "",
    ) -> Path:
        """
        Hugo content 디렉토리에 파일 저장.

        Args:
            metadata: 게시글 메타데이터.
            content: 마크다운 본문.
            base_path: Hugo content 디렉토리 경로 (예: hugo-site/content).
            category_path: 카테고리 경로 (예: "math/probability").

        Returns:
            저장된 파일의 Path.
        """
        slug = slugify(metadata.title)
        if not slug:
            slug = f"post-{datetime.now(KST).strftime('%Y%m%d%H%M%S')}"

        if category_path:
            dir_path = base_path / category_path
        else:
            dir_path = base_path

        dir_path.mkdir(parents=True, exist_ok=True)

        file_path = dir_path / f"{slug}.md"
        markdown = self.generate(metadata, content)
        file_path.write_text(markdown, encoding="utf-8")

        return file_path
