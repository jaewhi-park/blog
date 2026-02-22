"""TemplateManager 단위 테스트."""

from pathlib import Path

import pytest
import yaml

from core.content.template_manager import PromptTemplate, TemplateManager
from core.exceptions import TemplateError, TemplateNotFoundError


def _make_template_yaml(
    tmp_path: Path,
    template_id: str = "lecture_note",
    name: str = "렉쳐노트",
    description: str = "수학 렉쳐노트 스타일로 작성",
    system_prompt: str = "You are a mathematics educator.",
    user_prompt_template: str = "다음 내용을 작성해주세요.\n\n{content}\n\n{style_reference}",
    created_at: str = "2026-01-01T00:00:00+00:00",
    updated_at: str = "2026-01-01T00:00:00+00:00",
) -> Path:
    """테스트용 템플릿 YAML 파일 생성."""
    data = {
        "id": template_id,
        "name": name,
        "description": description,
        "system_prompt": system_prompt,
        "user_prompt_template": user_prompt_template,
        "created_at": created_at,
        "updated_at": updated_at,
    }
    path = tmp_path / f"{template_id}.yaml"
    with open(path, "w", encoding="utf-8") as f:
        yaml.safe_dump(data, f, allow_unicode=True, sort_keys=False)
    return path


def _make_template(
    template_id: str = "lecture_note",
    name: str = "렉쳐노트",
    description: str = "수학 렉쳐노트 스타일로 작성",
    system_prompt: str = "You are a mathematics educator.",
    user_prompt_template: str = "다음 내용을 작성해주세요.\n\n{content}\n\n{style_reference}",
    created_at: str = "",
    updated_at: str = "",
) -> PromptTemplate:
    """테스트용 PromptTemplate 인스턴스 생성."""
    return PromptTemplate(
        id=template_id,
        name=name,
        description=description,
        system_prompt=system_prompt,
        user_prompt_template=user_prompt_template,
        created_at=created_at,
        updated_at=updated_at,
    )


class TestPromptTemplate:
    def test_dataclass_creation(self) -> None:
        tpl = PromptTemplate(
            id="test",
            name="Test",
            description="A test template",
            system_prompt="system",
            user_prompt_template="{content}",
            created_at="2026-01-01",
            updated_at="2026-01-01",
        )
        assert tpl.id == "test"
        assert tpl.name == "Test"
        assert tpl.user_prompt_template == "{content}"


class TestListAll:
    def test_empty_directory(self, tmp_path: Path) -> None:
        mgr = TemplateManager(tmp_path)
        assert mgr.list_all() == []

    def test_nonexistent_directory(self, tmp_path: Path) -> None:
        mgr = TemplateManager(tmp_path / "nonexistent")
        assert mgr.list_all() == []

    def test_multiple_templates(self, tmp_path: Path) -> None:
        _make_template_yaml(tmp_path, "alpha", updated_at="2026-01-01T00:00:00+00:00")
        _make_template_yaml(tmp_path, "beta", updated_at="2026-02-01T00:00:00+00:00")

        mgr = TemplateManager(tmp_path)
        templates = mgr.list_all()

        assert len(templates) == 2
        assert templates[0].id == "beta"
        assert templates[1].id == "alpha"

    def test_sorted_by_updated_at_descending(self, tmp_path: Path) -> None:
        _make_template_yaml(tmp_path, "old", updated_at="2025-01-01T00:00:00+00:00")
        _make_template_yaml(tmp_path, "mid", updated_at="2025-06-01T00:00:00+00:00")
        _make_template_yaml(tmp_path, "new", updated_at="2026-01-01T00:00:00+00:00")

        mgr = TemplateManager(tmp_path)
        templates = mgr.list_all()

        assert [t.id for t in templates] == ["new", "mid", "old"]

    def test_skips_invalid_yaml(self, tmp_path: Path) -> None:
        _make_template_yaml(tmp_path, "valid")
        (tmp_path / "invalid.yaml").write_text(": : bad yaml", encoding="utf-8")

        mgr = TemplateManager(tmp_path)
        templates = mgr.list_all()

        assert len(templates) == 1
        assert templates[0].id == "valid"


class TestGet:
    def test_load_template(self, tmp_path: Path) -> None:
        _make_template_yaml(tmp_path, "lecture_note", name="렉쳐노트")

        mgr = TemplateManager(tmp_path)
        tpl = mgr.get("lecture_note")

        assert tpl.id == "lecture_note"
        assert tpl.name == "렉쳐노트"
        assert tpl.system_prompt == "You are a mathematics educator."

    def test_nonexistent_raises(self, tmp_path: Path) -> None:
        mgr = TemplateManager(tmp_path)
        with pytest.raises(TemplateNotFoundError, match="찾을 수 없습니다"):
            mgr.get("nonexistent")

    def test_invalid_yaml_raises(self, tmp_path: Path) -> None:
        (tmp_path / "bad.yaml").write_text("[ unclosed", encoding="utf-8")

        mgr = TemplateManager(tmp_path)
        with pytest.raises(TemplateError, match="YAML 파싱 실패"):
            mgr.get("bad")

    def test_missing_required_field_raises(self, tmp_path: Path) -> None:
        data = {"id": "incomplete", "name": "Incomplete"}
        with open(tmp_path / "incomplete.yaml", "w", encoding="utf-8") as f:
            yaml.safe_dump(data, f)

        mgr = TemplateManager(tmp_path)
        with pytest.raises(TemplateError, match="필수 필드가 누락"):
            mgr.get("incomplete")


class TestCreate:
    def test_create_template(self, tmp_path: Path) -> None:
        mgr = TemplateManager(tmp_path)
        tpl = _make_template()
        result = mgr.create(tpl)

        assert (tmp_path / "lecture_note.yaml").exists()
        assert result.id == "lecture_note"

    def test_auto_sets_timestamps(self, tmp_path: Path) -> None:
        mgr = TemplateManager(tmp_path)
        tpl = _make_template(created_at="", updated_at="")
        result = mgr.create(tpl)

        assert result.created_at != ""
        assert result.updated_at != ""

    def test_preserves_existing_timestamps(self, tmp_path: Path) -> None:
        mgr = TemplateManager(tmp_path)
        tpl = _make_template(
            created_at="2025-01-01T00:00:00+00:00",
            updated_at="2025-01-01T00:00:00+00:00",
        )
        result = mgr.create(tpl)

        assert result.created_at == "2025-01-01T00:00:00+00:00"
        assert result.updated_at == "2025-01-01T00:00:00+00:00"

    def test_duplicate_raises(self, tmp_path: Path) -> None:
        _make_template_yaml(tmp_path, "existing")

        mgr = TemplateManager(tmp_path)
        tpl = _make_template(template_id="existing")
        with pytest.raises(FileExistsError, match="이미 존재합니다"):
            mgr.create(tpl)

    def test_creates_directory_if_needed(self, tmp_path: Path) -> None:
        templates_dir = tmp_path / "sub" / "templates"
        mgr = TemplateManager(templates_dir)
        tpl = _make_template()
        mgr.create(tpl)

        assert (templates_dir / "lecture_note.yaml").exists()

    def test_roundtrip(self, tmp_path: Path) -> None:
        mgr = TemplateManager(tmp_path)
        tpl = _make_template(
            created_at="2026-01-01T00:00:00+00:00",
            updated_at="2026-01-01T00:00:00+00:00",
        )
        mgr.create(tpl)

        loaded = mgr.get("lecture_note")
        assert loaded.id == tpl.id
        assert loaded.name == tpl.name
        assert loaded.system_prompt == tpl.system_prompt
        assert loaded.user_prompt_template == tpl.user_prompt_template


class TestUpdate:
    def test_update_template(self, tmp_path: Path) -> None:
        _make_template_yaml(tmp_path, "lecture_note")

        mgr = TemplateManager(tmp_path)
        tpl = _make_template(name="수정된 이름")
        result = mgr.update("lecture_note", tpl)

        assert result.name == "수정된 이름"

    def test_updates_updated_at(self, tmp_path: Path) -> None:
        _make_template_yaml(
            tmp_path, "lecture_note", updated_at="2025-01-01T00:00:00+00:00"
        )

        mgr = TemplateManager(tmp_path)
        tpl = _make_template()
        result = mgr.update("lecture_note", tpl)

        assert result.updated_at != "2025-01-01T00:00:00+00:00"

    def test_nonexistent_raises(self, tmp_path: Path) -> None:
        mgr = TemplateManager(tmp_path)
        tpl = _make_template()
        with pytest.raises(TemplateNotFoundError, match="찾을 수 없습니다"):
            mgr.update("nonexistent", tpl)

    def test_persists_changes(self, tmp_path: Path) -> None:
        _make_template_yaml(tmp_path, "lecture_note")

        mgr = TemplateManager(tmp_path)
        tpl = _make_template(description="새 설명")
        mgr.update("lecture_note", tpl)

        reloaded = mgr.get("lecture_note")
        assert reloaded.description == "새 설명"


class TestDelete:
    def test_delete_template(self, tmp_path: Path) -> None:
        _make_template_yaml(tmp_path, "lecture_note")

        mgr = TemplateManager(tmp_path)
        assert mgr.delete("lecture_note") is True
        assert not (tmp_path / "lecture_note.yaml").exists()

    def test_nonexistent_raises(self, tmp_path: Path) -> None:
        mgr = TemplateManager(tmp_path)
        with pytest.raises(TemplateNotFoundError, match="찾을 수 없습니다"):
            mgr.delete("nonexistent")


class TestRender:
    def test_basic_render(self, tmp_path: Path) -> None:
        _make_template_yaml(
            tmp_path,
            "test",
            system_prompt="You are a writer.",
            user_prompt_template="Write about:\n\n{content}",
        )

        mgr = TemplateManager(tmp_path)
        system, user = mgr.render("test", content="quantum physics")

        assert system == "You are a writer."
        assert "quantum physics" in user

    def test_render_with_kwargs(self, tmp_path: Path) -> None:
        _make_template_yaml(
            tmp_path,
            "test",
            user_prompt_template="{content}\n\nSources: {sources}\n\nStyle: {style_reference}",
        )

        mgr = TemplateManager(tmp_path)
        _, user = mgr.render(
            "test",
            content="my content",
            sources="source1, source2",
            style_reference="formal",
        )

        assert "my content" in user
        assert "source1, source2" in user
        assert "formal" in user

    def test_unused_placeholder_defaults_empty(self, tmp_path: Path) -> None:
        _make_template_yaml(
            tmp_path,
            "test",
            user_prompt_template="{content}\n\n{style_reference}\n\n{sources}",
        )

        mgr = TemplateManager(tmp_path)
        _, user = mgr.render("test", content="only content")

        assert "only content" in user
        assert "{style_reference}" not in user
        assert "{sources}" not in user

    def test_nonexistent_template_raises(self, tmp_path: Path) -> None:
        mgr = TemplateManager(tmp_path)
        with pytest.raises(TemplateNotFoundError):
            mgr.render("nonexistent", content="test")

    def test_extra_kwargs(self, tmp_path: Path) -> None:
        _make_template_yaml(
            tmp_path,
            "test",
            user_prompt_template="{content} - {custom_field}",
        )

        mgr = TemplateManager(tmp_path)
        _, user = mgr.render("test", content="hello", custom_field="world")

        assert user == "hello - world"
