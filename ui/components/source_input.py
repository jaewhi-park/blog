"""소스 입력 컴포넌트 — PDF, URL, arXiv 소스 추가/관리."""

from __future__ import annotations

import tempfile
from pathlib import Path

import streamlit as st

from core.sources.aggregator import SourceInput


def source_input(*, key_prefix: str = "source") -> list[SourceInput]:
    """소스 입력 UI를 렌더링하고 SourceInput 목록을 반환한다.

    Args:
        key_prefix: Streamlit 위젯 키 프리픽스 (중복 방지).

    Returns:
        사용자가 추가한 SourceInput 목록.
    """
    session_key = f"{key_prefix}_list"
    if session_key not in st.session_state:
        st.session_state[session_key] = []

    sources: list[dict] = st.session_state[session_key]

    # ── 추가 버튼 ────────────────────────────────────────────
    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("+ PDF", key=f"{key_prefix}_add_pdf"):
            st.session_state[f"{key_prefix}_adding"] = "pdf"
    with col2:
        if st.button("+ URL", key=f"{key_prefix}_add_url"):
            st.session_state[f"{key_prefix}_adding"] = "url"
    with col3:
        if st.button("+ arXiv", key=f"{key_prefix}_add_arxiv"):
            st.session_state[f"{key_prefix}_adding"] = "arxiv"

    # ── 입력 폼 ──────────────────────────────────────────────
    adding = st.session_state.get(f"{key_prefix}_adding")

    if adding == "pdf":
        _pdf_input_form(key_prefix, sources)
    elif adding == "url":
        _url_input_form(key_prefix, sources)
    elif adding == "arxiv":
        _arxiv_input_form(key_prefix, sources)

    # ── 소스 목록 표시 ───────────────────────────────────────
    if sources:
        st.markdown("**등록된 소스:**")
        to_delete: int | None = None
        for i, src in enumerate(sources):
            cols = st.columns([5, 1])
            with cols[0]:
                label = _format_source_display(src)
                st.text(label)
            with cols[1]:
                if st.button("삭제", key=f"{key_prefix}_del_{i}"):
                    to_delete = i

        if to_delete is not None:
            sources.pop(to_delete)
            st.rerun()

    # ── SourceInput 변환 ─────────────────────────────────────
    return [_dict_to_source_input(s) for s in sources]


def _pdf_input_form(key_prefix: str, sources: list[dict]) -> None:
    """PDF 업로드 + 페이지 범위 입력 폼."""
    uploaded = st.file_uploader(
        "PDF 파일 업로드",
        type=["pdf"],
        key=f"{key_prefix}_pdf_file",
    )
    col1, col2 = st.columns(2)
    with col1:
        page_start = st.number_input(
            "시작 페이지 (0=전체)",
            min_value=0,
            value=0,
            key=f"{key_prefix}_pdf_start",
        )
    with col2:
        page_end = st.number_input(
            "끝 페이지 (0=전체)",
            min_value=0,
            value=0,
            key=f"{key_prefix}_pdf_end",
        )
    label = st.text_input("라벨 (선택)", key=f"{key_prefix}_pdf_label")

    if st.button("추가", key=f"{key_prefix}_pdf_confirm"):
        if uploaded is None:
            st.error("PDF 파일을 업로드하세요.")
            return

        # 임시 파일로 저장
        suffix = Path(uploaded.name).suffix
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp.write(uploaded.read())
            tmp_path = tmp.name

        page_range = None
        if page_start > 0 and page_end > 0:
            if page_start > page_end:
                st.error("시작 페이지가 끝 페이지보다 클 수 없습니다.")
                return
            page_range = (page_start, page_end)

        sources.append(
            {
                "source_type": "pdf",
                "path_or_url": tmp_path,
                "page_range": page_range,
                "label": label or uploaded.name,
                "display_name": uploaded.name,
            }
        )
        st.session_state[f"{key_prefix}_adding"] = None
        st.rerun()


def _url_input_form(key_prefix: str, sources: list[dict]) -> None:
    """URL 입력 폼."""
    url = st.text_input(
        "URL",
        placeholder="https://example.com/article",
        key=f"{key_prefix}_url_input",
    )
    label = st.text_input("라벨 (선택)", key=f"{key_prefix}_url_label")

    if st.button("추가", key=f"{key_prefix}_url_confirm"):
        if not url.strip():
            st.error("URL을 입력하세요.")
            return
        if not url.startswith(("http://", "https://")):
            st.error("올바른 URL을 입력하세요 (http:// 또는 https://).")
            return

        sources.append(
            {
                "source_type": "url",
                "path_or_url": url.strip(),
                "page_range": None,
                "label": label or None,
                "display_name": url.strip(),
            }
        )
        st.session_state[f"{key_prefix}_adding"] = None
        st.rerun()


def _arxiv_input_form(key_prefix: str, sources: list[dict]) -> None:
    """arXiv ID/URL 입력 폼."""
    arxiv_input = st.text_input(
        "arXiv ID 또는 URL",
        placeholder="2301.07041 또는 https://arxiv.org/abs/2301.07041",
        key=f"{key_prefix}_arxiv_input",
    )
    label = st.text_input("라벨 (선택)", key=f"{key_prefix}_arxiv_label")

    if st.button("추가", key=f"{key_prefix}_arxiv_confirm"):
        if not arxiv_input.strip():
            st.error("arXiv ID 또는 URL을 입력하세요.")
            return

        arxiv_id = _extract_arxiv_id(arxiv_input.strip())

        sources.append(
            {
                "source_type": "arxiv",
                "path_or_url": arxiv_id,
                "page_range": None,
                "label": label or f"arXiv:{arxiv_id}",
                "display_name": f"arXiv:{arxiv_id}",
            }
        )
        st.session_state[f"{key_prefix}_adding"] = None
        st.rerun()


def _extract_arxiv_id(input_str: str) -> str:
    """arXiv URL 또는 ID에서 순수 ID를 추출한다."""
    # URL 패턴 처리
    for prefix in (
        "https://arxiv.org/abs/",
        "http://arxiv.org/abs/",
        "https://arxiv.org/pdf/",
        "http://arxiv.org/pdf/",
    ):
        if input_str.startswith(prefix):
            return input_str[len(prefix) :].rstrip("/")
    return input_str


def _format_source_display(src: dict) -> str:
    """소스 정보를 표시용 문자열로 포맷한다."""
    icon_map = {"pdf": "PDF", "url": "URL", "arxiv": "arXiv"}
    icon = icon_map.get(src["source_type"], src["source_type"])
    display = src.get("display_name", src["path_or_url"])

    parts = [f"[{icon}] {display}"]
    if src.get("page_range"):
        start, end = src["page_range"]
        parts.append(f"(pages {start}-{end})")
    if src.get("label") and src["label"] != display:
        parts.append(f"— {src['label']}")

    return " ".join(parts)


def _dict_to_source_input(src: dict) -> SourceInput:
    """dict를 SourceInput dataclass로 변환한다."""
    page_range = src.get("page_range")
    if page_range is not None:
        page_range = tuple(page_range)
    return SourceInput(
        source_type=src["source_type"],
        path_or_url=src["path_or_url"],
        page_range=page_range,
        label=src.get("label"),
    )
