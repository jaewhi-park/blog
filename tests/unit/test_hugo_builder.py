"""HugoBuilder 단위 테스트."""

from pathlib import Path

from core.publishing.hugo_builder import HugoBuilder


class TestGetPreviewUrl:
    def test_basic_path(self, tmp_path: Path) -> None:
        builder = HugoBuilder(tmp_path)
        content_dir = tmp_path / "content"
        post = content_dir / "math" / "probability" / "my-post.md"

        url = builder.get_preview_url(post)
        assert url == "http://localhost:1313/math/probability/my-post/"

    def test_top_level_post(self, tmp_path: Path) -> None:
        builder = HugoBuilder(tmp_path)
        content_dir = tmp_path / "content"
        post = content_dir / "hello-world.md"

        url = builder.get_preview_url(post)
        assert url == "http://localhost:1313/hello-world/"

    def test_custom_port(self, tmp_path: Path) -> None:
        builder = HugoBuilder(tmp_path)
        content_dir = tmp_path / "content"
        post = content_dir / "math" / "test.md"

        url = builder.get_preview_url(post, port=8080)
        assert url == "http://localhost:8080/math/test/"

    def test_relative_path_fallback(self, tmp_path: Path) -> None:
        builder = HugoBuilder(tmp_path)
        # content 디렉토리 바깥의 경로
        post = Path("some/other/post.md")

        url = builder.get_preview_url(post)
        assert url == "http://localhost:1313/some/other/post/"


class TestIsServing:
    def test_not_serving_initially(self, tmp_path: Path) -> None:
        builder = HugoBuilder(tmp_path)
        assert builder.is_serving() is False

    def test_stop_when_not_serving(self, tmp_path: Path) -> None:
        builder = HugoBuilder(tmp_path)
        # stop()은 서버가 없어도 에러 없이 동작해야 함
        builder.stop()
        assert builder.is_serving() is False
