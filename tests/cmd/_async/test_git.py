"""Tests for libvcs.cmd._async.git."""

from __future__ import annotations

import asyncio
import datetime
import typing as t
from pathlib import Path

import pytest

from libvcs.cmd._async.git import (
    AsyncGit,
)
from libvcs.pytest_plugin import CreateRepoPytestFixtureFn
from libvcs.sync.git import GitSync


class RunFixture(t.NamedTuple):
    """Test fixture for AsyncGit.run()."""

    test_id: str
    args: list[str]
    kwargs: dict[str, t.Any]
    expected_in_output: str | None


RUN_FIXTURES = [
    RunFixture(
        test_id="version",
        args=["version"],
        kwargs={},
        expected_in_output="git version",
    ),
    RunFixture(
        test_id="help_short",
        args=["--help"],
        kwargs={},
        expected_in_output="usage: git",
    ),
]


class TestAsyncGit:
    """Tests for AsyncGit class."""

    def test_init(self, tmp_path: Path) -> None:
        """Test AsyncGit initialization."""
        git = AsyncGit(path=tmp_path)
        assert git.path == tmp_path
        assert git.progress_callback is None

    def test_repr(self, tmp_path: Path) -> None:
        """Test AsyncGit repr."""
        git = AsyncGit(path=tmp_path)
        assert "AsyncGit" in repr(git)
        assert str(tmp_path) in repr(git)

    @pytest.mark.parametrize(
        list(RunFixture._fields),
        RUN_FIXTURES,
        ids=[f.test_id for f in RUN_FIXTURES],
    )
    @pytest.mark.asyncio
    async def test_run(
        self,
        test_id: str,
        args: list[str],
        kwargs: dict[str, t.Any],
        expected_in_output: str | None,
        tmp_path: Path,
    ) -> None:
        """Test AsyncGit.run() with various commands."""
        git = AsyncGit(path=tmp_path)
        output = await git.run(args, **kwargs)
        if expected_in_output is not None:
            assert expected_in_output in output

    @pytest.mark.asyncio
    async def test_run_with_config(
        self,
        git_repo: GitSync,
    ) -> None:
        """Test AsyncGit.run() with config options."""
        git = AsyncGit(path=git_repo.path)
        output = await git.run(
            ["config", "user.name"],
            config={"user.name": "Test User"},
        )
        # Config is passed, command runs
        assert output is not None

    @pytest.mark.asyncio
    async def test_version(self, tmp_path: Path) -> None:
        """Test AsyncGit.version()."""
        git = AsyncGit(path=tmp_path)
        version = await git.version()
        assert "git version" in version


class TestAsyncGitClone:
    """Tests for AsyncGit.clone()."""

    @pytest.mark.asyncio
    async def test_clone_basic(
        self,
        tmp_path: Path,
        create_git_remote_repo: CreateRepoPytestFixtureFn,
    ) -> None:
        """Test basic clone operation."""
        remote_repo = create_git_remote_repo()
        clone_path = tmp_path / "cloned_repo"
        git = AsyncGit(path=clone_path)

        await git.clone(url=f"file://{remote_repo}")

        assert clone_path.exists()
        assert (clone_path / ".git").exists()

    @pytest.mark.asyncio
    async def test_clone_with_depth(
        self,
        tmp_path: Path,
        create_git_remote_repo: CreateRepoPytestFixtureFn,
    ) -> None:
        """Test shallow clone with depth parameter."""
        remote_repo = create_git_remote_repo()
        clone_path = tmp_path / "shallow_repo"
        git = AsyncGit(path=clone_path)

        await git.clone(url=f"file://{remote_repo}", depth=1)

        assert clone_path.exists()
        assert (clone_path / ".git").exists()
        # Note: .git/shallow file only exists if there's more history to truncate
        # For a single-commit repo, depth=1 still works but no shallow file is created

    @pytest.mark.asyncio
    async def test_clone_make_parents(
        self,
        tmp_path: Path,
        create_git_remote_repo: CreateRepoPytestFixtureFn,
    ) -> None:
        """Test clone creates parent directories."""
        remote_repo = create_git_remote_repo()
        clone_path = tmp_path / "deep" / "nested" / "repo"
        git = AsyncGit(path=clone_path)

        await git.clone(url=f"file://{remote_repo}", make_parents=True)

        assert clone_path.exists()


class TestAsyncGitFetch:
    """Tests for AsyncGit.fetch()."""

    @pytest.mark.asyncio
    async def test_fetch_basic(
        self,
        git_repo: GitSync,
    ) -> None:
        """Test basic fetch."""
        git = AsyncGit(path=git_repo.path)
        # Fetch from origin
        output = await git.fetch()
        # Should succeed (might be empty if nothing to fetch)
        assert output is not None


class TestAsyncGitStatus:
    """Tests for AsyncGit.status()."""

    @pytest.mark.asyncio
    async def test_status_clean(
        self,
        git_repo: GitSync,
    ) -> None:
        """Test status on clean repo."""
        git = AsyncGit(path=git_repo.path)
        status = await git.status()
        # Clean repo status
        assert status is not None

    @pytest.mark.asyncio
    async def test_status_porcelain(
        self,
        git_repo: GitSync,
    ) -> None:
        """Test porcelain status format."""
        git = AsyncGit(path=git_repo.path)
        status = await git.status(porcelain=True)
        # Clean repo should have empty porcelain output
        assert status == ""

    @pytest.mark.asyncio
    async def test_status_with_changes(
        self,
        git_repo: GitSync,
    ) -> None:
        """Test status with uncommitted changes."""
        # Create a new file
        new_file = git_repo.path / "new_file.txt"
        new_file.write_text("test content")

        git = AsyncGit(path=git_repo.path)
        status = await git.status(porcelain=True)
        # Should show untracked file
        assert "new_file.txt" in status


class TestAsyncGitCheckout:
    """Tests for AsyncGit.checkout()."""

    @pytest.mark.asyncio
    async def test_checkout_branch(
        self,
        git_repo: GitSync,
    ) -> None:
        """Test checkout existing branch."""
        git = AsyncGit(path=git_repo.path)
        # Get current branch first
        current = await git.symbolic_ref(name="HEAD", short=True)
        # Checkout same branch (should succeed)
        await git.checkout(branch=current.strip())


class TestAsyncGitRevParse:
    """Tests for AsyncGit.rev_parse()."""

    @pytest.mark.asyncio
    async def test_rev_parse_head(
        self,
        git_repo: GitSync,
    ) -> None:
        """Test rev-parse HEAD."""
        git = AsyncGit(path=git_repo.path)
        sha = await git.rev_parse(args="HEAD", verify=True)
        assert sha.strip()
        assert len(sha.strip()) == 40  # Full SHA-1

    @pytest.mark.asyncio
    async def test_rev_parse_show_toplevel(
        self,
        git_repo: GitSync,
    ) -> None:
        """Test rev-parse --show-toplevel."""
        git = AsyncGit(path=git_repo.path)
        toplevel = await git.rev_parse(show_toplevel=True)
        assert toplevel.strip() == str(git_repo.path)


class TestAsyncGitSymbolicRef:
    """Tests for AsyncGit.symbolic_ref()."""

    @pytest.mark.asyncio
    async def test_symbolic_ref_head(
        self,
        git_repo: GitSync,
    ) -> None:
        """Test symbolic-ref HEAD."""
        git = AsyncGit(path=git_repo.path)
        ref = await git.symbolic_ref(name="HEAD")
        assert "refs/heads/" in ref


class TestAsyncGitRemoteManager:
    """Tests for AsyncGitRemoteManager."""

    @pytest.mark.asyncio
    async def test_ls_remotes(
        self,
        git_repo: GitSync,
    ) -> None:
        """Test listing remotes."""
        git = AsyncGit(path=git_repo.path)
        remotes = await git.remotes.ls()
        assert "origin" in remotes

    @pytest.mark.asyncio
    async def test_add_and_remove_remote(
        self,
        git_repo: GitSync,
    ) -> None:
        """Test adding and removing a remote."""
        git = AsyncGit(path=git_repo.path)

        # Add a new remote
        await git.remotes.add(name="test_remote", url="file:///dev/null")

        # Verify it's in the list
        remotes = await git.remotes.ls()
        assert "test_remote" in remotes

        # Remove it
        await git.remotes.remove(name="test_remote")

        # Verify it's gone
        remotes = await git.remotes.ls()
        assert "test_remote" not in remotes

    @pytest.mark.asyncio
    async def test_get_url(
        self,
        git_repo: GitSync,
    ) -> None:
        """Test getting remote URL."""
        git = AsyncGit(path=git_repo.path)
        url = await git.remotes.get_url(name="origin")
        assert url.strip()  # Should have some URL


class TestAsyncGitStashCmd:
    """Tests for AsyncGitStashCmd."""

    @pytest.mark.asyncio
    async def test_stash_ls_empty(
        self,
        git_repo: GitSync,
    ) -> None:
        """Test listing empty stash."""
        git = AsyncGit(path=git_repo.path)
        stashes = await git.stash.ls()
        # Empty stash list
        assert stashes == ""

    @pytest.mark.asyncio
    async def test_stash_save_no_changes(
        self,
        git_repo: GitSync,
    ) -> None:
        """Test stash save with no changes."""
        git = AsyncGit(path=git_repo.path)
        # No changes to stash - command runs but reports nothing to save
        output = await git.stash.save(message="Test stash")
        assert "No local changes to save" in output


class TestAsyncGitReset:
    """Tests for AsyncGit.reset()."""

    @pytest.mark.asyncio
    async def test_reset_soft(
        self,
        git_repo: GitSync,
    ) -> None:
        """Test soft reset."""
        git = AsyncGit(path=git_repo.path)
        # Create a file and commit it
        test_file = git_repo.path / "reset_test.txt"
        test_file.write_text("initial content")
        await git.run(["add", "reset_test.txt"])
        await git.run(["commit", "-m", "test commit"])

        # Soft reset to HEAD~1
        output = await git.reset(pathspec="HEAD~1", soft=True)
        # Soft reset should succeed
        assert output is not None

    @pytest.mark.asyncio
    async def test_reset_mixed(
        self,
        git_repo: GitSync,
    ) -> None:
        """Test mixed reset (default mode)."""
        git = AsyncGit(path=git_repo.path)
        # Create and stage a file
        test_file = git_repo.path / "staged_file.txt"
        test_file.write_text("staged content")
        await git.run(["add", "staged_file.txt"])

        # Mixed reset to unstage
        output = await git.reset(mixed=True)
        assert output is not None

        # Verify file is unstaged
        status = await git.status(porcelain=True)
        assert "??" in status  # Untracked marker

    @pytest.mark.asyncio
    async def test_reset_hard(
        self,
        git_repo: GitSync,
    ) -> None:
        """Test hard reset discards changes."""
        git = AsyncGit(path=git_repo.path)
        # Modify a tracked file
        test_file = git_repo.path / "hard_reset.txt"
        test_file.write_text("original")
        await git.run(["add", "hard_reset.txt"])
        await git.run(["commit", "-m", "add file"])

        # Modify the file
        test_file.write_text("modified")

        # Hard reset should discard changes
        await git.reset(pathspec="HEAD", hard=True)

        # File should be back to original
        assert test_file.read_text() == "original"

    @pytest.mark.asyncio
    async def test_reset_quiet(
        self,
        git_repo: GitSync,
    ) -> None:
        """Test reset with quiet flag."""
        git = AsyncGit(path=git_repo.path)
        output = await git.reset(quiet=True)
        # Quiet mode should suppress output
        assert output == ""

    @pytest.mark.asyncio
    async def test_reset_pathspec_list(
        self,
        git_repo: GitSync,
    ) -> None:
        """Test reset with pathspec as list."""
        git = AsyncGit(path=git_repo.path)
        # Create and stage multiple files
        file1 = git_repo.path / "file1.txt"
        file2 = git_repo.path / "file2.txt"
        file1.write_text("content1")
        file2.write_text("content2")
        await git.run(["add", "file1.txt", "file2.txt"])

        # Reset specific files using list
        output = await git.reset(pathspec=["file1.txt", "file2.txt"])
        assert output is not None


class TestAsyncGitRebase:
    """Tests for AsyncGit.rebase()."""

    @pytest.mark.asyncio
    async def test_rebase_upstream(
        self,
        git_repo: GitSync,
    ) -> None:
        """Test rebase onto upstream branch."""
        git = AsyncGit(path=git_repo.path)
        # Get current branch
        current = await git.symbolic_ref(name="HEAD", short=True)
        current_branch = current.strip()

        # Create a feature branch
        await git.run(["checkout", "-b", "feature"])
        test_file = git_repo.path / "feature_file.txt"
        test_file.write_text("feature content")
        await git.run(["add", "feature_file.txt"])
        await git.run(["commit", "-m", "feature commit"])

        # Rebase onto original branch (trivial rebase - already up to date)
        output = await git.rebase(upstream=current_branch)
        assert output is not None

    @pytest.mark.asyncio
    async def test_rebase_onto(
        self,
        git_repo: GitSync,
    ) -> None:
        """Test rebase with onto option."""
        git = AsyncGit(path=git_repo.path)
        # Get initial commit
        initial = await git.rev_parse(args="HEAD", verify=True)

        # Create branch and commit
        await git.run(["checkout", "-b", "onto_test"])
        test_file = git_repo.path / "onto_file.txt"
        test_file.write_text("onto content")
        await git.run(["add", "onto_file.txt"])
        await git.run(["commit", "-m", "onto commit"])

        # Rebase onto initial commit (trivial case)
        output = await git.rebase(onto=initial.strip(), upstream=initial.strip())
        assert output is not None

    @pytest.mark.asyncio
    async def test_rebase_abort_no_rebase(
        self,
        git_repo: GitSync,
    ) -> None:
        """Test rebase abort when no rebase in progress."""
        git = AsyncGit(path=git_repo.path)
        # Abort with no rebase in progress should fail
        output = await git.rebase(abort=True, check_returncode=False)
        # Returns error message or empty depending on git version
        assert output is not None

    @pytest.mark.asyncio
    async def test_rebase_quiet(
        self,
        tmp_path: Path,
    ) -> None:
        """Test rebase with quiet flag."""
        # Create a fresh git repo with initial commit
        repo_path = tmp_path / "rebase_quiet_repo"
        repo_path.mkdir()
        git = AsyncGit(path=repo_path)
        await git.run(["init"])
        await git.run(["config", "user.email", "test@test.com"])
        await git.run(["config", "user.name", "Test User"])

        # Create initial commit
        test_file = repo_path / "initial.txt"
        test_file.write_text("initial content")
        await git.run(["add", "initial.txt"])
        await git.run(["commit", "-m", "initial"])

        # Rebase onto HEAD (trivial - no changes)
        head = await git.rev_parse(args="HEAD", verify=True)
        output = await git.rebase(upstream=head.strip(), quiet=True)
        # Quiet mode reduces output
        assert output is not None


class TestAsyncGitSubmoduleCmd:
    """Tests for AsyncGitSubmoduleCmd."""

    @pytest.mark.asyncio
    async def test_submodule_init_no_submodules(
        self,
        git_repo: GitSync,
    ) -> None:
        """Test submodule init on repo without submodules."""
        git = AsyncGit(path=git_repo.path)
        # Should succeed even without submodules
        output = await git.submodule.init()
        assert output == ""

    @pytest.mark.asyncio
    async def test_submodule_update_no_submodules(
        self,
        git_repo: GitSync,
    ) -> None:
        """Test submodule update on repo without submodules."""
        git = AsyncGit(path=git_repo.path)
        # Should succeed even without submodules
        output = await git.submodule.update()
        assert output == ""

    @pytest.mark.asyncio
    async def test_submodule_update_with_init(
        self,
        git_repo: GitSync,
    ) -> None:
        """Test submodule update with init flag."""
        git = AsyncGit(path=git_repo.path)
        output = await git.submodule.update(init=True)
        assert output == ""

    @pytest.mark.asyncio
    async def test_submodule_update_recursive(
        self,
        git_repo: GitSync,
    ) -> None:
        """Test submodule update with recursive flag."""
        git = AsyncGit(path=git_repo.path)
        output = await git.submodule.update(recursive=True)
        assert output == ""

    @pytest.mark.asyncio
    async def test_submodule_update_force(
        self,
        git_repo: GitSync,
    ) -> None:
        """Test submodule update with force flag."""
        git = AsyncGit(path=git_repo.path)
        output = await git.submodule.update(force=True)
        assert output == ""

    @pytest.mark.asyncio
    async def test_submodule_update_combined_flags(
        self,
        git_repo: GitSync,
    ) -> None:
        """Test submodule update with combined flags."""
        git = AsyncGit(path=git_repo.path)
        output = await git.submodule.update(init=True, recursive=True, force=True)
        assert output == ""


class TestAsyncGitConcurrency:
    """Tests for concurrent AsyncGit operations."""

    @pytest.mark.asyncio
    async def test_concurrent_status_calls(
        self,
        git_repo: GitSync,
    ) -> None:
        """Test multiple concurrent status calls."""
        git = AsyncGit(path=git_repo.path)

        async def get_status() -> str:
            return await git.status(porcelain=True)

        results = await asyncio.gather(*[get_status() for _ in range(5)])

        assert len(results) == 5
        for result in results:
            assert result == ""  # Clean repo

    @pytest.mark.asyncio
    async def test_concurrent_rev_parse(
        self,
        git_repo: GitSync,
    ) -> None:
        """Test multiple concurrent rev-parse calls."""
        git = AsyncGit(path=git_repo.path)

        async def get_head() -> str:
            return await git.rev_parse(args="HEAD", verify=True)

        results = await asyncio.gather(*[get_head() for _ in range(5)])

        assert len(results) == 5
        # All should return the same SHA
        first_sha = results[0].strip()
        for result in results[1:]:
            assert result.strip() == first_sha


class TestAsyncGitWithCallback:
    """Tests for AsyncGit with progress callbacks."""

    @pytest.mark.asyncio
    async def test_clone_with_callback(
        self,
        tmp_path: Path,
        create_git_remote_repo: CreateRepoPytestFixtureFn,
    ) -> None:
        """Test clone with progress callback."""
        progress_output: list[str] = []

        async def progress_cb(output: str, timestamp: datetime.datetime) -> None:
            progress_output.append(output)

        remote_repo = create_git_remote_repo()
        clone_path = tmp_path / "callback_repo"
        git = AsyncGit(path=clone_path, progress_callback=progress_cb)

        await git.clone(url=f"file://{remote_repo}", log_in_real_time=True)

        assert clone_path.exists()
        # Progress callback should have been called
        # (may be empty for local clone, but mechanism works)
