"""URLCrawler 단위 테스트."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import httpx
import pytest

from core.exceptions import SourceError
from core.sources.url_crawler import CrawledContent, URLCrawler


@pytest.fixture
def crawler() -> URLCrawler:
    return URLCrawler()


def _mock_response(html: str, status_code: int = 200) -> httpx.Response:
    """테스트용 httpx.Response를 생성한다."""
    request = httpx.Request("GET", "https://example.com")
    return httpx.Response(status_code=status_code, text=html, request=request)


def _patch_fetch(crawler: URLCrawler, html: str) -> AsyncMock:
    """crawler._fetch를 모킹하여 지정된 HTML을 반환하도록 한다."""
    mock = AsyncMock(return_value=html)
    crawler._fetch = mock  # type: ignore[method-assign]
    return mock


class TestCrawlBasic:
    @pytest.mark.asyncio
    async def test_extracts_title_and_text(self, crawler: URLCrawler) -> None:
        html = """
        <html>
            <head><title>Test Page</title></head>
            <body>
                <article><p>Hello world</p></article>
            </body>
        </html>
        """
        _patch_fetch(crawler, html)
        result = await crawler.crawl("https://example.com")

        assert result.title == "Test Page"
        assert "Hello world" in result.text
        assert result.url == "https://example.com"
        assert result.fetched_at  # ISO format timestamp

    @pytest.mark.asyncio
    async def test_title_from_h1_when_no_title_tag(self, crawler: URLCrawler) -> None:
        html = """
        <html><body>
            <h1>Main Heading</h1>
            <p>Content here</p>
        </body></html>
        """
        _patch_fetch(crawler, html)
        result = await crawler.crawl("https://example.com")

        assert result.title == "Main Heading"

    @pytest.mark.asyncio
    async def test_empty_title_when_none(self, crawler: URLCrawler) -> None:
        html = "<html><body><p>Just text</p></body></html>"
        _patch_fetch(crawler, html)
        result = await crawler.crawl("https://example.com")

        assert result.title == ""

    @pytest.mark.asyncio
    async def test_returns_crawled_content_dataclass(self, crawler: URLCrawler) -> None:
        html = "<html><body><p>Content</p></body></html>"
        _patch_fetch(crawler, html)
        result = await crawler.crawl("https://example.com")

        assert isinstance(result, CrawledContent)


class TestNoiseRemoval:
    @pytest.mark.asyncio
    async def test_removes_nav_footer_header(self, crawler: URLCrawler) -> None:
        html = """
        <html><body>
            <nav>Navigation</nav>
            <header>Header</header>
            <article><p>Main content</p></article>
            <footer>Footer</footer>
        </body></html>
        """
        _patch_fetch(crawler, html)
        result = await crawler.crawl("https://example.com")

        assert "Navigation" not in result.text
        assert "Header" not in result.text
        assert "Footer" not in result.text
        assert "Main content" in result.text

    @pytest.mark.asyncio
    async def test_removes_script_and_style(self, crawler: URLCrawler) -> None:
        html = """
        <html><body>
            <script>var x = 1;</script>
            <style>.foo { color: red; }</style>
            <p>Visible text</p>
        </body></html>
        """
        _patch_fetch(crawler, html)
        result = await crawler.crawl("https://example.com")

        assert "var x" not in result.text
        assert "color" not in result.text
        assert "Visible text" in result.text

    @pytest.mark.asyncio
    async def test_removes_ad_elements_by_class(self, crawler: URLCrawler) -> None:
        html = """
        <html><body>
            <div class="advertisement">Buy stuff!</div>
            <div class="sidebar">Side content</div>
            <article><p>Real content</p></article>
        </body></html>
        """
        _patch_fetch(crawler, html)
        result = await crawler.crawl("https://example.com")

        assert "Buy stuff" not in result.text
        assert "Side content" not in result.text
        assert "Real content" in result.text

    @pytest.mark.asyncio
    async def test_removes_ad_elements_by_id(self, crawler: URLCrawler) -> None:
        html = """
        <html><body>
            <div id="banner">Banner ad</div>
            <main><p>Article text</p></main>
        </body></html>
        """
        _patch_fetch(crawler, html)
        result = await crawler.crawl("https://example.com")

        assert "Banner ad" not in result.text
        assert "Article text" in result.text


class TestTextExtraction:
    @pytest.mark.asyncio
    async def test_prefers_article_tag(self, crawler: URLCrawler) -> None:
        html = """
        <html><body>
            <div>Outside article</div>
            <article><p>Inside article</p></article>
        </body></html>
        """
        _patch_fetch(crawler, html)
        result = await crawler.crawl("https://example.com")

        assert "Inside article" in result.text
        # article 외부 텍스트는 포함되지 않아야 함
        assert "Outside article" not in result.text

    @pytest.mark.asyncio
    async def test_prefers_main_tag(self, crawler: URLCrawler) -> None:
        html = """
        <html><body>
            <div>Outside main</div>
            <main><p>Inside main</p></main>
        </body></html>
        """
        _patch_fetch(crawler, html)
        result = await crawler.crawl("https://example.com")

        assert "Inside main" in result.text
        assert "Outside main" not in result.text

    @pytest.mark.asyncio
    async def test_falls_back_to_body(self, crawler: URLCrawler) -> None:
        html = """
        <html><body>
            <div><p>Body content only</p></div>
        </body></html>
        """
        _patch_fetch(crawler, html)
        result = await crawler.crawl("https://example.com")

        assert "Body content only" in result.text

    @pytest.mark.asyncio
    async def test_strips_blank_lines(self, crawler: URLCrawler) -> None:
        html = """
        <html><body>
            <p>Line one</p>


            <p>Line two</p>
        </body></html>
        """
        _patch_fetch(crawler, html)
        result = await crawler.crawl("https://example.com")

        # 빈 줄이 제거되어 연속된 줄로 나와야 함
        lines = result.text.splitlines()
        assert all(line.strip() for line in lines)


class TestErrorHandling:
    @pytest.mark.asyncio
    async def test_empty_text_raises(self, crawler: URLCrawler) -> None:
        html = """
        <html><body>
            <nav>Only navigation</nav>
            <script>Only script</script>
        </body></html>
        """
        _patch_fetch(crawler, html)
        with pytest.raises(SourceError, match="텍스트를 추출할 수 없습니다"):
            await crawler.crawl("https://example.com")

    @pytest.mark.asyncio
    async def test_http_error_raises(self, crawler: URLCrawler) -> None:
        request = httpx.Request("GET", "https://example.com")
        mock_response = httpx.Response(404, request=request)

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response

        with patch("core.sources.url_crawler.httpx.AsyncClient") as mock_cls:
            mock_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)

            with pytest.raises(SourceError, match="HTTP 오류 404"):
                await crawler.crawl("https://example.com")

    @pytest.mark.asyncio
    async def test_timeout_raises(self, crawler: URLCrawler) -> None:
        mock_client = AsyncMock()
        mock_client.get.side_effect = httpx.TimeoutException("timeout")

        with patch("core.sources.url_crawler.httpx.AsyncClient") as mock_cls:
            mock_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)

            with pytest.raises(SourceError, match="요청 시간 초과"):
                await crawler.crawl("https://example.com")

    @pytest.mark.asyncio
    async def test_connection_error_raises(self, crawler: URLCrawler) -> None:
        mock_client = AsyncMock()
        mock_client.get.side_effect = httpx.ConnectError("connection refused")

        with patch("core.sources.url_crawler.httpx.AsyncClient") as mock_cls:
            mock_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)

            with pytest.raises(SourceError, match="URL 접근 실패"):
                await crawler.crawl("https://example.com")


class TestCustomConfig:
    def test_custom_timeout_and_user_agent(self) -> None:
        crawler = URLCrawler(timeout=10.0, user_agent="CustomBot/1.0")
        assert crawler._timeout == 10.0
        assert crawler._user_agent == "CustomBot/1.0"
