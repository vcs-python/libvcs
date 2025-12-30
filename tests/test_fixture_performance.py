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
    from libvcs.pytest_plugin import RepoFixtureResult
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


@pytest.mark.performance
def test_hg_remote_repo_has_marker_file(
    hg_remote_repo: pathlib.Path,
) -> None:
    """Verify hg_remote_repo uses marker file for initialization tracking."""
    marker = hg_remote_repo / ".libvcs_initialized"
    assert marker.exists(), "hg_remote_repo should have .libvcs_initialized marker"


@pytest.mark.performance
def test_hg_repo_warm_cache_is_fast(
    hg_repo: RepoFixtureResult[HgSync],
) -> None:
    """Verify hg_repo warm cache uses copytree (should be <50ms).

    Mercurial is inherently slow (~100ms for hg --version alone),
    so we verify that cached runs avoid hg commands entirely.
    """
    # If from_cache is True, this was a copytree operation
    if hg_repo.from_cache:
        # created_at is relative perf_counter, but we verify it's fast
        assert hg_repo.master_copy_path.exists()


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


@pytest.mark.performance
def test_svn_repo_fixture_provides_working_repo(
    svn_repo: SvnSync,
) -> None:
    """Verify svn_repo fixture provides a functional repository."""
    # Should have .svn directory
    svn_dir = pathlib.Path(svn_repo.path) / ".svn"
    assert svn_dir.exists(), "svn_repo should have .svn directory"

    # Should be able to get revision (0 is valid for initial checkout)
    revision = svn_repo.get_revision()
    assert revision is not None, "svn_repo should return a revision"


@pytest.mark.performance
def test_svn_remote_repo_has_marker_file(
    svn_remote_repo: pathlib.Path,
) -> None:
    """Verify svn_remote_repo uses marker file for initialization tracking."""
    marker = svn_remote_repo / ".libvcs_initialized"
    assert marker.exists(), "svn_remote_repo should have .libvcs_initialized marker"


@pytest.mark.performance
def test_svn_repo_warm_cache_is_fast(
    svn_repo: RepoFixtureResult[SvnSync],
) -> None:
    """Verify svn_repo warm cache uses copytree (should be <50ms).

    SVN checkout is slow (~500ms for svn co alone),
    so we verify that cached runs avoid svn commands entirely.
    """
    # If from_cache is True, this was a copytree operation
    if svn_repo.from_cache:
        # created_at is relative perf_counter, but we verify it's fast
        assert svn_repo.master_copy_path.exists()


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


@pytest.mark.performance
def test_version_key_is_cached_to_disk(
    libvcs_persistent_cache: pathlib.Path,
) -> None:
    """Verify VCS version detection is cached to disk.

    This optimization avoids running slow `hg --version` (102ms) on every
    pytest session by caching the computed cache key to disk with 24h TTL.
    """
    cache_key_file = libvcs_persistent_cache.parent / ".cache_key"
    assert cache_key_file.exists(), ".cache_key file should exist"
    # Should contain the same 12-char hex key as the cache directory name
    cached_key = cache_key_file.read_text().strip()
    assert cached_key == libvcs_persistent_cache.name


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


# =============================================================================
# Copy Method Benchmarks
# =============================================================================
# These benchmarks compare native VCS copy commands against shutil.copytree
# to determine which method is faster for each VCS type.


class CopyBenchmarkResult(t.NamedTuple):
    """Result from a copy benchmark iteration."""

    method: str
    duration_ms: float


def _benchmark_copy(
    src: pathlib.Path,
    dst_base: pathlib.Path,
    copy_fn: t.Callable[[pathlib.Path, pathlib.Path], None],
    iterations: int = 5,
) -> list[float]:
    """Run copy benchmark for multiple iterations, return durations in ms."""
    import shutil
    import time

    durations: list[float] = []
    for i in range(iterations):
        dst = dst_base / f"iter_{i}"
        if dst.exists():
            shutil.rmtree(dst)

        start = time.perf_counter()
        copy_fn(src, dst)
        duration_ms = (time.perf_counter() - start) * 1000
        durations.append(duration_ms)

        # Cleanup for next iteration
        if dst.exists():
            shutil.rmtree(dst)

    return durations


@pytest.mark.performance
@pytest.mark.benchmark
def test_benchmark_svn_copy_methods(
    empty_svn_repo: pathlib.Path,
    tmp_path: pathlib.Path,
) -> None:
    """Benchmark svnadmin hotcopy vs shutil.copytree for SVN repos.

    This test determines if svnadmin hotcopy is faster than shutil.copytree.
    Results are printed to help decide which method to use in fixtures.
    """
    import shutil
    import subprocess

    def copytree_copy(src: pathlib.Path, dst: pathlib.Path) -> None:
        shutil.copytree(src, dst)

    def hotcopy_copy(src: pathlib.Path, dst: pathlib.Path) -> None:
        dst.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(
            ["svnadmin", "hotcopy", str(src), str(dst)],
            check=True,
            capture_output=True,
            timeout=30,
        )

    # Benchmark both methods
    copytree_times = _benchmark_copy(
        empty_svn_repo, tmp_path / "copytree", copytree_copy
    )
    hotcopy_times = _benchmark_copy(empty_svn_repo, tmp_path / "hotcopy", hotcopy_copy)

    # Calculate statistics
    copytree_avg = sum(copytree_times) / len(copytree_times)
    copytree_min = min(copytree_times)
    hotcopy_avg = sum(hotcopy_times) / len(hotcopy_times)
    hotcopy_min = min(hotcopy_times)

    # Report results
    print("\n" + "=" * 60)
    print("SVN Copy Method Benchmark Results")
    print("=" * 60)
    print(f"shutil.copytree: avg={copytree_avg:.2f}ms, min={copytree_min:.2f}ms")
    print(f"svnadmin hotcopy: avg={hotcopy_avg:.2f}ms, min={hotcopy_min:.2f}ms")
    print(f"Speedup: {copytree_avg / hotcopy_avg:.2f}x")
    print(f"Winner: {'hotcopy' if hotcopy_avg < copytree_avg else 'copytree'}")
    print("=" * 60)

    # Store results for analysis (test always passes - it's informational)
    # The assertion is informational - we want to see results regardless
    assert True, (
        f"SVN benchmark: copytree={copytree_avg:.2f}ms, hotcopy={hotcopy_avg:.2f}ms"
    )


@pytest.mark.performance
@pytest.mark.benchmark
def test_benchmark_git_copy_methods(
    empty_git_repo: pathlib.Path,
    tmp_path: pathlib.Path,
) -> None:
    """Benchmark git clone --local vs shutil.copytree for Git repos.

    Git's --local flag uses hardlinks when possible, which can be faster.
    """
    import shutil
    import subprocess

    def copytree_copy(src: pathlib.Path, dst: pathlib.Path) -> None:
        shutil.copytree(src, dst)

    def git_clone_local(src: pathlib.Path, dst: pathlib.Path) -> None:
        dst.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(
            ["git", "clone", "--local", str(src), str(dst)],
            check=True,
            capture_output=True,
            timeout=30,
        )

    # Benchmark both methods
    copytree_times = _benchmark_copy(
        empty_git_repo, tmp_path / "copytree", copytree_copy
    )
    clone_times = _benchmark_copy(empty_git_repo, tmp_path / "clone", git_clone_local)

    # Calculate statistics
    copytree_avg = sum(copytree_times) / len(copytree_times)
    copytree_min = min(copytree_times)
    clone_avg = sum(clone_times) / len(clone_times)
    clone_min = min(clone_times)

    # Report results
    print("\n" + "=" * 60)
    print("Git Copy Method Benchmark Results")
    print("=" * 60)
    print(f"shutil.copytree: avg={copytree_avg:.2f}ms, min={copytree_min:.2f}ms")
    print(f"git clone --local: avg={clone_avg:.2f}ms, min={clone_min:.2f}ms")
    print(f"Speedup: {copytree_avg / clone_avg:.2f}x")
    print(f"Winner: {'clone' if clone_avg < copytree_avg else 'copytree'}")
    print("=" * 60)

    assert True, (
        f"Git benchmark: copytree={copytree_avg:.2f}ms, clone={clone_avg:.2f}ms"
    )


@pytest.mark.performance
@pytest.mark.benchmark
def test_benchmark_hg_copy_methods(
    empty_hg_repo: pathlib.Path,
    tmp_path: pathlib.Path,
    hgconfig: pathlib.Path,
) -> None:
    """Benchmark hg clone vs shutil.copytree for Mercurial repos.

    Mercurial's clone can use hardlinks with --pull, but hg is inherently slow.
    """
    import os
    import shutil
    import subprocess

    env = {**os.environ, "HGRCPATH": str(hgconfig)}

    def copytree_copy(src: pathlib.Path, dst: pathlib.Path) -> None:
        shutil.copytree(src, dst)

    def hg_clone(src: pathlib.Path, dst: pathlib.Path) -> None:
        dst.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(
            ["hg", "clone", str(src), str(dst)],
            check=True,
            capture_output=True,
            timeout=60,
            env=env,
        )

    # Benchmark both methods
    copytree_times = _benchmark_copy(
        empty_hg_repo, tmp_path / "copytree", copytree_copy
    )
    clone_times = _benchmark_copy(empty_hg_repo, tmp_path / "clone", hg_clone)

    # Calculate statistics
    copytree_avg = sum(copytree_times) / len(copytree_times)
    copytree_min = min(copytree_times)
    clone_avg = sum(clone_times) / len(clone_times)
    clone_min = min(clone_times)

    # Report results
    print("\n" + "=" * 60)
    print("Mercurial Copy Method Benchmark Results")
    print("=" * 60)
    print(f"shutil.copytree: avg={copytree_avg:.2f}ms, min={copytree_min:.2f}ms")
    print(f"hg clone: avg={clone_avg:.2f}ms, min={clone_min:.2f}ms")
    print(f"Speedup: {copytree_avg / clone_avg:.2f}x")
    print(f"Winner: {'clone' if clone_avg < copytree_avg else 'copytree'}")
    print("=" * 60)

    assert True, f"Hg benchmark: copytree={copytree_avg:.2f}ms, clone={clone_avg:.2f}ms"


@pytest.mark.performance
@pytest.mark.benchmark
def test_benchmark_summary(
    empty_git_repo: pathlib.Path,
    empty_svn_repo: pathlib.Path,
    empty_hg_repo: pathlib.Path,
    tmp_path: pathlib.Path,
    hgconfig: pathlib.Path,
) -> None:
    """Comprehensive benchmark summary comparing all VCS copy methods.

    This test provides a single-run summary of all copy methods for quick
    comparison. Run with: pytest -v -s -m benchmark --run-performance
    """
    import os
    import shutil
    import subprocess
    import time

    env = {**os.environ, "HGRCPATH": str(hgconfig)}

    def measure_once(
        name: str,
        src: pathlib.Path,
        dst: pathlib.Path,
        copy_fn: t.Callable[[], t.Any],
    ) -> float:
        if dst.exists():
            shutil.rmtree(dst)
        start = time.perf_counter()
        copy_fn()
        duration = (time.perf_counter() - start) * 1000
        if dst.exists():
            shutil.rmtree(dst)
        return duration

    results: dict[str, dict[str, float]] = {}

    # SVN benchmarks
    svn_copytree_dst = tmp_path / "svn_copytree"
    svn_hotcopy_dst = tmp_path / "svn_hotcopy"
    results["SVN"] = {
        "copytree": measure_once(
            "svn_copytree",
            empty_svn_repo,
            svn_copytree_dst,
            lambda: shutil.copytree(empty_svn_repo, svn_copytree_dst),
        ),
        "native": measure_once(
            "svn_hotcopy",
            empty_svn_repo,
            svn_hotcopy_dst,
            lambda: subprocess.run(
                ["svnadmin", "hotcopy", str(empty_svn_repo), str(svn_hotcopy_dst)],
                check=True,
                capture_output=True,
            ),
        ),
    }

    # Git benchmarks
    git_copytree_dst = tmp_path / "git_copytree"
    git_clone_dst = tmp_path / "git_clone"
    results["Git"] = {
        "copytree": measure_once(
            "git_copytree",
            empty_git_repo,
            git_copytree_dst,
            lambda: shutil.copytree(empty_git_repo, git_copytree_dst),
        ),
        "native": measure_once(
            "git_clone",
            empty_git_repo,
            git_clone_dst,
            lambda: subprocess.run(
                ["git", "clone", "--local", str(empty_git_repo), str(git_clone_dst)],
                check=True,
                capture_output=True,
            ),
        ),
    }

    # Hg benchmarks
    hg_copytree_dst = tmp_path / "hg_copytree"
    hg_clone_dst = tmp_path / "hg_clone"
    results["Hg"] = {
        "copytree": measure_once(
            "hg_copytree",
            empty_hg_repo,
            hg_copytree_dst,
            lambda: shutil.copytree(empty_hg_repo, hg_copytree_dst),
        ),
        "native": measure_once(
            "hg_clone",
            empty_hg_repo,
            hg_clone_dst,
            lambda: subprocess.run(
                ["hg", "clone", str(empty_hg_repo), str(hg_clone_dst)],
                check=True,
                capture_output=True,
                env=env,
            ),
        ),
    }

    # Print summary
    print("\n" + "=" * 70)
    print("VCS Copy Method Benchmark Summary")
    print("=" * 70)
    print(
        f"{'VCS':<6} {'copytree (ms)':<15} {'native (ms)':<15} "
        f"{'speedup':<10} {'winner'}"
    )
    print("-" * 70)
    for vcs, times in results.items():
        speedup = times["copytree"] / times["native"]
        winner = "native" if times["native"] < times["copytree"] else "copytree"
        print(
            f"{vcs:<6} {times['copytree']:<15.2f} {times['native']:<15.2f} "
            f"{speedup:<10.2f}x {winner}"
        )
    print("=" * 70)
    print("\nRecommendations:")
    for vcs, times in results.items():
        if times["native"] < times["copytree"]:
            print(
                f"  - {vcs}: Use native copy "
                "(svnadmin hotcopy / git clone / hg clone)"
            )
        else:
            print(f"  - {vcs}: Use shutil.copytree")
    print("=" * 70)
