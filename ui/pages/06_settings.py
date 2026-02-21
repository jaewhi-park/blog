"""설정 페이지 — arxiv 관심사, 면책 조항."""

from __future__ import annotations

import sys
from pathlib import Path

_PROJECT_ROOT = str(Path(__file__).resolve().parent.parent.parent)
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

import yaml  # noqa: E402
import streamlit as st  # noqa: E402

st.set_page_config(page_title="설정 | whi-blog")

CONFIG_DIR = Path("config")
HUGO_DATA_DIR = Path("hugo-site/data")


# ── YAML 로드/저장 헬퍼 ──────────────────────────────────────
def _load_yaml(path: Path) -> dict:
    if not path.exists():
        return {}
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def _save_yaml(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        yaml.dump(
            data, f, allow_unicode=True, default_flow_style=False, sort_keys=False
        )


# ── 메인 ────────────────────────────────────────────────────
st.title("설정")

tab_arxiv, tab_disclaimer, tab_llm = st.tabs(["arxiv 관심사", "면책 조항", "LLM 설정"])

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Tab 1: arxiv 관심사
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
with tab_arxiv:
    arxiv_path = CONFIG_DIR / "arxiv_digest.yaml"
    arxiv_cfg = _load_yaml(arxiv_path)

    st.markdown("### 관심 카테고리")
    st.caption("arxiv 카테고리 코드 (예: math.PR, cs.LG, stat.ML)")

    # 현재 카테고리 표시 + 삭제
    current_cats: list[str] = arxiv_cfg.get("categories", [])
    if current_cats:
        cols = st.columns(min(len(current_cats), 6))
        remove_cat = None
        for i, cat in enumerate(current_cats):
            with cols[i % len(cols)]:
                if st.button(f"{cat}  x", key=f"rm_cat_{i}"):
                    remove_cat = cat
        if remove_cat:
            current_cats.remove(remove_cat)
            arxiv_cfg["categories"] = current_cats
            _save_yaml(arxiv_path, arxiv_cfg)
            st.rerun()
    else:
        st.info("등록된 카테고리가 없습니다.")

    # 카테고리 추가
    col_cat_add, col_cat_btn = st.columns([3, 1])
    with col_cat_add:
        new_cat = st.text_input(
            "카테고리 추가", placeholder="math.PR", label_visibility="collapsed"
        )
    with col_cat_btn:
        if st.button("추가", key="add_cat", disabled=not new_cat.strip()):
            cat_val = new_cat.strip()
            if cat_val not in current_cats:
                current_cats.append(cat_val)
                arxiv_cfg["categories"] = current_cats
                _save_yaml(arxiv_path, arxiv_cfg)
                st.rerun()
            else:
                st.warning("이미 등록된 카테고리입니다.")

    st.divider()

    st.markdown("### 관심 키워드")

    # 현재 키워드 표시 + 삭제
    current_kw: list[str] = arxiv_cfg.get("keywords", [])
    if current_kw:
        cols_kw = st.columns(min(len(current_kw), 6))
        remove_kw = None
        for i, kw in enumerate(current_kw):
            with cols_kw[i % len(cols_kw)]:
                if st.button(f"{kw}  x", key=f"rm_kw_{i}"):
                    remove_kw = kw
        if remove_kw:
            current_kw.remove(remove_kw)
            arxiv_cfg["keywords"] = current_kw
            _save_yaml(arxiv_path, arxiv_cfg)
            st.rerun()
    else:
        st.info("등록된 키워드가 없습니다.")

    # 키워드 추가
    col_kw_add, col_kw_btn = st.columns([3, 1])
    with col_kw_add:
        new_kw = st.text_input(
            "키워드 추가", placeholder="random matrix", label_visibility="collapsed"
        )
    with col_kw_btn:
        if st.button("추가", key="add_kw", disabled=not new_kw.strip()):
            kw_val = new_kw.strip()
            if kw_val not in current_kw:
                current_kw.append(kw_val)
                arxiv_cfg["keywords"] = current_kw
                _save_yaml(arxiv_path, arxiv_cfg)
                st.rerun()
            else:
                st.warning("이미 등록된 키워드입니다.")

    st.divider()

    st.markdown("### 관심사 설명")
    st.caption("LLM이 논문 필터링 시 참고하는 자연어 설명입니다.")

    interest_desc = st.text_area(
        "관심사 설명",
        value=arxiv_cfg.get("interest_description", ""),
        height=150,
        label_visibility="collapsed",
    )

    col_desc1, col_desc2 = st.columns([1, 3])
    with col_desc1:
        if st.button("저장", key="save_interest", type="primary"):
            arxiv_cfg["interest_description"] = interest_desc
            _save_yaml(arxiv_path, arxiv_cfg)
            st.success("관심사 설명이 저장되었습니다.")

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Tab 2: 면책 조항
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
with tab_disclaimer:
    disclaimer_config_path = CONFIG_DIR / "disclaimer.yaml"
    hugo_disclaimer_path = HUGO_DATA_DIR / "disclaimer.yaml"
    disc_cfg = _load_yaml(disclaimer_config_path)

    st.markdown("### LLM 생성 면책 조항")

    gen_cfg = disc_cfg.get("llm_generated", {})
    gen_text = st.text_area(
        "문구",
        value=gen_cfg.get("text", ""),
        height=80,
        key="gen_text",
    )
    gen_style = st.selectbox(
        "스타일",
        ["warning", "info", "note"],
        index=["warning", "info", "note"].index(gen_cfg.get("style", "warning")),
        key="gen_style",
    )

    st.divider()

    st.markdown("### LLM 보조 면책 조항")

    asst_cfg = disc_cfg.get("llm_assisted", {})
    asst_text = st.text_area(
        "문구",
        value=asst_cfg.get("text", ""),
        height=80,
        key="asst_text",
    )
    asst_style = st.selectbox(
        "스타일",
        ["warning", "info", "note"],
        index=["warning", "info", "note"].index(asst_cfg.get("style", "info")),
        key="asst_style",
    )

    st.divider()

    if st.button("면책 조항 저장", type="primary"):
        new_disc = {
            "llm_generated": {"text": gen_text, "style": gen_style},
            "llm_assisted": {"text": asst_text, "style": asst_style},
        }
        _save_yaml(disclaimer_config_path, new_disc)
        # Hugo data에도 동기화
        _save_yaml(hugo_disclaimer_path, new_disc)
        st.success("면책 조항 설정이 저장되었습니다.")

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Tab 3: LLM 설정 (M3에서 활성화)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
with tab_llm:
    st.info("M3에서 LLM 연동 후 활성화됩니다.")

    st.selectbox("기본 프로바이더", ["Claude", "OpenAI", "Llama"], disabled=True)
    st.selectbox("기본 모델", ["Sonnet", "Haiku", "Opus"], disabled=True)

    st.divider()
    st.markdown("#### Map-Reduce 모델 설정")
    st.selectbox("Map 모델 (경량)", ["Haiku", "GPT-4o-mini"], disabled=True)
    st.selectbox("Reduce 모델 (고성능)", ["Sonnet", "GPT-4o"], disabled=True)
