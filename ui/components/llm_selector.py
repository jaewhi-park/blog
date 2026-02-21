"""프로바이더/모델 선택 컴포넌트."""

from __future__ import annotations

import streamlit as st

# 프로바이더별 모델 목록 (config 로드 실패 시 fallback)
_DEFAULT_MODELS: dict[str, list[str]] = {
    "Claude": ["claude-sonnet-4-20250514", "claude-haiku-4-5-20251001"],
    "OpenAI": ["gpt-4o", "gpt-4o-mini"],
    "Llama": ["llama3.1"],
}

_PROVIDER_MAP: dict[str, str] = {
    "Claude": "claude",
    "OpenAI": "openai",
    "Llama": "llama",
}


def llm_selector(*, key_prefix: str = "llm") -> tuple[str, str]:
    """프로바이더와 모델 선택 UI를 렌더링한다.

    Args:
        key_prefix: Streamlit 위젯 키 프리픽스 (중복 방지).

    Returns:
        (provider, model) 튜플. provider는 "claude", "openai", "llama".
    """
    col1, col2 = st.columns(2)
    with col1:
        provider_display = st.selectbox(
            "프로바이더",
            list(_DEFAULT_MODELS.keys()),
            key=f"{key_prefix}_provider",
        )
    with col2:
        models = _DEFAULT_MODELS.get(provider_display, [])
        model = st.selectbox(
            "모델",
            models,
            key=f"{key_prefix}_model",
        )

    provider = _PROVIDER_MAP.get(provider_display, "claude")
    return provider, model
