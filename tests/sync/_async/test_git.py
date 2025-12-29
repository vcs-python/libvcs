"""Tests for libvcs.sync._async.git."""

from __future__ import annotations

import asyncio
import typing as t
from pathlib import Path

import pytest

from libvcs.sync._async.git import AsyncGitSync
from libvcs.sync.git import GitRemote


class TestAsyncGitSync:
    """Tests for AsyncGitSync class."""

    def test_init(self, tmp_path: Path) -> None:
        """Test AsyncGitSync initialization."""
        repo = AsyncGitSync(
            url="https://github.com/test/repo",
            path=tmp_path / "repo",
        )
        assert repo.url == "https://github.com/test/repo"
        assert repo.path == tmp_path / "repo"
        assert "origin" in repo._remotes

    def test_init_with_remotes(self, tmp_path: Path) -> None:
        """Test AsyncGitSync initialization with additional remotes."""
        repo = AsyncGitSync(
            url="https://github.com/test/repo",
            path=tmp_path / "repo",
            remotes={
                "upstream": "https://github.com/upstream/repo",
            },
        )
        assert "origin" in repo._remotes
        assert "upstream" in repo._remotes

    def test_repr(self, tmp_path: Path) -> None:
        """Test AsyncGitSync repr."""
        repo = AsyncGitSync(
            url="https://github.com/test/repo",
            path=tmp_path / "myrepo",
        )
        assert "AsyncGitSync" in repr(repo)
        assert "myrepo" in repr(repo)

    def test_chomp_protocol(self) -> None:
        """Test chomp_protocol removes git+ prefix."""
        assert (
            AsyncGitSync.chomp_protocol("git+https://example.com")
            == "https://example.com"
        )
        assert (
            AsyncGitSync.chomp_protocol("https://example.com") == "https://example.com"
        )


class TestAsyncGitSyncObtain:
    """Tests for AsyncGitSync.obtain()."""

    @pytest.mark.asyncio
    async def test_obtain_basic(
        self,
        tmp_path: Path,
        create_git_remote_repo: t.Any,
    ) -> None:
        """Test basic obtain operation."""
        remote_repo = create_git_remote_repo()
        repo_path = tmp_path / "obtained_repo"

        repo = AsyncGitSync(
            url=f"file://{remote_repo}",
            path=repo_path,
        )
        await repo.obtain()

        assert repo_path.exists()
        assert (repo_path / ".git").exists()

    @pytest.mark.asyncio
    async def test_obtain_shallow(
        self,
        tmp_path: Path,
        create_git_remote_repo: t.Any,
    ) -> None:
        """Test shallow clone via obtain."""
        remote_repo = create_git_remote_repo()
        repo_path = tmp_path / "shallow_repo"

        repo = AsyncGitSync(
            url=f"file://{remote_repo}",
            path=repo_path,
            git_shallow=True,
        )
        await repo.obtain()

        assert repo_path.exists()


class TestAsyncGitSyncUpdateRepo:
    """Tests for AsyncGitSync.update_repo()."""

    @pytest.mark.asyncio
    async def test_update_repo_basic(
        self,
        tmp_path: Path,
        create_git_remote_repo: t.Any,
    ) -> None:
        """Test basic update_repo operation."""
        remote_repo = create_git_remote_repo()
        repo_path = tmp_path / "update_repo"

        repo = AsyncGitSync(
            url=f"file://{remote_repo}",
            path=repo_path,
        )
        # First obtain
        await repo.obtain()

        # Then update
        await repo.update_repo()

        assert repo_path.exists()

    @pytest.mark.asyncio
    async def test_update_repo_obtains_if_missing(
        self,
        tmp_path: Path,
        create_git_remote_repo: t.Any,
    ) -> None:
        """Test update_repo clones if repo doesn't exist."""
        remote_repo = create_git_remote_repo()
        repo_path = tmp_path / "new_repo"

        repo = AsyncGitSync(
            url=f"file://{remote_repo}",
            path=repo_path,
        )
        # Just update_repo without obtain first
        await repo.update_repo()

        # Should have cloned
        assert repo_path.exists()
        assert (repo_path / ".git").exists()


class TestAsyncGitSyncGetRevision:
    """Tests for AsyncGitSync.get_revision()."""

    @pytest.mark.asyncio
    async def test_get_revision(
        self,
        tmp_path: Path,
        create_git_remote_repo: t.Any,
    ) -> None:
        """Test get_revision returns current HEAD or 'initial'."""
        remote_repo = create_git_remote_repo()
        repo_path = tmp_path / "rev_repo"

        repo = AsyncGitSync(
            url=f"file://{remote_repo}",
            path=repo_path,
        )
        await repo.obtain()

        revision = await repo.get_revision()
        assert revision
        # Either a 40-char SHA or "initial" for empty repos
        stripped = revision.strip()
        assert len(stripped) == 40 or stripped == "initial"


class TestAsyncGitSyncRemotes:
    """Tests for AsyncGitSync remote management."""

    @pytest.mark.asyncio
    async def test_remotes_get(
        self,
        tmp_path: Path,
        create_git_remote_repo: t.Any,
    ) -> None:
        """Test remotes_get returns remotes."""
        remote_repo = create_git_remote_repo()
        repo_path = tmp_path / "remotes_repo"

        repo = AsyncGitSync(
            url=f"file://{remote_repo}",
            path=repo_path,
        )
        await repo.obtain()

        remotes = await repo.remotes_get()
        assert "origin" in remotes
        assert isinstance(remotes["origin"], GitRemote)

    @pytest.mark.asyncio
    async def test_remote_get_single(
        self,
        tmp_path: Path,
        create_git_remote_repo: t.Any,
    ) -> None:
        """Test remote() returns single remote."""
        remote_repo = create_git_remote_repo()
        repo_path = tmp_path / "single_remote_repo"

        repo = AsyncGitSync(
            url=f"file://{remote_repo}",
            path=repo_path,
        )
        await repo.obtain()

        origin = await repo.remote("origin")
        assert origin is not None
        assert origin.name == "origin"

    @pytest.mark.asyncio
    async def test_set_remote(
        self,
        tmp_path: Path,
        create_git_remote_repo: t.Any,
    ) -> None:
        """Test set_remote adds a new remote."""
        remote_repo = create_git_remote_repo()
        # Create a second remote repo to use as upstream
        upstream_repo = create_git_remote_repo()
        repo_path = tmp_path / "set_remote_repo"

        repo = AsyncGitSync(
            url=f"file://{remote_repo}",
            path=repo_path,
        )
        await repo.obtain()

        # Add a new remote pointing to another valid repo
        await repo.set_remote(name="upstream", url=f"file://{upstream_repo}")

        # Verify it exists
        upstream = await repo.remote("upstream")
        assert upstream is not None
        assert upstream.name == "upstream"


class TestAsyncGitSyncStatus:
    """Tests for AsyncGitSync.status()."""

    @pytest.mark.asyncio
    async def test_status(
        self,
        tmp_path: Path,
        create_git_remote_repo: t.Any,
    ) -> None:
        """Test status() returns GitStatus without error."""
        remote_repo = create_git_remote_repo()
        repo_path = tmp_path / "status_repo"

        repo = AsyncGitSync(
            url=f"file://{remote_repo}",
            path=repo_path,
        )
        await repo.obtain()

        # Just verify status() runs without error
        # The GitStatus parser may not find data for all repos
        status = await repo.status()
        from libvcs.sync.git import GitStatus

        assert isinstance(status, GitStatus)


class TestAsyncGitSyncConcurrency:
    """Tests for concurrent AsyncGitSync operations."""

    @pytest.mark.asyncio
    async def test_concurrent_obtain(
        self,
        tmp_path: Path,
        create_git_remote_repo: t.Any,
    ) -> None:
        """Test multiple concurrent obtain operations."""
        remote_repo = create_git_remote_repo()

        async def clone_repo(i: int) -> AsyncGitSync:
            repo_path = tmp_path / f"concurrent_repo_{i}"
            repo = AsyncGitSync(
                url=f"file://{remote_repo}",
                path=repo_path,
            )
            await repo.obtain()
            return repo

        repos = await asyncio.gather(*[clone_repo(i) for i in range(3)])

        assert len(repos) == 3
        for repo in repos:
            assert repo.path.exists()
            assert (repo.path / ".git").exists()

    @pytest.mark.asyncio
    async def test_concurrent_status_calls(
        self,
        tmp_path: Path,
        create_git_remote_repo: t.Any,
    ) -> None:
        """Test multiple concurrent status calls on same repo."""
        remote_repo = create_git_remote_repo()
        repo_path = tmp_path / "concurrent_status_repo"

        repo = AsyncGitSync(
            url=f"file://{remote_repo}",
            path=repo_path,
        )
        await repo.obtain()

        async def get_revision() -> str:
            return await repo.get_revision()

        results = await asyncio.gather(*[get_revision() for _ in range(5)])

        assert len(results) == 5
        # All should return the same SHA
        first_sha = results[0].strip()
        for result in results[1:]:
            assert result.strip() == first_sha
