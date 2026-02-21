"""URL 크롤러 — httpx + BeautifulSoup4 기반 웹 페이지 텍스트 추출."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

import httpx
from bs4 import BeautifulSoup, Tag

from core.exceptions import SourceError

# 텍스트 추출 시 제거할 HTML 태그
_REMOVE_TAGS = frozenset(
    {
        "nav",
        "footer",
        "header",
        "aside",
        "script",
        "style",
        "noscript",
        "iframe",
        "svg",
        "form",
    }
)

# 광고/불필요 영역으로 간주할 class/id 패턴
_AD_PATTERNS = frozenset(
    {
        "ad",
        "ads",
        "advert",
        "advertisement",
        "banner",
        "sidebar",
        "cookie",
        "popup",
        "modal",
        "newsletter",
        "promo",
        "social-share",
        "share-buttons",
        "comment",
        "comments",
    }
)

_DEFAULT_TIMEOUT = 30.0
_DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (compatible; WhiBlogCrawler/1.0; +https://github.com/whikwon/whi-blog)"
)


@dataclass
class CrawledContent:
    """크롤링된 웹 페이지 컨텐츠."""

    url: str
    title: str
    text: str
    fetched_at: str


class URLCrawler:
    """httpx + BeautifulSoup4로 웹 페이지를 크롤링하고 본문 텍스트를 추출한다."""

    def __init__(
        self,
        *,
        timeout: float = _DEFAULT_TIMEOUT,
        user_agent: str = _DEFAULT_USER_AGENT,
    ) -> None:
        """
        Args:
            timeout: HTTP 요청 타임아웃 (초).
            user_agent: User-Agent 헤더 값.
        """
        self._timeout = timeout
        self._user_agent = user_agent

    async def crawl(self, url: str) -> CrawledContent:
        """
        웹 페이지를 크롤링하여 본문 텍스트를 추출한다.

        Args:
            url: 크롤링할 URL.

        Returns:
            추출된 텍스트, 제목, URL, 수집 시각.

        Raises:
            SourceError: URL 접근 실패 또는 파싱 실패.
        """
        html = await self._fetch(url)
        soup = BeautifulSoup(html, "html.parser")

        title = self._extract_title(soup)
        self._remove_noise(soup)
        text = self._extract_text(soup)

        if not text.strip():
            raise SourceError(f"페이지에서 텍스트를 추출할 수 없습니다: {url}")

        return CrawledContent(
            url=url,
            title=title,
            text=text,
            fetched_at=datetime.now(UTC).isoformat(),
        )

    async def _fetch(self, url: str) -> str:
        """URL에서 HTML을 가져온다."""
        try:
            async with httpx.AsyncClient(
                timeout=self._timeout,
                follow_redirects=True,
                headers={"User-Agent": self._user_agent},
            ) as client:
                response = await client.get(url)
                response.raise_for_status()
                return response.text
        except httpx.TimeoutException as e:
            raise SourceError(f"요청 시간 초과: {url}") from e
        except httpx.HTTPStatusError as e:
            raise SourceError(f"HTTP 오류 {e.response.status_code}: {url}") from e
        except httpx.HTTPError as e:
            raise SourceError(f"URL 접근 실패: {url}") from e

    def _extract_title(self, soup: BeautifulSoup) -> str:
        """페이지 제목을 추출한다."""
        if soup.title and soup.title.string:
            return soup.title.string.strip()
        h1 = soup.find("h1")
        if h1:
            return h1.get_text(strip=True)
        return ""

    def _remove_noise(self, soup: BeautifulSoup) -> None:
        """불필요한 HTML 요소를 제거한다."""
        # 태그 기반 제거
        for tag_name in _REMOVE_TAGS:
            for element in soup.find_all(tag_name):
                element.decompose()

        # class/id 기반 광고 영역 제거
        for element in soup.find_all(True):
            if not isinstance(element, Tag):
                continue
            classes = " ".join(element.get("class", []))
            el_id = element.get("id", "") or ""
            combined = f"{classes} {el_id}".lower()
            if any(pattern in combined for pattern in _AD_PATTERNS):
                element.decompose()

    def _extract_text(self, soup: BeautifulSoup) -> str:
        """정제된 HTML에서 본문 텍스트를 추출한다."""
        # <article> 또는 <main> 우선 사용
        body = soup.find("article") or soup.find("main") or soup.find("body")
        if body is None:
            body = soup

        lines: list[str] = []
        for line in body.get_text(separator="\n").splitlines():
            stripped = line.strip()
            if stripped:
                lines.append(stripped)

        return "\n".join(lines)
