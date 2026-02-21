"""whi-blog Streamlit CMS — 메인 앱."""

import sys
from pathlib import Path

# 프로젝트 루트를 sys.path에 추가 (core 패키지 import 지원)
_PROJECT_ROOT = str(Path(__file__).resolve().parent.parent)
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

import streamlit as st  # noqa: E402

st.set_page_config(
    page_title="whi-blog CMS",
    page_icon="📝",
    layout="wide",
    initial_sidebar_state="expanded",
)

# 공통 CSS
st.markdown(
    """
    <style>
    /* 사이드바 네비게이션 스타일 */
    [data-testid="stSidebar"] {
        min-width: 240px;
        max-width: 320px;
    }
    /* 메인 컨텐츠 상단 패딩 축소 */
    .block-container {
        padding-top: 2rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("whi-blog CMS")
st.markdown(
    "Hugo 기반 기술 블로그 관리 도구입니다. 왼쪽 사이드바에서 원하는 기능을 선택하세요."
)

st.divider()

col1, col2, col3 = st.columns(3)

with col1:
    st.markdown("### ✏️ 글 작성")
    st.markdown("직접 작성, 페어 라이팅, 자동 생성 모드를 지원합니다.")

with col2:
    st.markdown("### 📂 카테고리")
    st.markdown("Hugo 계층형 카테고리를 관리합니다.")

with col3:
    st.markdown("### ⚙️ 설정")
    st.markdown("LLM, arxiv 관심사, 면책 조항 등을 설정합니다.")
