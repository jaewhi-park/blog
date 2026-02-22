"""프롬프트 템플릿 CRUD 및 렌더링."""

from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

import yaml

from core.exceptions import TemplateError, TemplateNotFoundError


@dataclass
class PromptTemplate:
    """프롬프트 템플릿."""

    id: str
    name: str
    description: str
    system_prompt: str
    user_prompt_template: str
    created_at: str
    updated_at: str


_REQUIRED_FIELDS = {
    "id",
    "name",
    "description",
    "system_prompt",
    "user_prompt_template",
}


def _now_iso() -> str:
    """현재 시각을 ISO 8601 문자열로 반환한다."""
    return datetime.now(tz=timezone.utc).isoformat()


class TemplateManager:
    """templates/ 디렉토리의 YAML 파일로 프롬프트 템플릿을 관리한다."""

    def __init__(self, templates_dir: Path) -> None:
        """
        Args:
            templates_dir: 템플릿 YAML 파일이 저장되는 디렉토리 경로.
        """
        self._dir = templates_dir

    def list_all(self) -> list[PromptTemplate]:
        """모든 템플릿을 updated_at 역순으로 반환한다."""
        if not self._dir.exists():
            return []

        templates: list[PromptTemplate] = []
        for path in sorted(self._dir.glob("*.yaml")):
            try:
                templates.append(self._load(path))
            except TemplateError:
                continue

        templates.sort(key=lambda t: t.updated_at, reverse=True)
        return templates

    def get(self, template_id: str) -> PromptTemplate:
        """단일 템플릿을 로드한다.

        Raises:
            TemplateNotFoundError: 템플릿 파일이 존재하지 않는 경우.
            TemplateError: YAML 파싱 또는 필드 검증 실패.
        """
        path = self._template_path(template_id)
        if not path.exists():
            raise TemplateNotFoundError(f"템플릿을 찾을 수 없습니다: {template_id}")
        return self._load(path)

    def create(self, template: PromptTemplate) -> PromptTemplate:
        """새 템플릿을 저장한다.

        created_at, updated_at이 비어 있으면 현재 시각으로 자동 설정한다.

        Raises:
            FileExistsError: 동일 id의 템플릿이 이미 존재하는 경우.
        """
        path = self._template_path(template.id)
        if path.exists():
            raise FileExistsError(f"템플릿이 이미 존재합니다: {template.id}")

        now = _now_iso()
        if not template.created_at:
            template.created_at = now
        if not template.updated_at:
            template.updated_at = now

        self._dir.mkdir(parents=True, exist_ok=True)
        self._save(path, template)
        return template

    def update(self, template_id: str, template: PromptTemplate) -> PromptTemplate:
        """기존 템플릿을 수정한다. updated_at을 자동 갱신한다.

        Raises:
            TemplateNotFoundError: 템플릿 파일이 존재하지 않는 경우.
        """
        path = self._template_path(template_id)
        if not path.exists():
            raise TemplateNotFoundError(f"템플릿을 찾을 수 없습니다: {template_id}")

        template.updated_at = _now_iso()
        self._save(path, template)
        return template

    def delete(self, template_id: str) -> bool:
        """템플릿을 삭제한다.

        Raises:
            TemplateNotFoundError: 템플릿 파일이 존재하지 않는 경우.
        """
        path = self._template_path(template_id)
        if not path.exists():
            raise TemplateNotFoundError(f"템플릿을 찾을 수 없습니다: {template_id}")

        path.unlink()
        return True

    def render(self, template_id: str, content: str, **kwargs: str) -> tuple[str, str]:
        """템플릿을 렌더링하여 (system_prompt, rendered_user_prompt)를 반환한다.

        user_prompt_template의 플레이스홀더를 치환한다.
        미사용 플레이스홀더는 빈 문자열로 대체되고,
        내용이 없는 ``## 섹션``은 자동 제거된다.

        Raises:
            TemplateNotFoundError: 템플릿이 존재하지 않는 경우.
        """
        tpl = self.get(template_id)

        placeholders: dict[str, str] = defaultdict(str)
        placeholders["content"] = content
        placeholders.update(kwargs)

        rendered = tpl.user_prompt_template.format_map(placeholders)
        rendered = self._strip_empty_sections(rendered)
        return (tpl.system_prompt, rendered)

    # ── 내부 헬퍼 ──

    @staticmethod
    def _strip_empty_sections(text: str) -> str:
        """빈 섹션(## 헤딩 뒤 내용이 없는 섹션)을 제거한다."""
        result = re.sub(
            r"^## [^\n]+\n+(?=## |\Z)",
            "",
            text,
            flags=re.MULTILINE,
        )
        result = re.sub(r"\n{3,}", "\n\n", result)
        return result.strip()

    def _template_path(self, template_id: str) -> Path:
        """템플릿 id로 파일 경로를 반환한다."""
        return self._dir / f"{template_id}.yaml"

    def _load(self, path: Path) -> PromptTemplate:
        """YAML 파일을 로드하여 PromptTemplate으로 변환한다."""
        data = self._load_yaml(path)
        return self._dict_to_template(data, path)

    @staticmethod
    def _load_yaml(path: Path) -> dict:
        """YAML 파일을 파싱한다.

        Raises:
            TemplateError: 파싱에 실패한 경우.
        """
        try:
            with open(path, encoding="utf-8") as f:
                data = yaml.safe_load(f)
        except yaml.YAMLError as e:
            raise TemplateError(f"YAML 파싱 실패 ({path.name}): {e}") from e

        if not isinstance(data, dict):
            raise TemplateError(f"템플릿이 dict 형식이 아닙니다: {path.name}")

        return data

    @staticmethod
    def _dict_to_template(data: dict, path: Path) -> PromptTemplate:
        """dict를 PromptTemplate으로 변환한다.

        Raises:
            TemplateError: 필수 필드가 누락된 경우.
        """
        missing = _REQUIRED_FIELDS - set(data.keys())
        if missing:
            raise TemplateError(
                f"필수 필드가 누락되었습니다 ({path.name}): {', '.join(sorted(missing))}"
            )

        return PromptTemplate(
            id=str(data["id"]),
            name=str(data["name"]),
            description=str(data["description"]),
            system_prompt=str(data["system_prompt"]),
            user_prompt_template=str(data["user_prompt_template"]),
            created_at=str(data.get("created_at", "")),
            updated_at=str(data.get("updated_at", "")),
        )

    @staticmethod
    def _save(path: Path, template: PromptTemplate) -> None:
        """PromptTemplate을 YAML 파일로 저장한다."""
        with open(path, "w", encoding="utf-8") as f:
            yaml.safe_dump(
                asdict(template),
                f,
                allow_unicode=True,
                sort_keys=False,
                default_flow_style=False,
            )
