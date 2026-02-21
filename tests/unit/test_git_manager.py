"""GitManager 단위 테스트."""

from pathlib import Path

import pytest

from core.publishing.git_manager import GitError, GitManager


def _init_repo(tmp_path: Path) -> GitManager:
    """테스트용 git 저장소를 초기화하고 GitManager를 반환한다."""
    import subprocess

    subprocess.run(["git", "init"], cwd=tmp_path, capture_output=True, check=True)
    subprocess.run(
        ["git", "config", "user.email", "test@test.com"],
        cwd=tmp_path,
        capture_output=True,
        check=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Test"],
        cwd=tmp_path,
        capture_output=True,
        check=True,
    )
    return GitManager(tmp_path)


class TestCommitAndPush:
    def test_commit_creates_sha(self, tmp_path: Path) -> None:
        mgr = _init_repo(tmp_path)
        f = tmp_path / "test.md"
        f.write_text("hello")

        sha = mgr.commit_and_push("initial commit", [f], push=False)

        assert len(sha) >= 7
        assert sha.isalnum()

    def test_commit_multiple_files(self, tmp_path: Path) -> None:
        mgr = _init_repo(tmp_path)
        f1 = tmp_path / "a.md"
        f2 = tmp_path / "b.md"
        f1.write_text("a")
        f2.write_text("b")

        sha = mgr.commit_and_push("add two files", [f1, f2], push=False)
        assert sha

    def test_commit_no_files_raises(self, tmp_path: Path) -> None:
        mgr = _init_repo(tmp_path)
        # 빈 커밋 시도 — nothing to commit
        with pytest.raises(GitError):
            mgr.commit_and_push("empty", [], push=False)


class TestHasChanges:
    def test_clean_repo(self, tmp_path: Path) -> None:
        mgr = _init_repo(tmp_path)
        f = tmp_path / "init.txt"
        f.write_text("init")
        mgr.commit_and_push("init", [f], push=False)

        assert mgr.has_changes() is False

    def test_dirty_repo(self, tmp_path: Path) -> None:
        mgr = _init_repo(tmp_path)
        f = tmp_path / "init.txt"
        f.write_text("init")
        mgr.commit_and_push("init", [f], push=False)

        (tmp_path / "new.txt").write_text("new")
        assert mgr.has_changes() is True


class TestCreateBranch:
    def test_create_branch(self, tmp_path: Path) -> None:
        mgr = _init_repo(tmp_path)
        # 초기 커밋 필요 (HEAD가 있어야 브랜치 생성 가능)
        f = tmp_path / "init.txt"
        f.write_text("init")
        mgr.commit_and_push("init", [f], push=False)

        branch = mgr.create_branch("feature/test")
        assert branch == "feature/test"

    def test_create_duplicate_branch_raises(self, tmp_path: Path) -> None:
        mgr = _init_repo(tmp_path)
        f = tmp_path / "init.txt"
        f.write_text("init")
        mgr.commit_and_push("init", [f], push=False)

        mgr.create_branch("feature/dup")
        with pytest.raises(GitError):
            mgr.create_branch("feature/dup")
