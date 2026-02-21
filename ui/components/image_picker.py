"""이미지 선택 컴포넌트 — PDF 추출 이미지 썸네일 표시 및 선택."""

from __future__ import annotations

from pathlib import Path

import streamlit as st

from core.content.image_manager import ImageInfo, ImageManager, get_base_path


@st.cache_resource
def _get_image_manager() -> ImageManager:
    hugo_dir = Path("hugo-site")
    return ImageManager(hugo_dir / "static", base_path=get_base_path(hugo_dir))


def image_picker(
    images: list[ImageInfo],
    image_data: dict[str, bytes],
    *,
    post_slug: str,
    key_prefix: str = "img_picker",
) -> list[ImageInfo]:
    """PDF에서 추출된 이미지를 썸네일로 표시하고 선택할 수 있게 한다.

    선택된 이미지는 Hugo static 디렉토리에 저장되고,
    마크다운 참조 문자열이 표시된다.

    Args:
        images: PDF에서 추출된 ImageInfo 목록.
        image_data: filename → PNG bytes 매핑.
        post_slug: 게시글 슬러그 (이미지 저장 경로에 사용).
        key_prefix: Streamlit 위젯 키 프리픽스.

    Returns:
        사용자가 선택하고 저장된 ImageInfo 목록.
    """
    if not images:
        st.caption("추출된 이미지가 없습니다.")
        return []

    st.markdown(f"**추출된 이미지 ({len(images)}개)**")

    selected: list[ImageInfo] = []
    mgr = _get_image_manager()

    # 3열 그리드로 썸네일 표시
    cols_per_row = 3
    for row_start in range(0, len(images), cols_per_row):
        row_images = images[row_start : row_start + cols_per_row]
        cols = st.columns(cols_per_row)

        for col_idx, img in enumerate(row_images):
            img_idx = row_start + col_idx
            img_bytes = image_data.get(img.filename)

            with cols[col_idx]:
                if img_bytes:
                    st.image(img_bytes, use_container_width=True)
                else:
                    st.caption(f"[이미지 데이터 없음: {img.filename}]")

                # 페이지 정보 표시
                page_info = f"p.{img.page}" if img.page else ""
                st.caption(f"{img.filename} {page_info}")

                # 체크박스
                is_selected = st.checkbox(
                    "포함",
                    key=f"{key_prefix}_sel_{img_idx}",
                    value=False,
                )

                if is_selected:
                    caption = st.text_input(
                        "캡션",
                        key=f"{key_prefix}_cap_{img_idx}",
                        placeholder="이미지 설명...",
                    )

                    saved_img = _save_if_needed(
                        mgr,
                        img,
                        img_bytes,
                        post_slug,
                        caption,
                        key_prefix,
                        img_idx,
                    )
                    if saved_img:
                        selected.append(saved_img)
                        md_ref = mgr.generate_markdown_ref(post_slug, saved_img)
                        st.code(md_ref, language="markdown")

    if selected:
        st.success(f"{len(selected)}개 이미지 선택됨")

    return selected


def _save_if_needed(
    mgr: ImageManager,
    img: ImageInfo,
    img_bytes: bytes | None,
    post_slug: str,
    caption: str,
    key_prefix: str,
    img_idx: int,
) -> ImageInfo | None:
    """이미지를 Hugo static에 저장한다 (중복 저장 방지)."""
    if not img_bytes:
        return None

    saved_key = f"{key_prefix}_saved_{img_idx}"
    if saved_key in st.session_state:
        # 이미 저장됨 — 캡션만 업데이트
        info = st.session_state[saved_key]
        info.caption = caption or None
        return info

    saved_info = mgr.save_image(
        img_bytes,
        post_slug,
        img.filename,
        caption=caption or None,
        source="pdf_extract",
    )
    saved_info.page = img.page
    st.session_state[saved_key] = saved_info
    return saved_info
