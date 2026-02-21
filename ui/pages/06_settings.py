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
# Tab 3: LLM 설정
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
with tab_llm:
    llm_config_path = CONFIG_DIR / "llm_config.yaml"
    llm_cfg = _load_yaml(llm_config_path)
    providers_cfg = llm_cfg.get("providers", {})
    chunking_cfg = llm_cfg.get("chunking", {})

    # 프로바이더/모델 목록 구성
    _PROVIDER_DISPLAY = {"claude": "Claude", "openai": "OpenAI", "llama": "Llama"}
    provider_keys = list(providers_cfg.keys())
    provider_labels = [_PROVIDER_DISPLAY.get(k, k) for k in provider_keys]

    all_models: list[str] = []
    for pcfg in providers_cfg.values():
        for m in pcfg.get("models", []):
            all_models.append(m["id"])

    # ── 기본 프로바이더/모델 ──────────────────────────────────
    st.markdown("### 기본 프로바이더 / 모델")

    if not provider_keys:
        st.warning("llm_config.yaml에 프로바이더가 설정되어 있지 않습니다.")
    else:
        col_prov, col_model = st.columns(2)
        with col_prov:
            default_provider_idx = 0
            selected_provider_label = st.selectbox(
                "기본 프로바이더",
                provider_labels,
                index=default_provider_idx,
                key="llm_default_provider",
            )
            selected_provider_key = provider_keys[
                provider_labels.index(selected_provider_label)
            ]

        with col_model:
            prov_cfg = providers_cfg.get(selected_provider_key, {})
            prov_models = [m["id"] for m in prov_cfg.get("models", [])]
            current_default = prov_cfg.get("default_model", "")
            default_model_idx = (
                prov_models.index(current_default)
                if current_default in prov_models
                else 0
            )
            selected_model = st.selectbox(
                "기본 모델",
                prov_models,
                index=default_model_idx,
                key="llm_default_model",
            )

    st.divider()

    # ── Map-Reduce 모델 설정 ─────────────────────────────────
    st.markdown("### Map-Reduce 모델 설정")

    col_map, col_reduce = st.columns(2)
    with col_map:
        current_map = chunking_cfg.get("map_model", "")
        map_idx = all_models.index(current_map) if current_map in all_models else 0
        map_model = st.selectbox(
            "Map 모델 (경량)",
            all_models,
            index=map_idx,
            key="llm_map_model",
        )
    with col_reduce:
        current_reduce = chunking_cfg.get("reduce_model", "")
        reduce_idx = (
            all_models.index(current_reduce) if current_reduce in all_models else 0
        )
        reduce_model = st.selectbox(
            "Reduce 모델 (고성능)",
            all_models,
            index=reduce_idx,
            key="llm_reduce_model",
        )

    st.divider()

    # ── 청킹 파라미터 ────────────────────────────────────────
    st.markdown("### 청킹 파라미터")

    col_chunk, col_thresh = st.columns(2)
    with col_chunk:
        chunk_size = st.number_input(
            "청크 크기 (토큰)",
            min_value=500,
            max_value=32000,
            value=chunking_cfg.get("chunk_size_tokens", 4000),
            step=500,
            key="llm_chunk_size",
        )
    with col_thresh:
        threshold = st.slider(
            "컨텍스트 임계치",
            min_value=0.3,
            max_value=0.95,
            value=chunking_cfg.get("context_threshold", 0.7),
            step=0.05,
            key="llm_threshold",
            help="컨텍스트 윈도우의 이 비율을 초과하면 Map-Reduce를 사용합니다.",
        )

    st.divider()

    # ── 저장 ─────────────────────────────────────────────────
    if st.button("LLM 설정 저장", type="primary"):
        if provider_keys:
            providers_cfg[selected_provider_key]["default_model"] = selected_model

        llm_cfg["providers"] = providers_cfg
        llm_cfg["chunking"] = {
            "chunk_size_tokens": chunk_size,
            "context_threshold": threshold,
            "map_model": map_model,
            "reduce_model": reduce_model,
        }
        _save_yaml(llm_config_path, llm_cfg)
        st.success("LLM 설정이 저장되었습니다.")
