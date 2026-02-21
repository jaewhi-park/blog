"""글 작성 페이지 — 직접 작성 / 페어 라이팅 / 자동 생성."""

from __future__ import annotations

import sys
from pathlib import Path

# 프로젝트 루트를 sys.path에 추가 (core 패키지 import 지원)
_PROJECT_ROOT = str(Path(__file__).resolve().parent.parent.parent)
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

import streamlit as st  # noqa: E402

from core.content.category_manager import CategoryManager  # noqa: E402
from core.content.markdown_generator import MarkdownGenerator, PostMetadata, slugify  # noqa: E402
from core.exceptions import ConfigError, GitError, HugoError, LLMError  # noqa: E402
from core.publishing.git_manager import GitManager  # noqa: E402
from core.publishing.hugo_builder import HugoBuilder  # noqa: E402
from core.llm.base import LLMRequest  # noqa: E402
from core.llm.factory import LLMFactory  # noqa: E402
from ui.components.editor import image_upload_insert, markdown_editor  # noqa: E402
from ui.components.llm_selector import llm_selector  # noqa: E402
from ui.components.preview import markdown_preview  # noqa: E402

st.set_page_config(page_title="글 작성 | whi-blog", layout="wide")

# ── 경로 설정 ──────────────────────────────────────────────
PROJECT_ROOT = Path(_PROJECT_ROOT)
HUGO_SITE = Path("hugo-site")
HUGO_CONTENT = HUGO_SITE / "content"
HUGO_STATIC = HUGO_SITE / "static"
git_mgr = GitManager(PROJECT_ROOT)
hugo_builder = HugoBuilder(HUGO_SITE)

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
st.title("✏️ 글 작성")

mode = st.radio(
    "작성 모드",
    ["직접 작성", "페어 라이팅", "자동 생성"],
    horizontal=True,
)

st.divider()

# ── 공통: 메타데이터 입력 ───────────────────────────────────
col_meta1, col_meta2 = st.columns(2)
with col_meta1:
    title = st.text_input("제목")
with col_meta2:
    tags_input = st.text_input(
        "태그 (쉼표 구분)", placeholder="random-matrix, probability"
    )

# 카테고리 드롭다운 — CategoryManager 연동
if flat_cats:
    cat_options = ["(최상위)"] + [display for display, _ in flat_cats]
    cat_paths = [""] + [path for _, path in flat_cats]
    cat_idx = st.selectbox(
        "카테고리",
        range(len(cat_options)),
        format_func=lambda i: cat_options[i],
    )
    selected_category_path = cat_paths[cat_idx]
else:
    st.warning("등록된 카테고리가 없습니다. 카테고리 관리 페이지에서 추가하세요.")
    selected_category_path = ""

# 면책 조항 옵션 (모드에 따라 자동 설정)
col_opt1, col_opt2, col_opt3 = st.columns(3)
with col_opt1:
    is_draft = st.checkbox("초안 (draft)")
with col_opt2:
    use_math = st.checkbox("수식 렌더링 (KaTeX)", value=True)
with col_opt3:
    llm_assisted = mode == "페어 라이팅"
    llm_generated = mode == "자동 생성"
    if llm_assisted:
        st.info("📝 LLM 보조 → 면책 조항 자동 삽입")
    elif llm_generated:
        st.info("🤖 LLM 생성 → 면책 조항 자동 삽입")

st.divider()

# ── 직접 작성 모드 ──────────────────────────────────────────
if mode == "직접 작성":
    st.markdown("#### 에디터")
    content = markdown_editor(key="direct_editor", height=500)

    # 이미지 업로드
    with st.expander("이미지 업로드"):
        post_slug = slugify(title) if title else "untitled"
        md_ref = image_upload_insert(post_slug=post_slug, key="direct_img")
        if md_ref:
            st.info("위 마크다운 참조를 에디터 본문에 붙여넣으세요.")

    st.divider()

    # 액션 버튼
    col_a1, col_a2, col_a3, col_a4 = st.columns([1, 1, 1, 1])
    with col_a1:
        if st.button("임시저장", disabled=True):
            pass  # M2.8에서 구현
    with col_a2:
        hugo_preview_clicked = st.button(
            "미리보기 (Hugo)", disabled=not content.strip()
        )
    with col_a3:
        preview_clicked = st.button("미리보기")

    with col_a4:
        publish_disabled = not title or not content.strip()
        if st.button("게시하기", type="primary", disabled=publish_disabled):
            tags = [t.strip() for t in tags_input.split(",") if t.strip()]
            categories = [selected_category_path] if selected_category_path else []

            meta = PostMetadata(
                title=title,
                categories=categories,
                tags=tags,
                draft=is_draft,
                math=use_math,
            )

            gen = MarkdownGenerator()
            file_path = gen.save(meta, content, HUGO_CONTENT, selected_category_path)
            rel_path = file_path.relative_to(PROJECT_ROOT)
            st.success(f"파일 저장됨: `{rel_path}`")

            # Git commit + push
            try:
                sha = git_mgr.commit_and_push(
                    f"post: {title}",
                    [file_path],
                    push=True,
                )
                st.success(f"Git push 완료 (commit: `{sha}`)")
            except GitError as e:
                st.warning(f"Git 연동 실패 (파일은 저장됨): {e}")

    # 미리보기 다이얼로그
    @st.dialog("미리보기", width="large")
    def _show_preview() -> None:
        markdown_preview(content, title=title, height=600)

    if preview_clicked:
        _show_preview()

    # Hugo 로컬 미리보기
    if hugo_preview_clicked:
        try:
            # 임시 저장 후 Hugo 서버로 미리보기
            post_slug = slugify(title) if title else "preview"
            tags = [t.strip() for t in tags_input.split(",") if t.strip()]
            categories = [selected_category_path] if selected_category_path else []
            meta = PostMetadata(
                title=title or "Preview",
                categories=categories,
                tags=tags,
                draft=True,
                math=use_math,
            )
            gen = MarkdownGenerator()
            file_path = gen.save(meta, content, HUGO_CONTENT, selected_category_path)

            hugo_builder.serve()
            url = hugo_builder.get_preview_url(file_path)
            st.markdown(f"Hugo 서버에서 미리보기: [{url}]({url})")
        except HugoError as e:
            st.error(f"Hugo 서버 실행 실패: {e}")

# ── 페어 라이팅 모드 ────────────────────────────────────────
elif mode == "페어 라이팅":
    st.markdown("#### 에디터")
    content = markdown_editor(
        key="pair_editor",
        height=500,
        placeholder="초안을 작성하면 LLM이 피드백을 제공합니다...",
    )

    # 이미지 업로드
    with st.expander("이미지 업로드"):
        post_slug = slugify(title) if title else "untitled"
        md_ref = image_upload_insert(post_slug=post_slug, key="pair_img")
        if md_ref:
            st.info("위 마크다운 참조를 에디터 본문에 붙여넣으세요.")

    provider, model = llm_selector(key_prefix="pair")

    st.divider()

    # 액션 버튼
    col_p1, col_p2, col_p3, col_p4 = st.columns([1, 1, 1, 1])
    with col_p1:
        pair_hugo_preview = st.button(
            "미리보기 (Hugo)", key="pair_hugo_btn", disabled=not content.strip()
        )
    with col_p2:
        pair_preview = st.button("미리보기", key="pair_preview_btn")
    with col_p3:
        feedback_clicked = st.button("LLM 피드백 요청", disabled=not content.strip())
    with col_p4:
        pair_publish_disabled = not title or not content.strip()
        pair_publish_clicked = st.button(
            "게시하기",
            type="primary",
            key="pair_publish",
            disabled=pair_publish_disabled,
        )

    @st.dialog("미리보기", width="large")
    def _show_pair_preview() -> None:
        markdown_preview(content, title=title, height=600)

    if pair_preview:
        _show_pair_preview()

    # Hugo 로컬 미리보기
    if pair_hugo_preview:
        try:
            tags = [t.strip() for t in tags_input.split(",") if t.strip()]
            categories = [selected_category_path] if selected_category_path else []
            meta = PostMetadata(
                title=title or "Preview",
                categories=categories,
                tags=tags,
                draft=True,
                math=use_math,
                llm_assisted=True,
            )
            gen = MarkdownGenerator()
            file_path = gen.save(meta, content, HUGO_CONTENT, selected_category_path)
            hugo_builder.serve()
            url = hugo_builder.get_preview_url(file_path)
            st.markdown(f"Hugo 서버에서 미리보기: [{url}]({url})")
        except HugoError as e:
            st.error(f"Hugo 서버 실행 실패: {e}")

    # LLM 피드백
    if feedback_clicked:
        import asyncio

        try:
            client = LLMFactory.create(provider)
            request = LLMRequest(
                system_prompt=(
                    "당신은 기술 블로그 글 작성을 돕는 편집자입니다. "
                    "사용자의 초안을 읽고 구조, 논리, 명확성, 기술적 정확성 측면에서 "
                    "개선 피드백을 한국어로 제공하세요. 영어 수학/기술 용어는 그대로 유지하세요."
                ),
                user_prompt=f"다음 초안에 대한 피드백을 제공해주세요:\n\n{content}",
                model=model,
            )
            with st.spinner("LLM 피드백 생성 중..."):
                response = asyncio.run(client.generate(request))

            st.markdown("#### LLM 피드백")
            st.markdown(response.content)
            st.caption(
                f"모델: {response.model} | "
                f"토큰: {response.usage.get('input_tokens', 0)} in / "
                f"{response.usage.get('output_tokens', 0)} out"
            )
        except (ConfigError, LLMError) as e:
            st.error(f"LLM 호출 실패: {e}")

    # 게시하기
    if pair_publish_clicked:
        tags = [t.strip() for t in tags_input.split(",") if t.strip()]
        categories = [selected_category_path] if selected_category_path else []
        meta = PostMetadata(
            title=title,
            categories=categories,
            tags=tags,
            draft=is_draft,
            math=use_math,
            llm_assisted=True,
        )
        gen = MarkdownGenerator()
        file_path = gen.save(meta, content, HUGO_CONTENT, selected_category_path)
        rel_path = file_path.relative_to(PROJECT_ROOT)
        st.success(f"파일 저장됨: `{rel_path}`")
        try:
            sha = git_mgr.commit_and_push(f"post: {title}", [file_path], push=True)
            st.success(f"Git push 완료 (commit: `{sha}`)")
        except GitError as e:
            st.warning(f"Git 연동 실패 (파일은 저장됨): {e}")

# ── 자동 생성 모드 ──────────────────────────────────────────
elif mode == "자동 생성":
    st.caption("소스 입력은 M4에서 추가됩니다.")

    prompt = st.text_area(
        "주제 / 지시사항",
        height=150,
        placeholder="생성할 글의 주제나 지시사항을 입력하세요...",
        label_visibility="collapsed",
    )

    provider, model = llm_selector(key_prefix="auto")

    if st.button("생성 요청", type="primary", disabled=not prompt.strip()):
        import asyncio

        try:
            client = LLMFactory.create(provider)
            request = LLMRequest(
                system_prompt=(
                    "당신은 기술 블로그 글을 작성하는 전문 작가입니다. "
                    "주어진 주제에 대해 한국어로 기술 블로그 게시글을 작성하세요. "
                    "영어 수학/기술 용어는 그대로 유지하세요. "
                    "마크다운 형식으로 작성하되, front matter는 포함하지 마세요. "
                    "수식은 $...$ (인라인) 또는 $$...$$ (블록) 형식을 사용하세요."
                ),
                user_prompt=prompt,
                model=model,
            )
            with st.spinner("글 생성 중..."):
                response = asyncio.run(client.generate(request))

            st.session_state["auto_generated_content"] = response.content
            st.session_state["auto_generated_model"] = response.model
            st.caption(
                f"모델: {response.model} | "
                f"토큰: {response.usage.get('input_tokens', 0)} in / "
                f"{response.usage.get('output_tokens', 0)} out"
            )
        except (ConfigError, LLMError) as e:
            st.error(f"LLM 호출 실패: {e}")

    # 생성된 초안 편집 + 게시
    if "auto_generated_content" in st.session_state:
        st.markdown("#### 생성된 초안 (편집 가능)")
        edited = markdown_editor(
            key="auto_editor",
            height=500,
            initial_value=st.session_state["auto_generated_content"],
        )

        # 이미지 업로드
        with st.expander("이미지 업로드"):
            post_slug = slugify(title) if title else "untitled"
            md_ref = image_upload_insert(post_slug=post_slug, key="auto_img")
            if md_ref:
                st.info("위 마크다운 참조를 에디터 본문에 붙여넣으세요.")

        st.divider()

        # 액션 버튼
        col_auto1, col_auto2, col_auto3 = st.columns([1, 1, 1])
        with col_auto1:
            auto_hugo_preview = st.button(
                "미리보기 (Hugo)", key="auto_hugo_btn", disabled=not edited.strip()
            )
        with col_auto2:
            auto_preview = st.button("미리보기", key="auto_preview_btn")
        with col_auto3:
            auto_publish_disabled = not title or not edited.strip()
            auto_publish_clicked = st.button(
                "게시하기",
                type="primary",
                key="auto_publish",
                disabled=auto_publish_disabled,
            )

        @st.dialog("미리보기", width="large")
        def _show_auto_preview() -> None:
            markdown_preview(edited, title=title, height=600)

        if auto_preview:
            _show_auto_preview()

        # Hugo 로컬 미리보기
        if auto_hugo_preview:
            try:
                tags = [t.strip() for t in tags_input.split(",") if t.strip()]
                categories = [selected_category_path] if selected_category_path else []
                meta = PostMetadata(
                    title=title or "Preview",
                    categories=categories,
                    tags=tags,
                    draft=True,
                    math=use_math,
                    llm_generated=True,
                )
                gen = MarkdownGenerator()
                file_path = gen.save(meta, edited, HUGO_CONTENT, selected_category_path)
                hugo_builder.serve()
                url = hugo_builder.get_preview_url(file_path)
                st.markdown(f"Hugo 서버에서 미리보기: [{url}]({url})")
            except HugoError as e:
                st.error(f"Hugo 서버 실행 실패: {e}")

        # 게시하기
        if auto_publish_clicked:
            tags = [t.strip() for t in tags_input.split(",") if t.strip()]
            categories = [selected_category_path] if selected_category_path else []
            meta = PostMetadata(
                title=title,
                categories=categories,
                tags=tags,
                draft=is_draft,
                math=use_math,
                llm_generated=True,
                llm_model=st.session_state.get("auto_generated_model", model),
            )
            gen = MarkdownGenerator()
            file_path = gen.save(meta, edited, HUGO_CONTENT, selected_category_path)
            rel_path = file_path.relative_to(PROJECT_ROOT)
            st.success(f"파일 저장됨: `{rel_path}`")
            try:
                sha = git_mgr.commit_and_push(f"post: {title}", [file_path], push=True)
                st.success(f"Git push 완료 (commit: `{sha}`)")
            except GitError as e:
                st.warning(f"Git 연동 실패 (파일은 저장됨): {e}")
            # 게시 완료 후 session_state 정리
            del st.session_state["auto_generated_content"]
            del st.session_state["auto_generated_model"]
