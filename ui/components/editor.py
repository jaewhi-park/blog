"""마크다운 에디터 컴포넌트."""

from __future__ import annotations

import streamlit as st


def markdown_editor(
    *,
    key: str = "editor",
    height: int = 400,
    placeholder: str = "마크다운으로 작성하세요...",
    initial_value: str = "",
) -> str:
    """마크다운 에디터를 렌더링하고 입력된 텍스트를 반환한다.

    Args:
        key: Streamlit 위젯 키.
        height: 에디터 높이 (px).
        placeholder: 빈 상태 안내 문구.
        initial_value: 초기 텍스트.

    Returns:
        입력된 마크다운 텍스트.
    """
    content: str = st.text_area(
        "본문",
        value=initial_value,
        height=height,
        placeholder=placeholder,
        label_visibility="collapsed",
        key=key,
    )
    return content


def image_upload_insert(*, post_slug: str, key: str = "img_upload") -> str | None:
    """이미지 업로드 위젯을 렌더링하고 마크다운 참조 문자열을 반환한다.

    Args:
        post_slug: 게시글 슬러그 (이미지 저장 경로에 사용).
        key: Streamlit 위젯 키.

    Returns:
        삽입할 마크다운 이미지 참조 문자열. 업로드가 없으면 None.
    """
    uploaded = st.file_uploader(
        "이미지 업로드",
        type=["png", "jpg", "jpeg", "gif", "svg", "webp"],
        key=key,
        help="업로드된 이미지는 본문에 마크다운 참조로 삽입됩니다.",
    )

    if uploaded is None:
        return None

    # session_state에 업로드 이력 저장
    if "uploaded_images" not in st.session_state:
        st.session_state.uploaded_images = []

    from pathlib import Path

    from core.content.image_manager import ImageManager, get_base_path

    hugo_dir = Path("hugo-site")
    base_path = get_base_path(hugo_dir)
    mgr = ImageManager(hugo_dir / "static", base_path=base_path)

    image_data = uploaded.getvalue()
    info = mgr.save_image(image_data, post_slug, uploaded.name)
    md_ref = mgr.generate_markdown_ref(post_slug, info)

    st.session_state.uploaded_images.append(
        {"filename": uploaded.name, "markdown": md_ref}
    )

    st.success(f"이미지 저장됨: `{uploaded.name}`")
    st.code(md_ref, language="markdown")

    return md_ref
