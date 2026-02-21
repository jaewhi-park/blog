"""Hugo 이미지 관리."""

from __future__ import annotations

import re
import tomllib
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse


@dataclass
class ImageInfo:
    """이미지 메타데이터."""

    filename: str
    source: str  # "upload", "pdf_extract"
    page: int | None = None  # PDF 추출 시 원본 페이지
    caption: str | None = None


def get_base_path(hugo_dir: Path) -> str:
    """hugo.toml의 baseURL에서 경로 부분을 추출한다.

    예: baseURL = "https://example.github.io/blog/" → "/blog"

    Args:
        hugo_dir: Hugo 프로젝트 디렉토리 (hugo.toml이 있는 곳).

    Returns:
        경로 문자열 (trailing slash 없음). 루트이면 빈 문자열.
    """
    toml_path = hugo_dir / "hugo.toml"
    if not toml_path.exists():
        return ""

    with open(toml_path, "rb") as f:
        config = tomllib.load(f)

    base_url = config.get("baseURL", "")
    if not base_url:
        return ""

    path = urlparse(base_url).path.rstrip("/")
    return path


class ImageManager:
    """Hugo static 디렉토리에 이미지를 저장하고 마크다운 참조를 생성한다."""

    def __init__(self, hugo_static_path: Path, *, base_path: str = "") -> None:
        """
        Args:
            hugo_static_path: Hugo static 디렉토리 경로 (예: hugo-site/static).
            base_path: baseURL 경로 (예: "/blog"). 이미지 참조에 접두사로 사용.
        """
        self._static_path = hugo_static_path
        self._base_path = base_path

    def save_image(
        self,
        image_data: bytes,
        post_slug: str,
        filename: str,
        *,
        caption: str | None = None,
        source: str = "upload",
    ) -> ImageInfo:
        """
        이미지를 Hugo static에 저장하고 ImageInfo를 반환한다.

        저장 경로: {hugo_static_path}/images/{post_slug}/{filename}

        Args:
            image_data: 이미지 바이너리 데이터.
            post_slug: 게시글 슬러그 (디렉토리명으로 사용).
            filename: 저장할 파일명.
            caption: 이미지 캡션.
            source: 이미지 출처 ("upload", "pdf_extract").

        Returns:
            저장된 이미지의 ImageInfo.

        Raises:
            ValueError: image_data가 비어있는 경우.
        """
        if not image_data:
            raise ValueError("이미지 데이터가 비어있습니다.")

        safe_filename = _sanitize_filename(filename)

        dir_path = self._static_path / "images" / post_slug
        dir_path.mkdir(parents=True, exist_ok=True)

        file_path = dir_path / safe_filename
        file_path.write_bytes(image_data)

        return ImageInfo(
            filename=safe_filename,
            source=source,
            caption=caption,
        )

    def generate_markdown_ref(self, post_slug: str, image_info: ImageInfo) -> str:
        """
        마크다운 이미지 참조 문자열을 생성한다.

        Args:
            post_slug: 게시글 슬러그.
            image_info: 이미지 메타데이터.

        Returns:
            ![caption](/images/post-slug/filename) 형태의 문자열.
        """
        alt_text = image_info.caption or image_info.filename
        path = f"{self._base_path}/images/{post_slug}/{image_info.filename}"
        return f"![{alt_text}]({path})"

    def list_images(self, post_slug: str) -> list[ImageInfo]:
        """
        게시글에 저장된 이미지 목록을 반환한다.

        Args:
            post_slug: 게시글 슬러그.

        Returns:
            해당 게시글의 ImageInfo 목록.
        """
        dir_path = self._static_path / "images" / post_slug
        if not dir_path.exists():
            return []

        images: list[ImageInfo] = []
        for file in sorted(dir_path.iterdir()):
            if file.is_file() and file.suffix.lower() in {
                ".png",
                ".jpg",
                ".jpeg",
                ".gif",
                ".svg",
                ".webp",
            }:
                images.append(ImageInfo(filename=file.name, source="upload"))
        return images

    def get_image_paths(self, post_slug: str) -> list[Path]:
        """게시글에 저장된 이미지 파일의 절대 경로 목록을 반환한다.

        Args:
            post_slug: 게시글 슬러그.

        Returns:
            이미지 파일 Path 목록.
        """
        dir_path = self._static_path / "images" / post_slug
        if not dir_path.exists():
            return []

        return [
            f
            for f in sorted(dir_path.iterdir())
            if f.is_file()
            and f.suffix.lower() in {".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp"}
        ]

    def delete_image(self, post_slug: str, filename: str) -> bool:
        """
        이미지를 삭제한다.

        Args:
            post_slug: 게시글 슬러그.
            filename: 삭제할 파일명.

        Returns:
            삭제 성공 여부.

        Raises:
            FileNotFoundError: 이미지가 존재하지 않는 경우.
        """
        file_path = self._static_path / "images" / post_slug / filename
        if not file_path.exists():
            raise FileNotFoundError(f"이미지를 찾을 수 없습니다: {file_path}")

        file_path.unlink()

        # 디렉토리가 비어있으면 삭제
        dir_path = file_path.parent
        if dir_path.exists() and not any(dir_path.iterdir()):
            dir_path.rmdir()

        return True


def _sanitize_filename(filename: str) -> str:
    """파일명을 URL-safe하게 변환한다.

    공백·특수문자를 하이픈으로 치환하고, 확장자는 보존한다.
    한글은 그대로 유지한다.

    예: "스크린샷 2026-02-21 오후 9.30.27.png" → "스크린샷-2026-02-21-오후-9-30-27.png"
    """
    stem = Path(filename).stem
    suffix = Path(filename).suffix.lower()

    text = unicodedata.normalize("NFC", stem)
    # 한글, 영문, 숫자, 하이픈 외의 문자를 하이픈으로 치환
    text = re.sub(r"[^\w-]", "-", text)
    # 연속 하이픈 제거
    text = re.sub(r"-+", "-", text)
    text = text.strip("-")

    if not text:
        text = "image"

    return f"{text}{suffix}"
