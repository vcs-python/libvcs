"""Performance tests for libvcs pytest fixtures.

These tests verify that fixture caching works correctly and measures
fixture setup times. They are skipped by default - run with --run-performance.
"""

from __future__ import annotations

import pathlib
import typing as t

import pytest

from libvcs.sync.git import GitSync
from libvcs.sync.hg import HgSync
from libvcs.sync.svn import SvnSync

if t.TYPE_CHECKING:
    from libvcs.sync._async.git import AsyncGitSync
    from libvcs.sync._async.hg import AsyncHgSync
    from libvcs.sync._async.svn import AsyncSvnSync


# =============================================================================
# Git Fixture Performance Tests
# =============================================================================


@pytest.mark.performance
def test_git_repo_fixture_uses_cache(
    git_repo: GitSync,
    remote_repos_path: pathlib.Path,
) -> None:
    """Verify git_repo fixture uses master_copy caching."""
    master_copy = remote_repos_path / "git_repo_master"
    assert master_copy.exists(), "master_copy should exist after fixture setup"
    assert (master_copy / ".git").exists(), "master_copy should be a valid git repo"


@pytest.mark.performance
def test_git_remote_repo_uses_persistent_cache(
    git_remote_repo: pathlib.Path,
    libvcs_persistent_cache: pathlib.Path,
) -> None:
    """Verify git_remote_repo uses XDG persistent cache."""
    assert str(libvcs_persistent_cache) in str(git_remote_repo)
    # Non-bare repo has .git directory
    assert (git_remote_repo / ".git").exists(), "remote should have .git directory"


@pytest.mark.performance
def test_git_repo_fixture_setup_time(
    git_repo: GitSync,
) -> None:
    """Verify git_repo fixture setup is fast (uses cached copy)."""
    # The fixture is already set up - this test just verifies it works
    # The actual timing is captured by the fixture profiling hooks
    assert git_repo.path.exists()


@pytest.mark.performance
def test_git_repo_fixture_provides_working_repo(
    git_repo: GitSync,
) -> None:
    """Verify git_repo fixture provides a functional repository."""
    # Should have .git directory
    git_dir = pathlib.Path(git_repo.path) / ".git"
    assert git_dir.exists(), "git_repo should have .git directory"

    # Should be able to get revision
    revision = git_repo.get_revision()
    assert revision, "git_repo should have a revision"


# =============================================================================
# Mercurial Fixture Performance Tests
# =============================================================================


@pytest.mark.performance
def test_hg_repo_fixture_uses_cache(
    hg_repo: HgSync,
    remote_repos_path: pathlib.Path,
) -> None:
    """Verify hg_repo fixture uses master_copy caching."""
    master_copy = remote_repos_path / "hg_repo_master"
    assert master_copy.exists(), "master_copy should exist after fixture setup"
    assert (master_copy / ".hg").exists(), "master_copy should be a valid hg repo"


@pytest.mark.performance
def test_hg_remote_repo_uses_persistent_cache(
    hg_remote_repo: pathlib.Path,
    libvcs_persistent_cache: pathlib.Path,
) -> None:
    """Verify hg_remote_repo uses XDG persistent cache."""
    assert str(libvcs_persistent_cache) in str(hg_remote_repo)
    assert (hg_remote_repo / ".hg").exists(), "remote should have .hg"


@pytest.mark.performance
def test_hg_repo_fixture_provides_working_repo(
    hg_repo: HgSync,
) -> None:
    """Verify hg_repo fixture provides a functional repository."""
    hg_dir = pathlib.Path(hg_repo.path) / ".hg"
    assert hg_dir.exists(), "hg_repo should have .hg directory"


# =============================================================================
# SVN Fixture Performance Tests
# =============================================================================


@pytest.mark.performance
def test_svn_repo_fixture_uses_cache(
    svn_repo: SvnSync,
    remote_repos_path: pathlib.Path,
) -> None:
    """Verify svn_repo fixture uses master_copy caching."""
    master_copy = remote_repos_path / "svn_repo_master"
    assert master_copy.exists(), "master_copy should exist after fixture setup"
    assert (master_copy / ".svn").exists(), "master_copy should be a valid svn checkout"


@pytest.mark.performance
def test_svn_remote_repo_uses_persistent_cache(
    svn_remote_repo: pathlib.Path,
    libvcs_persistent_cache: pathlib.Path,
) -> None:
    """Verify svn_remote_repo uses XDG persistent cache."""
    assert str(libvcs_persistent_cache) in str(svn_remote_repo)
    assert (svn_remote_repo / "format").exists(), "remote should have format file"


# =============================================================================
# Async Fixture Performance Tests
# =============================================================================


@pytest.mark.performance
@pytest.mark.asyncio
async def test_async_git_repo_fixture_uses_shared_cache(
    async_git_repo: AsyncGitSync,
    remote_repos_path: pathlib.Path,
) -> None:
    """Verify async_git_repo shares master_copy with sync git_repo."""
    # Both sync and async should use the same master copy
    master_copy = remote_repos_path / "git_repo_master"
    assert master_copy.exists(), "shared master_copy should exist"


@pytest.mark.performance
@pytest.mark.asyncio
async def test_async_hg_repo_fixture_uses_shared_cache(
    async_hg_repo: AsyncHgSync,
    remote_repos_path: pathlib.Path,
) -> None:
    """Verify async_hg_repo shares master_copy with sync hg_repo."""
    master_copy = remote_repos_path / "hg_repo_master"
    assert master_copy.exists(), "shared master_copy should exist"


@pytest.mark.performance
@pytest.mark.asyncio
async def test_async_svn_repo_fixture_uses_shared_cache(
    async_svn_repo: AsyncSvnSync,
    remote_repos_path: pathlib.Path,
) -> None:
    """Verify async_svn_repo shares master_copy with sync svn_repo."""
    master_copy = remote_repos_path / "svn_repo_master"
    assert master_copy.exists(), "shared master_copy should exist"


# =============================================================================
# Cache Invalidation Tests
# =============================================================================


@pytest.mark.performance
def test_persistent_cache_has_version_key(
    libvcs_persistent_cache: pathlib.Path,
) -> None:
    """Verify persistent cache uses version-based directory."""
    # The cache path should end with a 12-char hex hash
    cache_name = libvcs_persistent_cache.name
    assert len(cache_name) == 12, f"cache key should be 12 chars, got: {cache_name}"
    # Should be valid hex
    try:
        int(cache_name, 16)
    except ValueError:
        pytest.fail(f"cache key should be hex, got: {cache_name}")


@pytest.mark.performance
def test_persistent_cache_location_follows_xdg(
    libvcs_persistent_cache: pathlib.Path,
) -> None:
    """Verify persistent cache is in XDG cache structure."""
    # The cache should be at <xdg_cache>/libvcs-test/<hash>/
    # We verify the structure rather than exact path (since HOME is monkeypatched)
    assert libvcs_persistent_cache.parent.name == "libvcs-test"
    # Cache key should be 12-char hex
    assert len(libvcs_persistent_cache.name) == 12


# =============================================================================
# Multiple Fixture Usage Tests
# =============================================================================


@pytest.mark.performance
def test_multiple_git_repo_instances_are_isolated(
    git_repo: GitSync,
    remote_repos_path: pathlib.Path,
) -> None:
    """Verify each test gets its own copy of git_repo."""
    # Create a file in this repo
    test_file = pathlib.Path(git_repo.path) / "test_isolation.txt"
    test_file.write_text("test isolation")

    # The master copy should NOT have this file
    master_copy = remote_repos_path / "git_repo_master"
    master_test_file = master_copy / "test_isolation.txt"
    assert not master_test_file.exists(), "test changes should not affect master_copy"


@pytest.mark.performance
def test_fixture_timing_baseline(
    git_repo: GitSync,
    hg_repo: HgSync,
    svn_repo: SvnSync,
) -> None:
    """Baseline test that uses all three repo fixtures.

    This test helps establish timing baselines when running with
    --fixture-durations.
    """
    assert pathlib.Path(git_repo.path).exists()
    assert pathlib.Path(hg_repo.path).exists()
    assert pathlib.Path(svn_repo.path).exists()
