"""스타일 레퍼런스 관리 페이지."""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

_PROJECT_ROOT = str(Path(__file__).resolve().parent.parent.parent)
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

import streamlit as st  # noqa: E402

from core.content.reference_manager import ReferenceManager  # noqa: E402
from core.exceptions import ReferenceError, ReferenceNotFoundError  # noqa: E402

st.set_page_config(page_title="레퍼런스 | whi-blog", layout="wide")

REFERENCES_DIR = Path("references")
ref_mgr = ReferenceManager(REFERENCES_DIR)

# ── 메인 ────────────────────────────────────────────────────
st.title("스타일 레퍼런스 관리")

refs = ref_mgr.list_all()

# ── 목록 ────────────────────────────────────────────────────
if not refs:
    st.info("등록된 레퍼런스가 없습니다. 아래에서 추가하세요.")
else:
    st.markdown("### 레퍼런스 목록")
    for ref in refs:
        type_badge = "파일" if ref.source_type == "file" else "URL"
        source_display = ref.source_path
        if ref.file_type:
            source_display += f" (.{ref.file_type})"

        with st.expander(
            f"**{ref.name}** (`{ref.id}`) — [{type_badge}] {source_display}"
        ):
            st.caption(f"생성: {ref.created_at} | 수정: {ref.updated_at}")

            # 내용 미리보기
            try:
                content = ref_mgr.get_content(ref.id)
                preview = content[:2000]
                if len(content) > 2000:
                    preview += f"\n\n... ({len(content):,}자 중 2,000자 표시)"
                st.code(preview, language=None)
            except ReferenceError as e:
                st.warning(f"내용을 불러올 수 없습니다: {e}")

st.divider()

# ── 파일 레퍼런스 추가 ──────────────────────────────────────
st.markdown("### 파일 레퍼런스 추가")
st.caption("PDF, Markdown(.md), 텍스트(.txt) 파일을 업로드합니다.")

col1, col2 = st.columns([1, 2])
with col1:
    file_ref_name = st.text_input(
        "이름", placeholder="예: Terence Tao 블로그 스타일", key="file_name"
    )
with col2:
    uploaded = st.file_uploader(
        "파일 업로드",
        type=["pdf", "md", "txt"],
        key="file_upload",
    )

if st.button(
    "파일 레퍼런스 추가",
    type="primary",
    disabled=not (file_ref_name.strip() and uploaded),
):
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir) / uploaded.name
        tmp_path.write_bytes(uploaded.getvalue())
        try:
            ref = ref_mgr.add_file(file_ref_name.strip(), tmp_path)
            st.success(f"파일 레퍼런스 추가됨: **{ref.name}** (`{ref.id}`)")
            st.rerun()
        except FileExistsError:
            st.error("동일한 이름의 레퍼런스가 이미 존재합니다.")
        except ReferenceError as e:
            st.error(f"추가 실패: {e}")

st.divider()

# ── URL 레퍼런스 추가 ───────────────────────────────────────
st.markdown("### URL 레퍼런스 추가")
st.caption("웹 페이지를 크롤링하여 텍스트를 캐시에 저장합니다.")

col1, col2 = st.columns([1, 2])
with col1:
    url_ref_name = st.text_input(
        "이름", placeholder="예: Paul Graham 에세이 스타일", key="url_name"
    )
with col2:
    url_input = st.text_input(
        "URL", placeholder="https://example.com/article", key="url_input"
    )

if st.button(
    "URL 레퍼런스 추가",
    type="primary",
    disabled=not (url_ref_name.strip() and url_input.strip()),
):
    with st.spinner("URL 크롤링 중..."):
        try:
            ref = ref_mgr.add_url(url_ref_name.strip(), url_input.strip())
            st.success(f"URL 레퍼런스 추가됨: **{ref.name}** (`{ref.id}`)")
            st.rerun()
        except FileExistsError:
            st.error("동일한 이름의 레퍼런스가 이미 존재합니다.")
        except ReferenceError as e:
            st.error(f"크롤링 실패: {e}")

st.divider()

# ── 삭제 ────────────────────────────────────────────────────
st.markdown("### 레퍼런스 삭제")

if refs:
    del_options = [f"{r.name} ({r.id}) [{r.source_type}]" for r in refs]
    del_idx = st.selectbox(
        "삭제할 레퍼런스",
        range(len(del_options)),
        format_func=lambda i: del_options[i],
        key="del_select",
    )

    if st.button("삭제", type="secondary"):
        target = refs[del_idx]
        try:
            ref_mgr.remove(target.id)
            st.success(f"레퍼런스 삭제됨: **{target.name}** (`{target.id}`)")
            st.rerun()
        except ReferenceNotFoundError:
            st.error("레퍼런스를 찾을 수 없습니다.")
else:
    st.info("삭제할 레퍼런스가 없습니다.")
