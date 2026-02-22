"""스타일 레퍼런스 관리 — 파일/URL 기반 문체 예시 CRUD + 캐시."""

from __future__ import annotations

import asyncio
import re
import shutil
import unicodedata
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

import yaml

from core.exceptions import ReferenceError, ReferenceNotFoundError
from core.sources.url_crawler import URLCrawler

_INDEX_FILE = "index.yaml"


def _slugify(text: str) -> str:
    """표시명을 id용 slug로 변환한다."""
    text = unicodedata.normalize("NFC", text)
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_]+", "-", text)
    text = re.sub(r"-+", "-", text)
    return text.strip("-")


def _now_iso() -> str:
    """현재 시각을 ISO 8601 문자열로 반환한다."""
    return datetime.now(tz=timezone.utc).isoformat()


@dataclass
class StyleReference:
    """스타일 레퍼런스."""

    id: str
    name: str
    source_type: str  # "file" | "url"
    source_path: str  # 파일 경로(상대) 또는 URL
    content_cache: str | None  # URL 크롤링 결과 캐시
    file_type: str | None  # "pdf", "md", "txt" (파일인 경우)
    created_at: str
    updated_at: str


_FILE_EXTENSIONS = {"pdf", "md", "txt"}


class ReferenceManager:
    """references/ 디렉토리에서 스타일 레퍼런스를 관리한다.

    메타데이터는 ``references/index.yaml``에 저장하고,
    파일 레퍼런스는 ``references/`` 디렉토리에 복사한다.
    URL 레퍼런스는 크롤링 결과를 ``content_cache``에 저장한다.
    """

    def __init__(self, references_dir: Path) -> None:
        """
        Args:
            references_dir: 레퍼런스 파일과 index.yaml이 저장되는 디렉토리.
        """
        self._dir = references_dir
        self._crawler = URLCrawler()

    # ── Public API ──

    def list_all(self) -> list[StyleReference]:
        """모든 레퍼런스를 updated_at 역순으로 반환한다."""
        index = self._load_index()
        refs = [self._dict_to_ref(d) for d in index]
        refs.sort(key=lambda r: r.updated_at, reverse=True)
        return refs

    def get(self, ref_id: str) -> StyleReference:
        """단일 레퍼런스를 반환한다.

        Raises:
            ReferenceNotFoundError: 레퍼런스가 존재하지 않는 경우.
        """
        index = self._load_index()
        for entry in index:
            if entry.get("id") == ref_id:
                return self._dict_to_ref(entry)
        raise ReferenceNotFoundError(f"레퍼런스를 찾을 수 없습니다: {ref_id}")

    def add_file(self, name: str, file_path: Path) -> StyleReference:
        """파일 레퍼런스를 추가한다.

        파일을 references/ 디렉토리에 복사하고 index.yaml에 등록한다.

        Args:
            name: 표시명.
            file_path: 원본 파일 경로.

        Returns:
            생성된 StyleReference.

        Raises:
            FileNotFoundError: 원본 파일이 존재하지 않는 경우.
            ReferenceError: 지원하지 않는 파일 확장자인 경우.
            FileExistsError: 동일 id의 레퍼런스가 이미 존재하는 경우.
        """
        file_path = Path(file_path)
        if not file_path.exists():
            raise FileNotFoundError(f"파일을 찾을 수 없습니다: {file_path}")

        ext = file_path.suffix.lstrip(".").lower()
        if ext not in _FILE_EXTENSIONS:
            raise ReferenceError(
                f"지원하지 않는 파일 형식입니다: .{ext} "
                f"(지원: {', '.join(sorted(_FILE_EXTENSIONS))})"
            )

        ref_id = _slugify(name)
        self._ensure_unique_id(ref_id)

        self._dir.mkdir(parents=True, exist_ok=True)
        dest = self._dir / f"{ref_id}.{ext}"
        shutil.copy2(str(file_path), str(dest))

        now = _now_iso()
        ref = StyleReference(
            id=ref_id,
            name=name,
            source_type="file",
            source_path=f"{ref_id}.{ext}",
            content_cache=None,
            file_type=ext,
            created_at=now,
            updated_at=now,
        )

        self._append_to_index(ref)
        return ref

    def add_url(self, name: str, url: str) -> StyleReference:
        """URL 레퍼런스를 추가한다.

        URL을 크롤링하여 텍스트를 캐시에 저장한다.

        Args:
            name: 표시명.
            url: 크롤링할 URL.

        Returns:
            생성된 StyleReference.

        Raises:
            ReferenceError: 크롤링에 실패한 경우.
            FileExistsError: 동일 id의 레퍼런스가 이미 존재하는 경우.
        """
        ref_id = _slugify(name)
        self._ensure_unique_id(ref_id)

        try:
            crawled = asyncio.run(self._crawler.crawl(url))
            content_cache = crawled.text
        except Exception as e:
            raise ReferenceError(f"URL 크롤링 실패: {url} — {e}") from e

        self._dir.mkdir(parents=True, exist_ok=True)

        now = _now_iso()
        ref = StyleReference(
            id=ref_id,
            name=name,
            source_type="url",
            source_path=url,
            content_cache=content_cache,
            file_type=None,
            created_at=now,
            updated_at=now,
        )

        self._append_to_index(ref)
        return ref

    def remove(self, ref_id: str) -> bool:
        """레퍼런스를 삭제한다.

        Raises:
            ReferenceNotFoundError: 레퍼런스가 존재하지 않는 경우.
        """
        index = self._load_index()
        found = None
        for i, entry in enumerate(index):
            if entry.get("id") == ref_id:
                found = i
                break

        if found is None:
            raise ReferenceNotFoundError(f"레퍼런스를 찾을 수 없습니다: {ref_id}")

        entry = index.pop(found)
        self._save_index(index)

        # 파일 레퍼런스인 경우 복사된 파일도 삭제
        if entry.get("source_type") == "file" and entry.get("source_path"):
            file_path = self._dir / entry["source_path"]
            if file_path.exists():
                file_path.unlink()

        return True

    def get_content(self, ref_id: str) -> str:
        """레퍼런스의 텍스트 내용을 반환한다.

        파일 레퍼런스는 직접 읽고, URL 레퍼런스는 캐시에서 반환한다.
        PDF 파일은 텍스트 추출을 수행한다.

        Raises:
            ReferenceNotFoundError: 레퍼런스가 존재하지 않는 경우.
            ReferenceError: 파일 읽기에 실패한 경우.
        """
        ref = self.get(ref_id)

        if ref.source_type == "url":
            if ref.content_cache:
                return ref.content_cache
            raise ReferenceError(f"URL 레퍼런스의 캐시가 비어 있습니다: {ref_id}")

        # 파일 레퍼런스
        file_path = self._dir / ref.source_path
        if not file_path.exists():
            raise ReferenceError(f"레퍼런스 파일을 찾을 수 없습니다: {file_path}")

        if ref.file_type == "pdf":
            return self._read_pdf(file_path)

        try:
            return file_path.read_text(encoding="utf-8")
        except UnicodeDecodeError as e:
            raise ReferenceError(f"파일 읽기 실패: {file_path} — {e}") from e

    # ── 내부 헬퍼 ──

    def _index_path(self) -> Path:
        """index.yaml 파일 경로를 반환한다."""
        return self._dir / _INDEX_FILE

    def _load_index(self) -> list[dict]:
        """index.yaml을 로드한다."""
        path = self._index_path()
        if not path.exists():
            return []
        try:
            with open(path, encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
        except yaml.YAMLError as e:
            raise ReferenceError(f"index.yaml 파싱 실패: {e}") from e

        return data.get("references", [])

    def _save_index(self, entries: list[dict]) -> None:
        """index.yaml을 저장한다."""
        self._dir.mkdir(parents=True, exist_ok=True)
        with open(self._index_path(), "w", encoding="utf-8") as f:
            yaml.safe_dump(
                {"references": entries},
                f,
                allow_unicode=True,
                sort_keys=False,
                default_flow_style=False,
            )

    def _append_to_index(self, ref: StyleReference) -> None:
        """index.yaml에 레퍼런스를 추가한다."""
        index = self._load_index()
        index.append(asdict(ref))
        self._save_index(index)

    def _ensure_unique_id(self, ref_id: str) -> None:
        """id 중복을 검사한다."""
        index = self._load_index()
        for entry in index:
            if entry.get("id") == ref_id:
                raise FileExistsError(f"레퍼런스가 이미 존재합니다: {ref_id}")

    @staticmethod
    def _dict_to_ref(data: dict) -> StyleReference:
        """dict를 StyleReference로 변환한다."""
        return StyleReference(
            id=str(data.get("id", "")),
            name=str(data.get("name", "")),
            source_type=str(data.get("source_type", "")),
            source_path=str(data.get("source_path", "")),
            content_cache=data.get("content_cache"),
            file_type=data.get("file_type"),
            created_at=str(data.get("created_at", "")),
            updated_at=str(data.get("updated_at", "")),
        )

    @staticmethod
    def _read_pdf(file_path: Path) -> str:
        """PDF에서 텍스트를 추출한다."""
        from core.sources.pdf_parser import PDFParser

        parser = PDFParser()
        result = parser.parse(file_path, extract_images=False)
        return result.text
