"""템플릿 관리 페이지."""

from __future__ import annotations

import re
import sys
import unicodedata
from pathlib import Path

_PROJECT_ROOT = str(Path(__file__).resolve().parent.parent.parent)
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

import streamlit as st  # noqa: E402

from core.content.template_manager import PromptTemplate, TemplateManager  # noqa: E402
from core.exceptions import TemplateError, TemplateNotFoundError  # noqa: E402

st.set_page_config(page_title="템플릿 | whi-blog", layout="wide")

TEMPLATES_DIR = Path("templates")
tpl_mgr = TemplateManager(TEMPLATES_DIR)


def _slugify(text: str) -> str:
    """표시명을 id용 slug로 변환."""
    text = unicodedata.normalize("NFC", text)
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_]+", "-", text)
    text = re.sub(r"-+", "-", text)
    return text.strip("-")


# ── 메인 ────────────────────────────────────────────────────
st.title("템플릿 관리")

templates = tpl_mgr.list_all()

# ── 목록 ────────────────────────────────────────────────────
if not templates:
    st.info("등록된 템플릿이 없습니다. 아래에서 추가하세요.")
else:
    st.markdown("### 템플릿 목록")
    for tpl in templates:
        with st.expander(f"**{tpl.name}** (`{tpl.id}`) — {tpl.description}"):
            st.markdown("**System Prompt**")
            st.code(tpl.system_prompt, language=None)
            st.markdown("**User Prompt Template**")
            st.code(tpl.user_prompt_template, language=None)
            st.caption(f"생성: {tpl.created_at} | 수정: {tpl.updated_at}")

st.divider()

# ── 생성 ────────────────────────────────────────────────────
st.markdown("### 템플릿 생성")

with st.form("create_template", clear_on_submit=True):
    col1, col2 = st.columns(2)
    with col1:
        new_name = st.text_input("이름", placeholder="예: 렉쳐노트")
    with col2:
        new_desc = st.text_input("설명", placeholder="예: 수학 렉쳐노트 스타일로 작성")

    new_system = st.text_area(
        "System Prompt",
        height=150,
        placeholder="LLM에게 부여할 역할/지시 (예: You are a mathematics educator...)",
    )
    new_user = st.text_area(
        "User Prompt Template",
        height=150,
        placeholder="플레이스홀더: {content}, {sources}, {style_reference}",
    )

    submitted = st.form_submit_button("생성", type="primary")

    if submitted:
        name_stripped = new_name.strip()
        if not name_stripped:
            st.error("이름을 입력해주세요.")
        elif not new_system.strip():
            st.error("System Prompt를 입력해주세요.")
        elif not new_user.strip():
            st.error("User Prompt Template을 입력해주세요.")
        else:
            tpl_id = _slugify(name_stripped)
            tpl = PromptTemplate(
                id=tpl_id,
                name=name_stripped,
                description=new_desc.strip(),
                system_prompt=new_system,
                user_prompt_template=new_user,
                created_at="",
                updated_at="",
            )
            try:
                tpl_mgr.create(tpl)
                st.success(f"템플릿 생성됨: **{name_stripped}** (`{tpl_id}`)")
                st.rerun()
            except FileExistsError:
                st.error(f"동일한 ID의 템플릿이 이미 존재합니다: `{tpl_id}`")
            except TemplateError as e:
                st.error(f"생성 실패: {e}")

st.divider()

# ── 편집 ────────────────────────────────────────────────────
st.markdown("### 템플릿 편집")

if templates:
    edit_options = [f"{t.name} ({t.id})" for t in templates]
    edit_idx = st.selectbox(
        "편집할 템플릿",
        range(len(edit_options)),
        format_func=lambda i: edit_options[i],
        key="edit_select",
    )
    target = templates[edit_idx]

    with st.form("edit_template"):
        col1, col2 = st.columns(2)
        with col1:
            edit_name = st.text_input("이름", value=target.name, key="edit_name")
        with col2:
            edit_desc = st.text_input("설명", value=target.description, key="edit_desc")

        edit_system = st.text_area(
            "System Prompt",
            value=target.system_prompt,
            height=150,
            key="edit_system",
        )
        edit_user = st.text_area(
            "User Prompt Template",
            value=target.user_prompt_template,
            height=150,
            key="edit_user",
        )

        if st.form_submit_button("저장", type="primary"):
            updated = PromptTemplate(
                id=target.id,
                name=edit_name.strip() or target.name,
                description=edit_desc.strip(),
                system_prompt=edit_system,
                user_prompt_template=edit_user,
                created_at=target.created_at,
                updated_at="",
            )
            try:
                tpl_mgr.update(target.id, updated)
                st.success(f"템플릿 수정됨: **{updated.name}** (`{target.id}`)")
                st.rerun()
            except TemplateNotFoundError:
                st.error("템플릿을 찾을 수 없습니다.")
            except TemplateError as e:
                st.error(f"수정 실패: {e}")
else:
    st.info("편집할 템플릿이 없습니다.")

st.divider()

# ── 삭제 ────────────────────────────────────────────────────
st.markdown("### 템플릿 삭제")

if templates:
    del_options = [f"{t.name} ({t.id})" for t in templates]
    del_idx = st.selectbox(
        "삭제할 템플릿",
        range(len(del_options)),
        format_func=lambda i: del_options[i],
        key="del_select",
    )

    if st.button("삭제", type="secondary"):
        target_del = templates[del_idx]
        try:
            tpl_mgr.delete(target_del.id)
            st.success(f"템플릿 삭제됨: **{target_del.name}** (`{target_del.id}`)")
            st.rerun()
        except TemplateNotFoundError:
            st.error("템플릿을 찾을 수 없습니다.")
else:
    st.info("삭제할 템플릿이 없습니다.")
