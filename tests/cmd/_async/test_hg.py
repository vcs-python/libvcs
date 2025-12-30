"""Tests for libvcs.cmd._async.hg."""

from __future__ import annotations

import typing as t
from pathlib import Path

import pytest

from libvcs.cmd._async.hg import AsyncHg
from libvcs.pytest_plugin import CreateRepoPytestFixtureFn


class RunFixture(t.NamedTuple):
    """Test fixture for AsyncHg.run()."""

    test_id: str
    args: list[str]
    kwargs: dict[str, t.Any]
    expected_in_output: str | None


RUN_FIXTURES = [
    RunFixture(
        test_id="version",
        args=["version"],
        kwargs={},
        expected_in_output="Mercurial",
    ),
    RunFixture(
        test_id="help_short",
        args=["--help"],
        kwargs={},
        expected_in_output="Mercurial",
    ),
]


class TestAsyncHg:
    """Tests for AsyncHg class."""

    def test_init(self, tmp_path: Path) -> None:
        """Test AsyncHg initialization."""
        hg = AsyncHg(path=tmp_path)
        assert hg.path == tmp_path
        assert hg.progress_callback is None

    def test_repr(self, tmp_path: Path) -> None:
        """Test AsyncHg repr."""
        hg = AsyncHg(path=tmp_path)
        assert "AsyncHg" in repr(hg)
        assert str(tmp_path) in repr(hg)

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
        """Test AsyncHg.run() with various commands."""
        hg = AsyncHg(path=tmp_path)
        output = await hg.run(args, **kwargs)
        if expected_in_output is not None:
            assert expected_in_output in output


class TestAsyncHgClone:
    """Tests for AsyncHg.clone()."""

    @pytest.mark.asyncio
    async def test_clone_basic(
        self,
        tmp_path: Path,
        create_hg_remote_repo: CreateRepoPytestFixtureFn,
    ) -> None:
        """Test basic clone operation."""
        remote_repo = create_hg_remote_repo()
        repo_path = tmp_path / "cloned_repo"

        hg = AsyncHg(path=repo_path)
        await hg.clone(url=f"file://{remote_repo}")

        assert repo_path.exists()
        assert (repo_path / ".hg").exists()

    @pytest.mark.asyncio
    async def test_clone_quiet(
        self,
        tmp_path: Path,
        create_hg_remote_repo: CreateRepoPytestFixtureFn,
    ) -> None:
        """Test clone with quiet flag."""
        remote_repo = create_hg_remote_repo()
        repo_path = tmp_path / "quiet_repo"

        hg = AsyncHg(path=repo_path)
        await hg.clone(url=f"file://{remote_repo}", quiet=True)

        assert repo_path.exists()

    @pytest.mark.asyncio
    async def test_clone_no_update(
        self,
        tmp_path: Path,
        create_hg_remote_repo: CreateRepoPytestFixtureFn,
    ) -> None:
        """Test clone with no_update flag."""
        remote_repo = create_hg_remote_repo()
        repo_path = tmp_path / "noupdate_repo"

        hg = AsyncHg(path=repo_path)
        await hg.clone(url=f"file://{remote_repo}", no_update=True)

        assert repo_path.exists()
        assert (repo_path / ".hg").exists()


class TestAsyncHgUpdate:
    """Tests for AsyncHg.update()."""

    @pytest.mark.asyncio
    async def test_update_basic(
        self,
        tmp_path: Path,
        create_hg_remote_repo: CreateRepoPytestFixtureFn,
    ) -> None:
        """Test basic update operation."""
        remote_repo = create_hg_remote_repo()
        repo_path = tmp_path / "update_repo"

        hg = AsyncHg(path=repo_path)
        await hg.clone(url=f"file://{remote_repo}")
        output = await hg.update()

        assert "files" in output or "0 files" in output


class TestAsyncHgPull:
    """Tests for AsyncHg.pull()."""

    @pytest.mark.asyncio
    async def test_pull_basic(
        self,
        tmp_path: Path,
        create_hg_remote_repo: CreateRepoPytestFixtureFn,
    ) -> None:
        """Test basic pull operation."""
        remote_repo = create_hg_remote_repo()
        repo_path = tmp_path / "pull_repo"

        hg = AsyncHg(path=repo_path)
        await hg.clone(url=f"file://{remote_repo}")
        output = await hg.pull()

        assert "no changes found" in output or "pulling from" in output

    @pytest.mark.asyncio
    async def test_pull_with_update(
        self,
        tmp_path: Path,
        create_hg_remote_repo: CreateRepoPytestFixtureFn,
    ) -> None:
        """Test pull with update flag."""
        remote_repo = create_hg_remote_repo()
        repo_path = tmp_path / "pull_update_repo"

        hg = AsyncHg(path=repo_path)
        await hg.clone(url=f"file://{remote_repo}")
        output = await hg.pull(update=True)

        assert output is not None
