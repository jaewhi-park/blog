"""글 작성 페이지 — 직접 작성 / 페어 라이팅 / 자동 생성."""

import streamlit as st

st.set_page_config(page_title="글 작성 | whi-blog", layout="wide")

st.title("✏️ 글 작성")

mode = st.radio(
    "작성 모드",
    ["직접 작성", "페어 라이팅", "자동 생성"],
    horizontal=True,
)

st.divider()

# 공통: 메타데이터 입력
col_meta1, col_meta2 = st.columns(2)
with col_meta1:
    title = st.text_input("제목")
with col_meta2:
    tags = st.text_input("태그 (쉼표 구분)", placeholder="random-matrix, probability")

# 카테고리 선택 (M2.3에서 CategoryManager 연동 예정)
category = st.selectbox(
    "카테고리",
    [
        "math/probability",
        "math/algebra",
        "investment/macro-analysis",
        "ai/ml-engineering",
    ],
    help="카테고리 매니저 연동 후 동적으로 로드됩니다.",
)

st.divider()

if mode == "직접 작성":
    st.markdown("#### 마크다운 에디터")
    content = st.text_area(
        "본문",
        height=400,
        placeholder="마크다운으로 작성하세요...",
        label_visibility="collapsed",
    )

    col_action1, col_action2, col_action3 = st.columns([1, 1, 2])
    with col_action1:
        st.button("임시저장", disabled=True)
    with col_action2:
        st.button("미리보기 (Hugo)", disabled=True)
    with col_action3:
        st.button("게시하기", type="primary", disabled=True)

elif mode == "페어 라이팅":
    st.markdown("#### 마크다운 에디터 + LLM 피드백")
    st.info("M3에서 LLM 연동 후 활성화됩니다.")

    content = st.text_area(
        "초안",
        height=300,
        placeholder="초안을 작성하면 LLM이 피드백을 제공합니다...",
        label_visibility="collapsed",
    )

    col_llm1, col_llm2 = st.columns(2)
    with col_llm1:
        st.selectbox("프로바이더", ["Claude", "OpenAI", "Llama"], disabled=True)
    with col_llm2:
        st.selectbox("모델", ["Sonnet", "Haiku"], disabled=True)

    st.button("LLM 피드백 요청", disabled=True)

elif mode == "자동 생성":
    st.markdown("#### 소스 기반 자동 생성")
    st.info("M4에서 소스 연동 후 활성화됩니다.")

    prompt = st.text_area(
        "주제 / 지시사항",
        height=150,
        placeholder="생성할 글의 주제나 지시사항을 입력하세요...",
        label_visibility="collapsed",
    )

    col_llm1, col_llm2 = st.columns(2)
    with col_llm1:
        st.selectbox(
            "프로바이더",
            ["Claude", "OpenAI", "Llama"],
            key="auto_provider",
            disabled=True,
        )
    with col_llm2:
        st.selectbox("모델", ["Sonnet", "Haiku"], key="auto_model", disabled=True)

    st.button("생성 요청", type="primary", disabled=True)
