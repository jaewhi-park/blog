"""글 관리 페이지 — 기존 게시글 수정/삭제."""

from __future__ import annotations

import sys
from pathlib import Path

# 프로젝트 루트를 sys.path에 추가 (core 패키지 import 지원)
_PROJECT_ROOT = str(Path(__file__).resolve().parent.parent.parent)
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

import streamlit as st  # noqa: E402

from core.content.category_manager import CategoryManager  # noqa: E402
import shutil  # noqa: E402  # isort: skip

from core.content.image_manager import ImageManager, get_base_path  # noqa: E402
from core.content.markdown_generator import PostMetadata, slugify  # noqa: E402
from core.content.post_manager import PostManager  # noqa: E402
from core.exceptions import GitError  # noqa: E402
from core.publishing.git_manager import GitManager  # noqa: E402
from ui.components.editor import markdown_editor  # noqa: E402
from ui.components.preview import markdown_preview  # noqa: E402

st.set_page_config(page_title="글 관리 | whi-blog", layout="wide")

# ── 경로 설정 ──────────────────────────────────────────────
PROJECT_ROOT = Path(_PROJECT_ROOT)
HUGO_SITE = PROJECT_ROOT / "hugo-site"
HUGO_CONTENT = HUGO_SITE / "content"
HUGO_STATIC = HUGO_SITE / "static"
post_mgr = PostManager(HUGO_CONTENT)
git_mgr = GitManager(PROJECT_ROOT)
img_mgr = ImageManager(HUGO_STATIC, base_path=get_base_path(HUGO_SITE))

# ── 카테고리 목록 로드 ──────────────────────────────────────
cat_mgr = CategoryManager(HUGO_CONTENT)


def _flatten_categories(cats: list, prefix: str = "") -> list[tuple[str, str]]:
    """카테고리 트리를 (표시명, 경로) 튜플의 플랫 리스트로 변환한다."""
    result: list[tuple[str, str]] = []
    for cat in cats:
        display = f"{prefix}{cat.name}" if not prefix else f"{prefix} > {cat.name}"
        result.append((display, cat.path))
        result.extend(_flatten_categories(cat.children, display))
    return result


flat_cats = _flatten_categories(cat_mgr.list_all())

# ── 헤더 ────────────────────────────────────────────────────
st.title("📂 글 관리")

# ── 글 목록 로드 ──────────────────────────────────────────
all_posts = post_mgr.list_posts()

if not all_posts:
    st.info("게시된 글이 없습니다.")
    st.stop()

# ── 필터 ──────────────────────────────────────────────────
col_filter1, col_filter2 = st.columns([2, 1])

with col_filter1:
    # 카테고리 필터
    all_categories = sorted({c for p in all_posts for c in p.categories})
    cat_filter_options = ["전체"] + all_categories
    selected_cat_filter = st.selectbox("카테고리 필터", cat_filter_options)

with col_filter2:
    draft_only = st.checkbox("초안만 보기")

# 필터 적용
filtered_posts = all_posts
if selected_cat_filter != "전체":
    filtered_posts = [p for p in filtered_posts if selected_cat_filter in p.categories]
if draft_only:
    filtered_posts = [p for p in filtered_posts if p.draft]

if not filtered_posts:
    st.warning("필터 조건에 맞는 글이 없습니다.")
    st.stop()

# ── 글 선택 ──────────────────────────────────────────────
post_labels = []
for p in filtered_posts:
    label = f"{p.title}  ({p.date[:10]})"
    if p.draft:
        label += "  [draft]"
    post_labels.append(label)

selected_idx = st.selectbox(
    "글 선택",
    range(len(post_labels)),
    format_func=lambda i: post_labels[i],
)

selected_post = filtered_posts[selected_idx]

# 선택된 글이 바뀌면 위젯 state를 리셋하기 위한 고유 키
_post_key = str(selected_post.file_path)

st.divider()

# ── 선택된 글 로드 ──────────────────────────────────────
metadata, body = post_mgr.load_post(selected_post.file_path)

# ── 메타데이터 편집 ──────────────────────────────────────
col_meta1, col_meta2 = st.columns(2)
with col_meta1:
    edit_title = st.text_input(
        "제목", value=metadata.title, key=f"manage_title_{_post_key}"
    )
with col_meta2:
    edit_tags = st.text_input(
        "태그 (쉼표 구분)",
        value=", ".join(metadata.tags),
        key=f"manage_tags_{_post_key}",
    )

# 카테고리 드롭다운
if flat_cats:
    cat_options = ["(최상위)"] + [display for display, _ in flat_cats]
    cat_paths = [""] + [path for _, path in flat_cats]

    # 현재 카테고리와 매칭되는 인덱스 찾기
    current_cat = metadata.categories[0] if metadata.categories else ""
    default_idx = 0
    if current_cat in cat_paths:
        default_idx = cat_paths.index(current_cat)

    cat_idx = st.selectbox(
        "카테고리",
        range(len(cat_options)),
        index=default_idx,
        format_func=lambda i: cat_options[i],
        key=f"manage_category_{_post_key}",
    )
    edit_category_path = cat_paths[cat_idx]
else:
    edit_category_path = ""

col_opt1, col_opt2 = st.columns(2)
with col_opt1:
    edit_draft = st.checkbox(
        "초안 (draft)", value=metadata.draft, key=f"manage_draft_{_post_key}"
    )
with col_opt2:
    edit_math = st.checkbox(
        "수식 렌더링 (KaTeX)", value=metadata.math, key=f"manage_math_{_post_key}"
    )

st.divider()

# ── 에디터 ──────────────────────────────────────────────
st.markdown("#### 에디터")
edit_content = markdown_editor(
    key=f"manage_editor_{_post_key}",
    height=500,
    initial_value=body,
)

# ── 액션 버튼 ──────────────────────────────────────────
col_a1, col_a2, col_a3 = st.columns([1, 1, 1])

with col_a1:
    preview_clicked = st.button("미리보기", key="manage_preview")

with col_a2:
    save_disabled = not edit_title
    save_clicked = st.button(
        "저장", type="primary", disabled=save_disabled, key="manage_save"
    )

with col_a3:
    delete_clicked = st.button("삭제", type="secondary", key="manage_delete")


# ── 미리보기 ──────────────────────────────────────────
@st.dialog("미리보기", width="large")
def _show_preview() -> None:
    markdown_preview(edit_content, title=edit_title, height=600)


if preview_clicked:
    _show_preview()

# ── 저장 처리 ──────────────────────────────────────────
if save_clicked:
    tags = [t.strip() for t in edit_tags.split(",") if t.strip()]
    categories = [edit_category_path] if edit_category_path else metadata.categories

    updated_meta = PostMetadata(
        title=edit_title,
        date=metadata.date,
        categories=categories,
        tags=tags,
        draft=edit_draft,
        math=edit_math,
        llm_generated=metadata.llm_generated,
        llm_assisted=metadata.llm_assisted,
        llm_disclaimer=metadata.llm_disclaimer,
        llm_model=metadata.llm_model,
        sources=metadata.sources,
    )

    post_mgr.save_post(selected_post.file_path, updated_meta, edit_content)
    rel_path = selected_post.file_path.relative_to(PROJECT_ROOT)
    st.success(f"파일 저장됨: `{rel_path}`")

    post_slug = slugify(edit_title) if edit_title else "untitled"
    commit_files = [selected_post.file_path] + img_mgr.get_image_paths(post_slug)
    try:
        sha = git_mgr.commit_and_push(
            f"edit: {edit_title}",
            commit_files,
            push=True,
        )
        st.success(f"Git push 완료 (commit: `{sha}`)")
    except GitError as e:
        st.warning(f"Git 연동 실패 (파일은 저장됨): {e}")


# ── 삭제 처리 ──────────────────────────────────────────
@st.dialog("글 삭제 확인")
def _confirm_delete() -> None:
    st.warning(f"**{selected_post.title}** 글을 삭제하시겠습니까?")
    st.caption(f"파일: `{selected_post.file_path.relative_to(PROJECT_ROOT)}`")

    col_d1, col_d2 = st.columns(2)
    with col_d1:
        if st.button("삭제 확인", type="primary", key="confirm_delete_btn"):
            # 이미지 경로 수집 (삭제 전에 해야 함)
            post_slug = slugify(selected_post.title) if selected_post.title else ""
            image_files = img_mgr.get_image_paths(post_slug) if post_slug else []

            # 게시글 삭제
            post_mgr.delete_post(selected_post.file_path)
            commit_files = [selected_post.file_path]

            # 이미지 디렉토리 삭제
            if post_slug:
                img_dir = HUGO_STATIC / "images" / post_slug
                if img_dir.exists():
                    commit_files.extend(image_files)
                    shutil.rmtree(img_dir)

            st.success("파일이 삭제되었습니다.")

            try:
                sha = git_mgr.commit_and_push(
                    f"delete: {selected_post.title}",
                    commit_files,
                    push=True,
                )
                st.success(f"Git push 완료 (commit: `{sha}`)")
            except GitError as e:
                st.warning(f"Git 연동 실패 (파일은 삭제됨): {e}")

            st.rerun()
    with col_d2:
        if st.button("취소", key="cancel_delete_btn"):
            st.rerun()


if delete_clicked:
    _confirm_delete()
