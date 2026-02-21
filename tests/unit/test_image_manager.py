"""ImageManager 단위 테스트."""

from pathlib import Path

import pytest

from core.content.image_manager import ImageInfo, ImageManager


class TestSaveImage:
    def test_save_creates_file(self, tmp_path: Path) -> None:
        mgr = ImageManager(tmp_path)
        info = mgr.save_image(b"\x89PNG\r\n", "my-post", "diagram.png")

        assert (tmp_path / "images" / "my-post" / "diagram.png").exists()
        assert info.filename == "diagram.png"
        assert info.source == "upload"

    def test_save_preserves_data(self, tmp_path: Path) -> None:
        data = b"\x89PNG\r\nfake image data"
        mgr = ImageManager(tmp_path)
        mgr.save_image(data, "my-post", "img.png")

        saved = (tmp_path / "images" / "my-post" / "img.png").read_bytes()
        assert saved == data

    def test_save_with_caption(self, tmp_path: Path) -> None:
        mgr = ImageManager(tmp_path)
        info = mgr.save_image(b"data", "my-post", "fig1.png", caption="Figure 1")

        assert info.caption == "Figure 1"

    def test_save_with_source(self, tmp_path: Path) -> None:
        mgr = ImageManager(tmp_path)
        info = mgr.save_image(b"data", "my-post", "fig1.png", source="pdf_extract")

        assert info.source == "pdf_extract"

    def test_save_empty_data_raises(self, tmp_path: Path) -> None:
        mgr = ImageManager(tmp_path)
        with pytest.raises(ValueError, match="비어있습니다"):
            mgr.save_image(b"", "my-post", "empty.png")

    def test_save_creates_nested_dirs(self, tmp_path: Path) -> None:
        mgr = ImageManager(tmp_path)
        mgr.save_image(b"data", "deep-post", "img.png")

        assert (tmp_path / "images" / "deep-post").is_dir()

    def test_save_multiple_images(self, tmp_path: Path) -> None:
        mgr = ImageManager(tmp_path)
        mgr.save_image(b"data1", "my-post", "a.png")
        mgr.save_image(b"data2", "my-post", "b.png")

        assert (tmp_path / "images" / "my-post" / "a.png").exists()
        assert (tmp_path / "images" / "my-post" / "b.png").exists()


class TestGenerateMarkdownRef:
    def test_basic_ref(self, tmp_path: Path) -> None:
        mgr = ImageManager(tmp_path)
        info = ImageInfo(filename="diagram.png", source="upload")

        ref = mgr.generate_markdown_ref("my-post", info)
        assert ref == "![diagram.png](/images/my-post/diagram.png)"

    def test_ref_with_caption(self, tmp_path: Path) -> None:
        mgr = ImageManager(tmp_path)
        info = ImageInfo(
            filename="fig1.png", source="upload", caption="Figure 1: Overview"
        )

        ref = mgr.generate_markdown_ref("my-post", info)
        assert ref == "![Figure 1: Overview](/images/my-post/fig1.png)"

    def test_ref_no_caption_uses_filename(self, tmp_path: Path) -> None:
        mgr = ImageManager(tmp_path)
        info = ImageInfo(filename="chart.svg", source="upload")

        ref = mgr.generate_markdown_ref("my-post", info)
        assert "![chart.svg]" in ref


class TestListImages:
    def test_empty_directory(self, tmp_path: Path) -> None:
        mgr = ImageManager(tmp_path)
        assert mgr.list_images("nonexistent") == []

    def test_list_saved_images(self, tmp_path: Path) -> None:
        mgr = ImageManager(tmp_path)
        mgr.save_image(b"data1", "my-post", "a.png")
        mgr.save_image(b"data2", "my-post", "b.jpg")

        images = mgr.list_images("my-post")
        assert len(images) == 2
        filenames = {img.filename for img in images}
        assert filenames == {"a.png", "b.jpg"}

    def test_ignores_non_image_files(self, tmp_path: Path) -> None:
        mgr = ImageManager(tmp_path)
        mgr.save_image(b"data", "my-post", "img.png")

        # 이미지가 아닌 파일 직접 생성
        dir_path = tmp_path / "images" / "my-post"
        (dir_path / "notes.txt").write_text("not an image")

        images = mgr.list_images("my-post")
        assert len(images) == 1
        assert images[0].filename == "img.png"

    def test_supported_extensions(self, tmp_path: Path) -> None:
        mgr = ImageManager(tmp_path)
        for ext in ["png", "jpg", "jpeg", "gif", "svg", "webp"]:
            mgr.save_image(b"data", "my-post", f"img.{ext}")

        images = mgr.list_images("my-post")
        assert len(images) == 6


class TestDeleteImage:
    def test_delete_existing(self, tmp_path: Path) -> None:
        mgr = ImageManager(tmp_path)
        mgr.save_image(b"data", "my-post", "img.png")

        assert mgr.delete_image("my-post", "img.png") is True
        assert not (tmp_path / "images" / "my-post" / "img.png").exists()

    def test_delete_removes_empty_dir(self, tmp_path: Path) -> None:
        mgr = ImageManager(tmp_path)
        mgr.save_image(b"data", "my-post", "img.png")

        mgr.delete_image("my-post", "img.png")
        assert not (tmp_path / "images" / "my-post").exists()

    def test_delete_keeps_dir_with_other_images(self, tmp_path: Path) -> None:
        mgr = ImageManager(tmp_path)
        mgr.save_image(b"data1", "my-post", "a.png")
        mgr.save_image(b"data2", "my-post", "b.png")

        mgr.delete_image("my-post", "a.png")
        assert (tmp_path / "images" / "my-post").exists()
        assert (tmp_path / "images" / "my-post" / "b.png").exists()

    def test_delete_nonexistent_raises(self, tmp_path: Path) -> None:
        mgr = ImageManager(tmp_path)
        with pytest.raises(FileNotFoundError):
            mgr.delete_image("my-post", "nonexistent.png")
