"""프로바이더/모델 선택 컴포넌트."""

from __future__ import annotations

import logging

import streamlit as st

from core.config import Config

logger = logging.getLogger(__name__)

# 프로바이더 표시명 ↔ 내부 키 매핑
_PROVIDER_MAP: dict[str, str] = {
    "Claude": "claude",
    "OpenAI": "openai",
    "Llama": "llama",
}

# config 로드 실패 시 fallback
_FALLBACK_MODELS: dict[str, list[str]] = {
    "Claude": ["claude-sonnet-4-20250514", "claude-haiku-4-5-20251001"],
    "OpenAI": ["gpt-4o", "gpt-4o-mini"],
    "Llama": ["llama3.1"],
}


def _load_models_from_config() -> dict[str, list[str]]:
    """config/llm_config.yaml에서 프로바이더별 모델 목록을 로드한다."""
    try:
        cfg = Config()
        result: dict[str, list[str]] = {}
        for display_name, provider_key in _PROVIDER_MAP.items():
            provider_cfg = cfg.llm.get("providers", {}).get(provider_key, {})
            models = provider_cfg.get("models", [])
            if models:
                result[display_name] = [m["id"] for m in models]
        if result:
            return result
    except Exception:
        logger.debug("llm_config.yaml 로드 실패, fallback 사용")
    return _FALLBACK_MODELS


def llm_selector(*, key_prefix: str = "llm") -> tuple[str, str]:
    """프로바이더와 모델 선택 UI를 렌더링한다.

    Args:
        key_prefix: Streamlit 위젯 키 프리픽스 (중복 방지).

    Returns:
        (provider, model) 튜플. provider는 "claude", "openai", "llama".
    """
    provider_models = _load_models_from_config()

    col1, col2 = st.columns(2)
    with col1:
        provider_display = st.selectbox(
            "프로바이더",
            list(provider_models.keys()),
            key=f"{key_prefix}_provider",
        )
    with col2:
        models = provider_models.get(provider_display, [])
        model = st.selectbox(
            "모델",
            models,
            key=f"{key_prefix}_model",
        )

    provider = _PROVIDER_MAP.get(provider_display, "claude")
    return provider, model
