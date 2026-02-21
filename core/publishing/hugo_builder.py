"""Hugo 빌드 및 로컬 서버."""

from __future__ import annotations

import subprocess
import time
from pathlib import Path

from core.exceptions import HugoError


class HugoBuilder:
    """Hugo 빌드와 로컬 서버를 관리한다."""

    def __init__(self, hugo_site_path: Path) -> None:
        """
        Args:
            hugo_site_path: Hugo 사이트 루트 경로 (예: hugo-site/).
        """
        self._site_path = hugo_site_path
        self._server_process: subprocess.Popen | None = None

    def build(self) -> bool:
        """hugo build를 실행한다.

        Returns:
            빌드 성공 여부.

        Raises:
            HugoError: 빌드 실패 시.
        """
        try:
            subprocess.run(
                ["hugo", "--minify"],
                cwd=self._site_path,
                capture_output=True,
                text=True,
                check=True,
            )
            return True
        except subprocess.CalledProcessError as e:
            raise HugoError(f"Hugo 빌드 실패:\n{e.stderr}") from e
        except FileNotFoundError as e:
            raise HugoError("Hugo가 설치되어 있지 않습니다.") from e

    def serve(self, port: int = 1313) -> subprocess.Popen:
        """hugo server -D를 실행한다 (로컬 미리보기).

        이미 실행 중인 서버가 있으면 그대로 반환한다.

        Args:
            port: 서버 포트.

        Returns:
            서버 프로세스.

        Raises:
            HugoError: 서버 시작 실패 시.
        """
        # 이미 실행 중이면 재사용
        if self._server_process is not None and self._server_process.poll() is None:
            return self._server_process

        try:
            proc = subprocess.Popen(
                ["hugo", "server", "-D", "--port", str(port)],
                cwd=self._site_path,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            # 서버 기동 대기
            time.sleep(2)

            if proc.poll() is not None:
                stderr = proc.stderr.read().decode() if proc.stderr else ""
                raise HugoError(f"Hugo 서버 시작 실패:\n{stderr}")

            self._server_process = proc
            return proc
        except FileNotFoundError as e:
            raise HugoError("Hugo가 설치되어 있지 않습니다.") from e

    def stop(self) -> None:
        """실행 중인 Hugo 서버를 종료한다."""
        if self._server_process is not None and self._server_process.poll() is None:
            self._server_process.terminate()
            self._server_process.wait(timeout=5)
        self._server_process = None

    def is_serving(self) -> bool:
        """Hugo 서버가 실행 중인지 확인한다."""
        return self._server_process is not None and self._server_process.poll() is None

    def get_preview_url(self, post_path: Path, port: int = 1313) -> str:
        """게시글의 로컬 미리보기 URL을 반환한다.

        Args:
            post_path: 게시글 파일 경로 (content 디렉토리 기준 상대 경로).
            port: Hugo 서버 포트.

        Returns:
            로컬 미리보기 URL.
        """
        # content/math/probability/my-post.md → math/probability/my-post/
        content_dir = self._site_path / "content"
        try:
            rel = post_path.relative_to(content_dir)
        except ValueError:
            rel = post_path

        # .md 확장자 제거, URL 경로로 변환
        url_path = str(rel.with_suffix("")).replace("\\", "/")
        return f"http://localhost:{port}/{url_path}/"
