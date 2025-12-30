"""Tests for libvcs.sync._async.hg."""

from __future__ import annotations

from pathlib import Path

import pytest

from libvcs.pytest_plugin import CreateRepoPytestFixtureFn
from libvcs.sync._async.hg import AsyncHgSync


class TestAsyncHgSync:
    """Tests for AsyncHgSync class."""

    def test_init(self, tmp_path: Path) -> None:
        """Test AsyncHgSync initialization."""
        repo = AsyncHgSync(
            url="https://hg.example.com/repo",
            path=tmp_path / "repo",
        )
        assert repo.url == "https://hg.example.com/repo"
        assert repo.path == tmp_path / "repo"

    def test_repr(self, tmp_path: Path) -> None:
        """Test AsyncHgSync repr."""
        repo = AsyncHgSync(
            url="https://hg.example.com/repo",
            path=tmp_path / "myrepo",
        )
        assert "AsyncHgSync" in repr(repo)
        assert "myrepo" in repr(repo)


class TestAsyncHgSyncObtain:
    """Tests for AsyncHgSync.obtain()."""

    @pytest.mark.asyncio
    async def test_obtain_basic(
        self,
        tmp_path: Path,
        create_hg_remote_repo: CreateRepoPytestFixtureFn,
    ) -> None:
        """Test basic obtain operation."""
        remote_repo = create_hg_remote_repo()
        repo_path = tmp_path / "obtained_repo"

        repo = AsyncHgSync(
            url=f"file://{remote_repo}",
            path=repo_path,
        )
        await repo.obtain()

        assert repo_path.exists()
        assert (repo_path / ".hg").exists()


class TestAsyncHgSyncUpdateRepo:
    """Tests for AsyncHgSync.update_repo()."""

    @pytest.mark.asyncio
    async def test_update_repo_basic(
        self,
        tmp_path: Path,
        create_hg_remote_repo: CreateRepoPytestFixtureFn,
    ) -> None:
        """Test basic update_repo operation."""
        remote_repo = create_hg_remote_repo()
        repo_path = tmp_path / "update_repo"

        repo = AsyncHgSync(
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
        create_hg_remote_repo: CreateRepoPytestFixtureFn,
    ) -> None:
        """Test update_repo clones if repo doesn't exist."""
        remote_repo = create_hg_remote_repo()
        repo_path = tmp_path / "new_repo"

        repo = AsyncHgSync(
            url=f"file://{remote_repo}",
            path=repo_path,
        )
        # Just update_repo without obtain first
        await repo.update_repo()

        # Should have cloned
        assert repo_path.exists()
        assert (repo_path / ".hg").exists()


class TestAsyncHgSyncGetRevision:
    """Tests for AsyncHgSync.get_revision()."""

    @pytest.mark.asyncio
    async def test_get_revision(
        self,
        tmp_path: Path,
        create_hg_remote_repo: CreateRepoPytestFixtureFn,
    ) -> None:
        """Test get_revision returns current revision."""
        remote_repo = create_hg_remote_repo()
        repo_path = tmp_path / "rev_repo"

        repo = AsyncHgSync(
            url=f"file://{remote_repo}",
            path=repo_path,
        )
        await repo.obtain()

        revision = await repo.get_revision()
        # Mercurial revisions are numeric (0, 1, 2, ...)
        assert revision.strip().isdigit() or revision.strip() == ""


class TestAsyncHgRepoFixture:
    """Tests for the async_hg_repo pytest fixture."""

    @pytest.mark.asyncio
    async def test_async_hg_repo_fixture(
        self,
        async_hg_repo: AsyncHgSync,
    ) -> None:
        """Test that async_hg_repo fixture provides a working repository."""
        assert async_hg_repo.path.exists()
        assert (async_hg_repo.path / ".hg").exists()

    @pytest.mark.asyncio
    async def test_async_hg_repo_revision(
        self,
        async_hg_repo: AsyncHgSync,
    ) -> None:
        """Test async_hg_repo fixture can get revision."""
        revision = await async_hg_repo.get_revision()
        assert revision.strip().isdigit() or revision.strip() == ""
