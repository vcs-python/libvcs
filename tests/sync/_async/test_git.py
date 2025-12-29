"""Tests for libvcs.sync._async.git."""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from libvcs.pytest_plugin import CreateRepoPytestFixtureFn
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
        create_git_remote_repo: CreateRepoPytestFixtureFn,
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
        create_git_remote_repo: CreateRepoPytestFixtureFn,
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
        create_git_remote_repo: CreateRepoPytestFixtureFn,
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
        create_git_remote_repo: CreateRepoPytestFixtureFn,
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
        create_git_remote_repo: CreateRepoPytestFixtureFn,
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
        create_git_remote_repo: CreateRepoPytestFixtureFn,
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
        create_git_remote_repo: CreateRepoPytestFixtureFn,
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
        create_git_remote_repo: CreateRepoPytestFixtureFn,
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
        create_git_remote_repo: CreateRepoPytestFixtureFn,
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


class TestAsyncGitRepoFixture:
    """Tests for the async_git_repo pytest fixture."""

    @pytest.mark.asyncio
    async def test_async_git_repo_fixture(
        self,
        async_git_repo: AsyncGitSync,
    ) -> None:
        """Test that async_git_repo fixture provides a working repository."""
        # Verify the repo exists and is initialized
        assert async_git_repo.path.exists()
        assert (async_git_repo.path / ".git").exists()

        # Verify we can perform async operations
        revision = await async_git_repo.get_revision()
        assert revision
        assert len(revision.strip()) == 40  # Full SHA

    @pytest.mark.asyncio
    async def test_async_git_repo_status(
        self,
        async_git_repo: AsyncGitSync,
    ) -> None:
        """Test that status() works on fixture-provided repo."""
        from libvcs.sync.git import GitStatus

        status = await async_git_repo.status()
        assert isinstance(status, GitStatus)

    @pytest.mark.asyncio
    async def test_async_git_repo_remotes(
        self,
        async_git_repo: AsyncGitSync,
    ) -> None:
        """Test that remotes are properly configured on fixture-provided repo."""
        remotes = await async_git_repo.remotes_get()
        assert "origin" in remotes


class TestAsyncGitSyncFromPipUrl:
    """Tests for AsyncGitSync.from_pip_url()."""

    def test_from_pip_url_https(self, tmp_path: Path) -> None:
        """Test from_pip_url with git+https URL."""
        repo = AsyncGitSync.from_pip_url(
            pip_url="git+https://github.com/test/repo.git",
            path=tmp_path / "pip_repo",
        )
        assert repo.url == "https://github.com/test/repo.git"
        assert repo.path == tmp_path / "pip_repo"

    def test_from_pip_url_with_revision(self, tmp_path: Path) -> None:
        """Test from_pip_url with revision specifier."""
        repo = AsyncGitSync.from_pip_url(
            pip_url="git+https://github.com/test/repo.git@v1.0.0",
            path=tmp_path / "pip_repo",
        )
        assert repo.url == "https://github.com/test/repo.git"
        assert repo.rev == "v1.0.0"

    def test_from_pip_url_ssh(self, tmp_path: Path) -> None:
        """Test from_pip_url with git+ssh URL."""
        repo = AsyncGitSync.from_pip_url(
            pip_url="git+ssh://git@github.com/test/repo.git",
            path=tmp_path / "pip_repo",
        )
        assert repo.url == "ssh://git@github.com/test/repo.git"


class TestAsyncGitSyncGetGitVersion:
    """Tests for AsyncGitSync.get_git_version()."""

    @pytest.mark.asyncio
    async def test_get_git_version(
        self,
        async_git_repo: AsyncGitSync,
    ) -> None:
        """Test get_git_version returns version string."""
        version = await async_git_repo.get_git_version()
        assert "git version" in version

    @pytest.mark.asyncio
    async def test_get_git_version_format(
        self,
        async_git_repo: AsyncGitSync,
    ) -> None:
        """Test get_git_version returns expected format."""
        version = await async_git_repo.get_git_version()
        # Version string should contain numbers
        import re

        assert re.search(r"\d+\.\d+", version)


class TestAsyncGitSyncUpdateRepoStash:
    """Tests for AsyncGitSync.update_repo() stash handling."""

    @pytest.mark.asyncio
    async def test_update_repo_with_uncommitted_changes(
        self,
        tmp_path: Path,
        create_git_remote_repo: CreateRepoPytestFixtureFn,
    ) -> None:
        """Test update_repo with uncommitted changes triggers stash."""
        from libvcs.pytest_plugin import git_remote_repo_single_commit_post_init

        # Create remote with a commit
        remote_repo = create_git_remote_repo(
            remote_repo_post_init=git_remote_repo_single_commit_post_init
        )
        repo_path = tmp_path / "stash_test_repo"

        repo = AsyncGitSync(
            url=f"file://{remote_repo}",
            path=repo_path,
        )
        await repo.obtain()

        # Create uncommitted changes
        test_file = repo_path / "local_change.txt"
        test_file.write_text("local uncommitted content")
        await repo.cmd.run(["add", "local_change.txt"])

        # Update should handle the uncommitted changes (may stash if needed)
        # This tests the stash logic path
        await repo.update_repo()

        # Repo should still exist and be valid
        assert repo_path.exists()
        revision = await repo.get_revision()
        assert revision

    @pytest.mark.asyncio
    async def test_update_repo_clean_working_tree(
        self,
        tmp_path: Path,
        create_git_remote_repo: CreateRepoPytestFixtureFn,
    ) -> None:
        """Test update_repo with clean working tree skips stash."""
        from libvcs.pytest_plugin import git_remote_repo_single_commit_post_init

        remote_repo = create_git_remote_repo(
            remote_repo_post_init=git_remote_repo_single_commit_post_init
        )
        repo_path = tmp_path / "clean_repo"

        repo = AsyncGitSync(
            url=f"file://{remote_repo}",
            path=repo_path,
        )
        await repo.obtain()

        # No changes - update should succeed without stash
        await repo.update_repo()

        assert repo_path.exists()


class TestAsyncGitSyncSetRemotes:
    """Tests for AsyncGitSync.set_remotes()."""

    @pytest.mark.asyncio
    async def test_set_remotes_overwrite_false(
        self,
        tmp_path: Path,
        create_git_remote_repo: CreateRepoPytestFixtureFn,
    ) -> None:
        """Test set_remotes with overwrite=False preserves existing remotes."""
        remote_repo = create_git_remote_repo()
        repo_path = tmp_path / "set_remotes_repo"

        repo = AsyncGitSync(
            url=f"file://{remote_repo}",
            path=repo_path,
        )
        await repo.obtain()

        # Get original origin URL
        original_remotes = await repo.remotes_get()
        original_origin_url = original_remotes["origin"].fetch_url

        # Try to set remotes with overwrite=False
        await repo.set_remotes(overwrite=False)

        # Origin should still have same URL
        updated_remotes = await repo.remotes_get()
        assert updated_remotes["origin"].fetch_url == original_origin_url

    @pytest.mark.asyncio
    async def test_set_remotes_adds_new_remote(
        self,
        tmp_path: Path,
        create_git_remote_repo: CreateRepoPytestFixtureFn,
    ) -> None:
        """Test set_remotes adds new remotes from configuration."""
        remote_repo = create_git_remote_repo()
        upstream_repo = create_git_remote_repo()
        repo_path = tmp_path / "add_remote_repo"

        repo = AsyncGitSync(
            url=f"file://{remote_repo}",
            path=repo_path,
            remotes={"upstream": f"file://{upstream_repo}"},
        )
        await repo.obtain()

        # Set remotes should add upstream
        await repo.set_remotes(overwrite=False)

        remotes = await repo.remotes_get()
        assert "origin" in remotes
        assert "upstream" in remotes


class TestAsyncGitSyncGetCurrentRemoteName:
    """Tests for AsyncGitSync.get_current_remote_name()."""

    @pytest.mark.asyncio
    async def test_get_current_remote_name_default(
        self,
        async_git_repo: AsyncGitSync,
    ) -> None:
        """Test get_current_remote_name returns origin by default."""
        remote_name = await async_git_repo.get_current_remote_name()
        assert remote_name == "origin"

    @pytest.mark.asyncio
    async def test_get_current_remote_name_on_detached_head(
        self,
        tmp_path: Path,
        create_git_remote_repo: CreateRepoPytestFixtureFn,
    ) -> None:
        """Test get_current_remote_name on detached HEAD falls back to origin."""
        from libvcs.pytest_plugin import git_remote_repo_single_commit_post_init

        remote_repo = create_git_remote_repo(
            remote_repo_post_init=git_remote_repo_single_commit_post_init
        )
        repo_path = tmp_path / "detached_head_repo"

        repo = AsyncGitSync(
            url=f"file://{remote_repo}",
            path=repo_path,
        )
        await repo.obtain()

        # Detach HEAD
        head = await repo.cmd.rev_parse(args="HEAD", verify=True)
        await repo.cmd.checkout(branch=head.strip(), detach=True)

        # Should fall back to 'origin'
        remote_name = await repo.get_current_remote_name()
        assert remote_name == "origin"


class TestAsyncGitSyncConcurrency:
    """Tests for concurrent AsyncGitSync operations."""

    @pytest.mark.asyncio
    async def test_concurrent_obtain(
        self,
        tmp_path: Path,
        create_git_remote_repo: CreateRepoPytestFixtureFn,
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
        create_git_remote_repo: CreateRepoPytestFixtureFn,
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
