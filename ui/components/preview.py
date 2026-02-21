"""마크다운 미리보기 컴포넌트."""

from __future__ import annotations

import streamlit as st

# KaTeX CDN (수식 렌더링)
_KATEX_CSS = '<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/katex@0.16.11/dist/katex.min.css">'
_KATEX_JS = """
<script defer src="https://cdn.jsdelivr.net/npm/katex@0.16.11/dist/katex.min.js"></script>
<script defer src="https://cdn.jsdelivr.net/npm/katex@0.16.11/dist/contrib/auto-render.min.js"
    onload="renderMathInElement(document.body, {
        delimiters: [
            {left: '$$', right: '$$', display: true},
            {left: '$', right: '$', display: false},
            {left: '\\\\[', right: '\\\\]', display: true},
            {left: '\\\\(', right: '\\\\)', display: false}
        ]
    });">
</script>
"""


def markdown_preview(content: str, *, title: str = "", height: int = 400) -> None:
    """마크다운 본문을 미리보기로 렌더링한다. KaTeX 수식을 지원한다.

    Args:
        content: 마크다운 텍스트.
        title: 미리보기 상단에 표시할 제목 (빈 문자열이면 생략).
        height: 미리보기 영역 높이 (px).
    """
    if not content.strip():
        st.info("본문을 입력하면 미리보기가 표시됩니다.")
        return

    # 제목이 있으면 마크다운 상단에 추가
    preview_md = ""
    if title:
        preview_md = f"# {title}\n\n"
    preview_md += content

    html = f"""
    {_KATEX_CSS}
    <div style="
        border: 1px solid #ddd;
        border-radius: 8px;
        padding: 1.5rem;
        max-height: {height}px;
        overflow-y: auto;
        background: var(--body-background, #fff);
    ">
    {_md_to_html(preview_md)}
    </div>
    {_KATEX_JS}
    """
    st.components.v1.html(html, height=height + 40, scrolling=True)


def _md_to_html(md_text: str) -> str:
    """마크다운을 HTML로 변환한다.

    간단한 변환만 수행하며, 수식은 KaTeX JS가 처리한다.
    """
    import re

    lines = md_text.split("\n")
    html_parts: list[str] = []
    in_code_block = False

    for line in lines:
        # 코드 블록
        if line.strip().startswith("```"):
            if in_code_block:
                html_parts.append("</code></pre>")
                in_code_block = False
            else:
                lang = line.strip()[3:]
                html_parts.append(
                    f'<pre><code class="language-{lang}">' if lang else "<pre><code>"
                )
                in_code_block = True
            continue

        if in_code_block:
            html_parts.append(_escape_html(line))
            html_parts.append("\n")
            continue

        # 빈 줄
        if not line.strip():
            html_parts.append("<br>")
            continue

        # 제목
        heading_match = re.match(r"^(#{1,6})\s+(.+)$", line)
        if heading_match:
            level = len(heading_match.group(1))
            text = _inline_format(heading_match.group(2))
            html_parts.append(f"<h{level}>{text}</h{level}>")
            continue

        # 일반 텍스트
        html_parts.append(f"<p>{_inline_format(line)}</p>")

    return "\n".join(html_parts)


def _inline_format(text: str) -> str:
    """인라인 마크다운 서식을 HTML로 변환한다."""
    import re

    # 볼드
    text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
    # 이탤릭
    text = re.sub(r"\*(.+?)\*", r"<em>\1</em>", text)
    # 인라인 코드
    text = re.sub(r"`(.+?)`", r"<code>\1</code>", text)
    # 링크
    text = re.sub(r"\[(.+?)\]\((.+?)\)", r'<a href="\2">\1</a>', text)
    # 이미지
    text = re.sub(r"!\[(.+?)\]\((.+?)\)", r'<img src="\2" alt="\1">', text)

    return text


def _escape_html(text: str) -> str:
    """HTML 특수문자를 이스케이프한다."""
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
