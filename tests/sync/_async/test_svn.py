"""Tests for libvcs.sync._async.svn."""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from libvcs.pytest_plugin import CreateRepoPytestFixtureFn
from libvcs.sync._async.svn import AsyncSvnSync

if not shutil.which("svn"):
    pytestmark = pytest.mark.skip(reason="svn is not available")


class TestAsyncSvnSyncGetSvnUrlRev:
    """Tests for AsyncSvnSync._get_svn_url_rev()."""

    @pytest.mark.asyncio
    async def test_get_svn_url_rev_from_working_copy(
        self,
        tmp_path: Path,
        create_svn_remote_repo: CreateRepoPytestFixtureFn,
    ) -> None:
        """Test _get_svn_url_rev from actual working copy."""
        remote_repo = create_svn_remote_repo()
        repo_path = tmp_path / "url_rev_repo"

        repo = AsyncSvnSync(
            url=f"file://{remote_repo}",
            path=repo_path,
        )
        await repo.obtain()

        # Get URL and revision from the working copy
        url, rev = await repo._get_svn_url_rev(str(repo_path))

        # URL should match the remote
        assert url is not None
        assert str(remote_repo) in url
        # Revision should be 0 for empty repo
        assert rev == 0

    @pytest.mark.asyncio
    async def test_get_svn_url_rev_nonexistent_location(
        self,
        tmp_path: Path,
        create_svn_remote_repo: CreateRepoPytestFixtureFn,
    ) -> None:
        """Test _get_svn_url_rev with non-existent location."""
        remote_repo = create_svn_remote_repo()
        repo_path = tmp_path / "url_rev_repo"

        repo = AsyncSvnSync(
            url=f"file://{remote_repo}",
            path=repo_path,
        )
        await repo.obtain()

        # Get URL and revision from non-existent path
        url, rev = await repo._get_svn_url_rev(str(tmp_path / "nonexistent"))

        # Should return None, 0 for non-existent path
        assert url is None
        assert rev == 0

    @pytest.mark.asyncio
    async def test_get_svn_url_rev_xml_format(
        self,
        tmp_path: Path,
        create_svn_remote_repo: CreateRepoPytestFixtureFn,
    ) -> None:
        """Test _get_svn_url_rev with XML format entries file."""
        remote_repo = create_svn_remote_repo()
        repo_path = tmp_path / "xml_repo"

        repo = AsyncSvnSync(
            url=f"file://{remote_repo}",
            path=repo_path,
        )
        await repo.obtain()

        # Create a mock XML entries file
        entries_path = repo_path / ".svn" / "entries"
        xml_data = f"""<?xml version="1.0" encoding="utf-8"?>
<wc-entries xmlns="svn:">
<entry name="" url="file://{remote_repo}" committed-rev="42"/>
<entry name="file.txt" committed-rev="10"/>
</wc-entries>"""
        entries_path.write_text(xml_data)

        # Parse the mock entries file
        url, rev = await repo._get_svn_url_rev(str(repo_path))

        # Should parse URL and max revision from XML
        assert url is not None
        assert str(remote_repo) in url
        assert rev == 42  # max of 42 and 10


class TestAsyncSvnSync:
    """Tests for AsyncSvnSync class."""

    def test_init(self, tmp_path: Path) -> None:
        """Test AsyncSvnSync initialization."""
        repo = AsyncSvnSync(
            url="file:///path/to/repo",
            path=tmp_path / "repo",
        )
        assert repo.url == "file:///path/to/repo"
        assert repo.path == tmp_path / "repo"

    def test_repr(self, tmp_path: Path) -> None:
        """Test AsyncSvnSync repr."""
        repo = AsyncSvnSync(
            url="file:///path/to/repo",
            path=tmp_path / "myrepo",
        )
        assert "AsyncSvnSync" in repr(repo)
        assert "myrepo" in repr(repo)

    def test_init_with_auth(self, tmp_path: Path) -> None:
        """Test AsyncSvnSync initialization with auth credentials."""
        repo = AsyncSvnSync(
            url="svn://svn.example.com/repo",
            path=tmp_path / "repo",
            username="user",
            password="pass",
            svn_trust_cert=True,
        )
        assert repo.username == "user"
        assert repo.password == "pass"
        assert repo.svn_trust_cert is True


class TestAsyncSvnSyncObtain:
    """Tests for AsyncSvnSync.obtain()."""

    @pytest.mark.asyncio
    async def test_obtain_basic(
        self,
        tmp_path: Path,
        create_svn_remote_repo: CreateRepoPytestFixtureFn,
    ) -> None:
        """Test basic obtain operation."""
        remote_repo = create_svn_remote_repo()
        repo_path = tmp_path / "obtained_repo"

        repo = AsyncSvnSync(
            url=f"file://{remote_repo}",
            path=repo_path,
        )
        await repo.obtain()

        assert repo_path.exists()
        assert (repo_path / ".svn").exists()


class TestAsyncSvnSyncUpdateRepo:
    """Tests for AsyncSvnSync.update_repo()."""

    @pytest.mark.asyncio
    async def test_update_repo_basic(
        self,
        tmp_path: Path,
        create_svn_remote_repo: CreateRepoPytestFixtureFn,
    ) -> None:
        """Test basic update_repo operation."""
        remote_repo = create_svn_remote_repo()
        repo_path = tmp_path / "update_repo"

        repo = AsyncSvnSync(
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
        create_svn_remote_repo: CreateRepoPytestFixtureFn,
    ) -> None:
        """Test update_repo checks out if repo doesn't exist."""
        remote_repo = create_svn_remote_repo()
        repo_path = tmp_path / "new_repo"

        repo = AsyncSvnSync(
            url=f"file://{remote_repo}",
            path=repo_path,
        )
        # Just update_repo without obtain first
        await repo.update_repo()

        # Should have checked out
        assert repo_path.exists()
        assert (repo_path / ".svn").exists()


class TestAsyncSvnSyncGetRevision:
    """Tests for AsyncSvnSync.get_revision()."""

    @pytest.mark.asyncio
    async def test_get_revision(
        self,
        tmp_path: Path,
        create_svn_remote_repo: CreateRepoPytestFixtureFn,
    ) -> None:
        """Test get_revision returns current revision."""
        remote_repo = create_svn_remote_repo()
        repo_path = tmp_path / "rev_repo"

        repo = AsyncSvnSync(
            url=f"file://{remote_repo}",
            path=repo_path,
        )
        await repo.obtain()

        revision = await repo.get_revision()
        # SVN revisions start at 0 for empty repos
        assert revision == 0

    @pytest.mark.asyncio
    async def test_get_revision_file(
        self,
        tmp_path: Path,
        create_svn_remote_repo: CreateRepoPytestFixtureFn,
    ) -> None:
        """Test get_revision_file returns file revision."""
        remote_repo = create_svn_remote_repo()
        repo_path = tmp_path / "rev_file_repo"

        repo = AsyncSvnSync(
            url=f"file://{remote_repo}",
            path=repo_path,
        )
        await repo.obtain()

        revision = await repo.get_revision_file("./")
        # SVN revisions start at 0 for empty repos
        assert revision == 0


class TestAsyncSvnRepoFixture:
    """Tests for the async_svn_repo pytest fixture."""

    @pytest.mark.asyncio
    async def test_async_svn_repo_fixture(
        self,
        async_svn_repo: AsyncSvnSync,
    ) -> None:
        """Test that async_svn_repo fixture provides a working repository."""
        assert async_svn_repo.path.exists()
        assert (async_svn_repo.path / ".svn").exists()

    @pytest.mark.asyncio
    async def test_async_svn_repo_revision(
        self,
        async_svn_repo: AsyncSvnSync,
    ) -> None:
        """Test async_svn_repo fixture can get revision."""
        revision = await async_svn_repo.get_revision()
        # SVN revisions start at 0 for empty repos
        assert revision == 0
