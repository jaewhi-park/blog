"""Git 연동 — 커밋, push, 브랜치, PR."""

from __future__ import annotations

import subprocess
from pathlib import Path


class GitError(Exception):
    """Git 명령 실행 실패."""


class GitManager:
    """Git 저장소 조작을 담당한다."""

    def __init__(self, repo_path: Path) -> None:
        """
        Args:
            repo_path: git 저장소 루트 경로.
        """
        self._repo = repo_path

    def commit_and_push(
        self,
        message: str,
        files: list[Path],
        *,
        push: bool = True,
    ) -> str:
        """파일을 추가하고 커밋한 뒤 push한다.

        Args:
            message: 커밋 메시지.
            files: 커밋할 파일 경로 목록.
            push: True이면 커밋 후 push까지 수행.

        Returns:
            커밋 SHA (short).

        Raises:
            GitError: git 명령 실패 시.
        """
        # git add
        for f in files:
            self._run(["git", "add", str(f)])

        # git commit
        self._run(["git", "commit", "-m", message])

        # commit SHA
        sha = self._run(["git", "rev-parse", "--short", "HEAD"]).strip()

        # push
        if push:
            self._run(["git", "push"])

        return sha

    def create_branch(self, branch_name: str) -> str:
        """새 브랜치를 생성하고 체크아웃한다.

        Args:
            branch_name: 브랜치명.

        Returns:
            생성된 브랜치명.

        Raises:
            GitError: 브랜치 생성 실패 시.
        """
        self._run(["git", "checkout", "-b", branch_name])
        return branch_name

    def create_pr(
        self,
        title: str,
        body: str,
        branch: str,
        base: str = "main",
    ) -> str:
        """GitHub PR을 생성한다 (gh CLI 사용).

        Args:
            title: PR 제목.
            body: PR 본문.
            branch: 소스 브랜치.
            base: 대상 브랜치.

        Returns:
            PR URL.

        Raises:
            GitError: PR 생성 실패 시.
        """
        result = self._run(
            [
                "gh",
                "pr",
                "create",
                "--title",
                title,
                "--body",
                body,
                "--head",
                branch,
                "--base",
                base,
            ]
        )
        return result.strip()

    def has_changes(self) -> bool:
        """스테이징되지 않은 변경사항이 있는지 확인한다."""
        result = self._run(["git", "status", "--porcelain"])
        return bool(result.strip())

    def _run(self, cmd: list[str]) -> str:
        """git 명령을 실행하고 stdout을 반환한다."""
        try:
            result = subprocess.run(
                cmd,
                cwd=self._repo,
                capture_output=True,
                text=True,
                check=True,
            )
            return result.stdout
        except subprocess.CalledProcessError as e:
            raise GitError(f"명령 실패: {' '.join(cmd)}\nstderr: {e.stderr}") from e
