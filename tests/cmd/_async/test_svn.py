"""Tests for libvcs.cmd._async.svn."""

from __future__ import annotations

import shutil
import typing as t
from pathlib import Path

import pytest

from libvcs.cmd._async.svn import AsyncSvn
from libvcs.pytest_plugin import CreateRepoPytestFixtureFn

if not shutil.which("svn"):
    pytestmark = pytest.mark.skip(reason="svn is not available")


class RunFixture(t.NamedTuple):
    """Test fixture for AsyncSvn.run()."""

    test_id: str
    args: list[str]
    kwargs: dict[str, t.Any]
    expected_in_output: str | None


RUN_FIXTURES = [
    RunFixture(
        test_id="version",
        args=["--version"],
        kwargs={},
        expected_in_output="svn",
    ),
    RunFixture(
        test_id="help_short",
        args=["help"],
        kwargs={},
        expected_in_output="usage",
    ),
]


class TestAsyncSvn:
    """Tests for AsyncSvn class."""

    def test_init(self, tmp_path: Path) -> None:
        """Test AsyncSvn initialization."""
        svn = AsyncSvn(path=tmp_path)
        assert svn.path == tmp_path
        assert svn.progress_callback is None

    def test_repr(self, tmp_path: Path) -> None:
        """Test AsyncSvn repr."""
        svn = AsyncSvn(path=tmp_path)
        assert "AsyncSvn" in repr(svn)
        assert str(tmp_path) in repr(svn)

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
        """Test AsyncSvn.run() with various commands."""
        svn = AsyncSvn(path=tmp_path)
        output = await svn.run(args, **kwargs)
        if expected_in_output is not None:
            assert expected_in_output in output.lower()


class TestAsyncSvnCheckout:
    """Tests for AsyncSvn.checkout()."""

    @pytest.mark.asyncio
    async def test_checkout_basic(
        self,
        tmp_path: Path,
        create_svn_remote_repo: CreateRepoPytestFixtureFn,
    ) -> None:
        """Test basic checkout operation."""
        remote_repo = create_svn_remote_repo()
        repo_path = tmp_path / "checked_out_repo"

        svn = AsyncSvn(path=repo_path)
        await svn.checkout(url=f"file://{remote_repo}")

        assert repo_path.exists()
        assert (repo_path / ".svn").exists()

    @pytest.mark.asyncio
    async def test_checkout_quiet(
        self,
        tmp_path: Path,
        create_svn_remote_repo: CreateRepoPytestFixtureFn,
    ) -> None:
        """Test checkout with quiet flag."""
        remote_repo = create_svn_remote_repo()
        repo_path = tmp_path / "quiet_repo"

        svn = AsyncSvn(path=repo_path)
        await svn.checkout(url=f"file://{remote_repo}", quiet=True)

        assert repo_path.exists()


class TestAsyncSvnUpdate:
    """Tests for AsyncSvn.update()."""

    @pytest.mark.asyncio
    async def test_update_basic(
        self,
        tmp_path: Path,
        create_svn_remote_repo: CreateRepoPytestFixtureFn,
    ) -> None:
        """Test basic update operation."""
        remote_repo = create_svn_remote_repo()
        repo_path = tmp_path / "update_repo"

        svn = AsyncSvn(path=repo_path)
        await svn.checkout(url=f"file://{remote_repo}")
        output = await svn.update()

        assert "revision" in output.lower() or "at revision" in output.lower()


class TestAsyncSvnInfo:
    """Tests for AsyncSvn.info()."""

    @pytest.mark.asyncio
    async def test_info_basic(
        self,
        tmp_path: Path,
        create_svn_remote_repo: CreateRepoPytestFixtureFn,
    ) -> None:
        """Test basic info operation."""
        remote_repo = create_svn_remote_repo()
        repo_path = tmp_path / "info_repo"

        svn = AsyncSvn(path=repo_path)
        await svn.checkout(url=f"file://{remote_repo}")
        output = await svn.info()

        assert "URL:" in output or "url" in output.lower()

    @pytest.mark.asyncio
    async def test_info_xml(
        self,
        tmp_path: Path,
        create_svn_remote_repo: CreateRepoPytestFixtureFn,
    ) -> None:
        """Test info with XML output."""
        remote_repo = create_svn_remote_repo()
        repo_path = tmp_path / "info_xml_repo"

        svn = AsyncSvn(path=repo_path)
        await svn.checkout(url=f"file://{remote_repo}")
        output = await svn.info(xml=True)

        assert "<?xml" in output
        assert "<info>" in output
