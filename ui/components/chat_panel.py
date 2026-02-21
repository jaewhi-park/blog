"""재사용 가능한 LLM 대화 패널 컴포넌트."""

from __future__ import annotations

import streamlit as st


def chat_panel(
    messages: list[dict[str, str]],
    key_prefix: str,
    input_placeholder: str = "메시지를 입력하세요...",
    height: int = 400,
) -> str | None:
    """대화 이력을 표시하고 새 메시지 입력을 받는다.

    Args:
        messages: 대화 이력. 각 dict는 role, content 키를 가지며,
            선택적으로 usage (dict[str, int]) 키를 가질 수 있다.
        key_prefix: Streamlit 위젯 key 프리픽스 (충돌 방지).
        input_placeholder: 입력 필드 placeholder 텍스트.
        height: 대화 이력 컨테이너 높이(px).

    Returns:
        새 메시지 텍스트. 입력이 없으면 None.
    """
    # 대화 이력 표시
    with st.container(height=height):
        if not messages:
            st.caption("대화 이력이 없습니다.")
        for idx, msg in enumerate(messages):
            role = msg["role"]
            with st.chat_message(role):
                st.markdown(msg["content"])
                if role == "assistant":
                    footer_cols = st.columns([1, 1, 10])
                    with footer_cols[0]:
                        with st.popover("📋", help="복사"):
                            st.code(
                                msg["content"],
                                language=None,
                                wrap_lines=True,
                            )
                    if "usage" in msg:
                        usage = msg["usage"]
                        with footer_cols[1]:
                            st.caption(
                                f"{usage.get('input_tokens', 0)}↑ "
                                f"{usage.get('output_tokens', 0)}↓"
                            )

    # 메시지 입력
    new_message = st.text_area(
        "메시지 입력",
        key=f"{key_prefix}_chat_input",
        placeholder=input_placeholder,
        height=100,
        label_visibility="collapsed",
    )
    if st.button(
        "전송",
        key=f"{key_prefix}_chat_send",
        disabled=not (new_message and new_message.strip()),
    ):
        return new_message.strip()
    return None
