"""Tests for libvcs._internal.async_subprocess."""

from __future__ import annotations

import asyncio
import subprocess
import typing as t
from pathlib import Path

import pytest

from libvcs._internal.async_subprocess import (
    AsyncCompletedProcess,
    AsyncSubprocessCommand,
)


class RunFixture(t.NamedTuple):
    """Test fixture for AsyncSubprocessCommand.run()."""

    test_id: str
    args: list[str]
    kwargs: dict[str, t.Any]
    expected_stdout: str | None
    expected_returncode: int


RUN_FIXTURES = [
    RunFixture(
        test_id="echo_text",
        args=["echo", "hello"],
        kwargs={"text": True},
        expected_stdout="hello\n",
        expected_returncode=0,
    ),
    RunFixture(
        test_id="echo_bytes",
        args=["echo", "hello"],
        kwargs={"text": False},
        expected_stdout=None,  # bytes comparison handled separately
        expected_returncode=0,
    ),
    RunFixture(
        test_id="true_command",
        args=["true"],
        kwargs={},
        expected_stdout=None,
        expected_returncode=0,
    ),
    RunFixture(
        test_id="false_command",
        args=["false"],
        kwargs={"check": False},
        expected_stdout=None,
        expected_returncode=1,
    ),
]


class TestAsyncCompletedProcess:
    """Tests for AsyncCompletedProcess dataclass."""

    def test_init(self) -> None:
        """Test basic initialization."""
        result = AsyncCompletedProcess(
            args=["echo", "test"],
            returncode=0,
            stdout="test\n",
            stderr="",
        )
        assert result.args == ["echo", "test"]
        assert result.returncode == 0
        assert result.stdout == "test\n"
        assert result.stderr == ""

    def test_check_returncode_success(self) -> None:
        """Test check_returncode with zero exit code."""
        result = AsyncCompletedProcess(
            args=["true"],
            returncode=0,
        )
        # Should not raise
        result.check_returncode()

    def test_check_returncode_failure(self) -> None:
        """Test check_returncode with non-zero exit code."""
        result = AsyncCompletedProcess(
            args=["false"],
            returncode=1,
            stdout="",
            stderr="error",
        )
        with pytest.raises(subprocess.CalledProcessError) as exc_info:
            result.check_returncode()
        assert exc_info.value.returncode == 1
        assert exc_info.value.cmd == ["false"]


class TestAsyncSubprocessCommand:
    """Tests for AsyncSubprocessCommand."""

    def test_init(self) -> None:
        """Test basic initialization."""
        cmd = AsyncSubprocessCommand(args=["echo", "hello"])
        assert cmd.args == ["echo", "hello"]
        assert cmd.cwd is None
        assert cmd.env is None

    def test_init_with_cwd(self, tmp_path: Path) -> None:
        """Test initialization with working directory."""
        cmd = AsyncSubprocessCommand(args=["pwd"], cwd=tmp_path)
        assert cmd.cwd == tmp_path

    def test_args_as_list_sequence(self) -> None:
        """Test _args_as_list with sequence of strings."""
        cmd = AsyncSubprocessCommand(args=["echo", "hello", "world"])
        assert cmd._args_as_list() == ["echo", "hello", "world"]

    def test_args_as_list_single_string(self) -> None:
        """Test _args_as_list with single string."""
        cmd = AsyncSubprocessCommand(args="echo")
        assert cmd._args_as_list() == ["echo"]

    def test_args_as_list_path(self, tmp_path: Path) -> None:
        """Test _args_as_list with Path object."""
        cmd = AsyncSubprocessCommand(args=tmp_path)
        assert cmd._args_as_list() == [str(tmp_path)]

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
        expected_stdout: str | None,
        expected_returncode: int,
    ) -> None:
        """Test run() with various commands."""
        cmd = AsyncSubprocessCommand(args=args)
        result = await cmd.run(**kwargs)

        assert result.returncode == expected_returncode
        if expected_stdout is not None:
            assert result.stdout == expected_stdout

    @pytest.mark.asyncio
    async def test_run_bytes_output(self) -> None:
        """Test run() returns bytes when text=False."""
        cmd = AsyncSubprocessCommand(args=["echo", "hello"])
        result = await cmd.run(text=False)

        assert isinstance(result.stdout, bytes)
        assert result.stdout == b"hello\n"

    @pytest.mark.asyncio
    async def test_run_with_input(self) -> None:
        """Test run() with stdin input."""
        cmd = AsyncSubprocessCommand(args=["cat"])
        result = await cmd.run(input="hello", text=True)

        assert result.stdout == "hello"
        assert result.returncode == 0

    @pytest.mark.asyncio
    async def test_run_with_check_raises(self) -> None:
        """Test run() with check=True raises on non-zero exit."""
        cmd = AsyncSubprocessCommand(args=["false"])
        with pytest.raises(subprocess.CalledProcessError) as exc_info:
            await cmd.run(check=True)
        assert exc_info.value.returncode == 1

    @pytest.mark.asyncio
    async def test_run_with_timeout(self) -> None:
        """Test run() respects timeout."""
        cmd = AsyncSubprocessCommand(args=["sleep", "10"])
        with pytest.raises(asyncio.TimeoutError):
            await cmd.run(timeout=0.1)

    @pytest.mark.asyncio
    async def test_run_with_cwd(self, tmp_path: Path) -> None:
        """Test run() uses specified working directory."""
        cmd = AsyncSubprocessCommand(args=["pwd"], cwd=tmp_path)
        result = await cmd.run(text=True)

        assert result.stdout.strip() == str(tmp_path)

    @pytest.mark.asyncio
    async def test_check_output(self) -> None:
        """Test check_output() returns stdout."""
        cmd = AsyncSubprocessCommand(args=["echo", "hello"])
        output = await cmd.check_output(text=True)

        assert output == "hello\n"

    @pytest.mark.asyncio
    async def test_check_output_raises_on_error(self) -> None:
        """Test check_output() raises on non-zero exit."""
        cmd = AsyncSubprocessCommand(args=["false"])
        with pytest.raises(subprocess.CalledProcessError):
            await cmd.check_output()

    @pytest.mark.asyncio
    async def test_wait(self) -> None:
        """Test wait() returns exit code."""
        cmd = AsyncSubprocessCommand(args=["true"])
        returncode = await cmd.wait()

        assert returncode == 0

    @pytest.mark.asyncio
    async def test_wait_with_timeout(self) -> None:
        """Test wait() respects timeout."""
        cmd = AsyncSubprocessCommand(args=["sleep", "10"])
        with pytest.raises(asyncio.TimeoutError):
            await cmd.wait(timeout=0.1)

    @pytest.mark.asyncio
    async def test_concurrent_commands(self) -> None:
        """Test running multiple commands concurrently."""
        commands = [AsyncSubprocessCommand(args=["echo", str(i)]) for i in range(5)]

        results = await asyncio.gather(*[cmd.run(text=True) for cmd in commands])

        assert len(results) == 5
        for i, result in enumerate(results):
            assert result.stdout.strip() == str(i)
            assert result.returncode == 0
