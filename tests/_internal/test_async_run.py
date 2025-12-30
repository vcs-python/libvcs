"""Tests for libvcs._internal.async_run."""

from __future__ import annotations

import asyncio
import datetime
import typing as t
from pathlib import Path

import pytest

from libvcs._internal.async_run import (
    AsyncProgressCallbackProtocol,
    async_run,
    wrap_sync_callback,
)
from libvcs.exc import CommandError, CommandTimeoutError


class RunFixture(t.NamedTuple):
    """Test fixture for async_run()."""

    test_id: str
    args: list[str]
    kwargs: dict[str, t.Any]
    expected_output: str | None
    should_raise: bool


RUN_FIXTURES = [
    RunFixture(
        test_id="echo_simple",
        args=["echo", "hello"],
        kwargs={},
        expected_output="hello",
        should_raise=False,
    ),
    RunFixture(
        test_id="echo_multiline",
        args=["echo", "line1\nline2"],
        kwargs={},
        expected_output="line1\nline2",
        should_raise=False,
    ),
    RunFixture(
        test_id="true_command",
        args=["true"],
        kwargs={},
        expected_output="",
        should_raise=False,
    ),
    RunFixture(
        test_id="false_no_check",
        args=["false"],
        kwargs={"check_returncode": False},
        expected_output="",
        should_raise=False,
    ),
    RunFixture(
        test_id="false_with_check",
        args=["false"],
        kwargs={"check_returncode": True},
        expected_output=None,
        should_raise=True,
    ),
]


class TestAsyncRun:
    """Tests for async_run function."""

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
        expected_output: str | None,
        should_raise: bool,
    ) -> None:
        """Test async_run() with various commands."""
        if should_raise:
            with pytest.raises(CommandError):
                await async_run(args, **kwargs)
        else:
            output = await async_run(args, **kwargs)
            if expected_output is not None:
                assert output == expected_output

    @pytest.mark.asyncio
    async def test_run_with_cwd(self, tmp_path: Path) -> None:
        """Test async_run() uses specified working directory."""
        output = await async_run(["pwd"], cwd=tmp_path)
        assert output == str(tmp_path)

    @pytest.mark.asyncio
    async def test_run_with_timeout(self) -> None:
        """Test async_run() respects timeout."""
        with pytest.raises(CommandTimeoutError):
            await async_run(["sleep", "10"], timeout=0.1)

    @pytest.mark.asyncio
    async def test_run_timeout_error_attributes(self) -> None:
        """Test CommandTimeoutError has expected attributes."""
        with pytest.raises(CommandTimeoutError) as exc_info:
            await async_run(["sleep", "10"], timeout=0.1)

        assert exc_info.value.returncode == -1
        assert "timed out" in exc_info.value.output

    @pytest.mark.asyncio
    async def test_run_command_error_attributes(self) -> None:
        """Test CommandError has expected attributes."""
        with pytest.raises(CommandError) as exc_info:
            await async_run(["false"], check_returncode=True)

        assert exc_info.value.returncode == 1

    @pytest.mark.asyncio
    async def test_run_with_callback(self) -> None:
        """Test async_run() calls progress callback."""
        progress_output: list[str] = []
        timestamps: list[datetime.datetime] = []

        async def callback(output: str, timestamp: datetime.datetime) -> None:
            progress_output.append(output)
            timestamps.append(timestamp)

        # Use a command that writes to stderr
        await async_run(
            ["sh", "-c", "echo stderr_line >&2"],
            callback=callback,
            check_returncode=True,
        )

        # Should have received stderr output + final \r
        assert len(progress_output) >= 1
        assert any("stderr_line" in p for p in progress_output)
        # Final \r is sent
        assert progress_output[-1] == "\r"

    @pytest.mark.asyncio
    async def test_run_callback_receives_timestamps(self) -> None:
        """Test callback receives valid datetime timestamps."""
        timestamps: list[datetime.datetime] = []

        async def callback(output: str, timestamp: datetime.datetime) -> None:
            timestamps.append(timestamp)

        await async_run(
            ["sh", "-c", "echo line >&2"],
            callback=callback,
        )

        assert len(timestamps) >= 1
        for ts in timestamps:
            assert isinstance(ts, datetime.datetime)

    @pytest.mark.asyncio
    async def test_run_stderr_on_error(self) -> None:
        """Test stderr content is returned on command error."""
        output = await async_run(
            ["sh", "-c", "echo error_msg >&2; exit 1"],
            check_returncode=False,
        )
        assert "error_msg" in output

    @pytest.mark.asyncio
    async def test_run_concurrent(self) -> None:
        """Test running multiple commands concurrently."""

        async def run_echo(i: int) -> str:
            return await async_run(["echo", str(i)])

        results = await asyncio.gather(*[run_echo(i) for i in range(5)])

        assert len(results) == 5
        for i, result in enumerate(results):
            assert result == str(i)


class TestWrapSyncCallback:
    """Tests for wrap_sync_callback helper."""

    @pytest.mark.asyncio
    async def test_wrap_sync_callback(self) -> None:
        """Test wrap_sync_callback creates working async wrapper."""
        calls: list[tuple[str, datetime.datetime]] = []

        def sync_cb(output: str, timestamp: datetime.datetime) -> None:
            calls.append((output, timestamp))

        async_cb = wrap_sync_callback(sync_cb)

        # Verify it's a valid async callback
        now = datetime.datetime.now()
        await async_cb("test", now)

        assert len(calls) == 1
        assert calls[0] == ("test", now)

    @pytest.mark.asyncio
    async def test_wrap_sync_callback_type(self) -> None:
        """Test wrapped callback conforms to protocol."""

        def sync_cb(output: str, timestamp: datetime.datetime) -> None:
            pass

        async_cb = wrap_sync_callback(sync_cb)

        # Type check: should be usable where AsyncProgressCallbackProtocol expected
        callback: AsyncProgressCallbackProtocol = async_cb
        await callback("test", datetime.datetime.now())


class TestAsyncProgressCallbackProtocol:
    """Tests for AsyncProgressCallbackProtocol."""

    @pytest.mark.asyncio
    async def test_protocol_implementation(self) -> None:
        """Test that a function can implement the protocol."""
        received: list[str] = []

        async def my_callback(output: str, timestamp: datetime.datetime) -> None:
            received.append(output)

        # Use as protocol type
        cb: AsyncProgressCallbackProtocol = my_callback
        await cb("hello", datetime.datetime.now())

        assert received == ["hello"]


class TestArgsToList:
    """Tests for _args_to_list helper."""

    @pytest.mark.asyncio
    async def test_string_arg(self) -> None:
        """Test single string argument."""
        output = await async_run("echo")
        assert output == ""

    @pytest.mark.asyncio
    async def test_path_arg(self, tmp_path: Path) -> None:
        """Test Path argument."""
        test_script = tmp_path / "test.sh"
        test_script.write_text("#!/bin/sh\necho working")
        test_script.chmod(0o755)

        output = await async_run(test_script)
        assert output == "working"

    @pytest.mark.asyncio
    async def test_bytes_arg(self) -> None:
        """Test bytes argument."""
        output = await async_run([b"echo", b"bytes_test"])
        assert output == "bytes_test"
