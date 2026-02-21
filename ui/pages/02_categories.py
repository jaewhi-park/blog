"""카테고리 관리 페이지."""

from __future__ import annotations

import sys
from pathlib import Path

_PROJECT_ROOT = str(Path(__file__).resolve().parent.parent.parent)
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

import streamlit as st  # noqa: E402

from core.content.category_manager import CategoryManager  # noqa: E402

st.set_page_config(page_title="카테고리 | whi-blog")

HUGO_CONTENT = Path("hugo-site/content")
cat_mgr = CategoryManager(HUGO_CONTENT)


# ── 헬퍼 ────────────────────────────────────────────────────
def _flatten_for_select(cats: list, prefix: str = "") -> list[tuple[str, str]]:
    """카테고리 트리를 (표시명, 경로) 플랫 리스트로 변환."""
    result: list[tuple[str, str]] = []
    for cat in cats:
        display = f"{prefix}{cat.name}" if not prefix else f"{prefix} > {cat.name}"
        result.append((display, cat.path))
        result.extend(_flatten_for_select(cat.children, display))
    return result


def _render_tree(cats: list, indent: int = 0) -> None:
    """카테고리 트리를 들여쓰기로 표시."""
    for cat in cats:
        prefix = "\u2003" * indent  # em space for indentation
        post_count = ""
        st.markdown(f"{prefix}**{cat.name}** `{cat.path}` {post_count}")
        if cat.children:
            _render_tree(cat.children, indent + 1)


# ── 메인 ────────────────────────────────────────────────────
st.title("카테고리 관리")

# 카테고리 트리 표시
cats = cat_mgr.list_all()

if not cats:
    st.info("등록된 카테고리가 없습니다. 아래에서 추가하세요.")
else:
    st.markdown("### 카테고리 트리")
    _render_tree(cats)

st.divider()

# ── 추가 ────────────────────────────────────────────────────
st.markdown("### 카테고리 추가")

col_add1, col_add2 = st.columns(2)
with col_add1:
    new_name = st.text_input("카테고리 이름", placeholder="예: Probability")
with col_add2:
    flat = _flatten_for_select(cats)
    parent_options = ["(최상위)"] + [display for display, _ in flat]
    parent_paths = [None] + [path for _, path in flat]
    parent_idx = st.selectbox(
        "부모 카테고리",
        range(len(parent_options)),
        format_func=lambda i: parent_options[i],
        key="add_parent",
    )
    selected_parent = parent_paths[parent_idx]

if st.button("추가", type="primary", disabled=not new_name.strip()):
    try:
        created = cat_mgr.add(new_name.strip(), parent_path=selected_parent)
        st.success(f"카테고리 추가됨: **{created.name}** (`{created.path}`)")
        st.rerun()
    except FileExistsError:
        st.error("동일한 이름의 카테고리가 이미 존재합니다.")

st.divider()

# ── 삭제 ────────────────────────────────────────────────────
st.markdown("### 카테고리 삭제")

if flat:
    del_options = [display for display, _ in flat]
    del_paths = [path for _, path in flat]
    del_idx = st.selectbox(
        "삭제할 카테고리",
        range(len(del_options)),
        format_func=lambda i: del_options[i],
        key="del_select",
    )

    if st.button("삭제", type="secondary"):
        try:
            cat_mgr.remove(del_paths[del_idx])
            st.success(f"카테고리 삭제됨: `{del_paths[del_idx]}`")
            st.rerun()
        except FileNotFoundError:
            st.error("카테고리를 찾을 수 없습니다.")
        except ValueError as e:
            st.error(f"삭제 불가: {e}")
else:
    st.info("삭제할 카테고리가 없습니다.")

st.divider()

# ── 이동 ────────────────────────────────────────────────────
st.markdown("### 카테고리 이동")

if flat:
    col_mv1, col_mv2 = st.columns(2)
    with col_mv1:
        mv_options = [display for display, _ in flat]
        mv_paths = [path for _, path in flat]
        mv_idx = st.selectbox(
            "이동할 카테고리",
            range(len(mv_options)),
            format_func=lambda i: mv_options[i],
            key="mv_src",
        )
    with col_mv2:
        dest_options = ["(최상위)"] + [display for display, _ in flat]
        dest_paths = [""] + [path for _, path in flat]
        dest_idx = st.selectbox(
            "이동 대상 (새 부모)",
            range(len(dest_options)),
            format_func=lambda i: dest_options[i],
            key="mv_dest",
        )

    if st.button("이동"):
        try:
            cat_mgr.move(mv_paths[mv_idx], dest_paths[dest_idx])
            st.success(
                f"`{mv_paths[mv_idx]}` → `{dest_paths[dest_idx] or '(최상위)'}` 이동 완료"
            )
            st.rerun()
        except FileNotFoundError:
            st.error("카테고리를 찾을 수 없습니다.")
        except FileExistsError:
            st.error("대상 위치에 동일한 이름의 카테고리가 이미 존재합니다.")
else:
    st.info("이동할 카테고리가 없습니다.")
