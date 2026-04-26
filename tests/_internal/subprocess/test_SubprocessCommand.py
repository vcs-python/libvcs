"""Tests for SubprocessCommand."""

from __future__ import annotations

import subprocess
import typing as t

import pytest

from libvcs._internal.subprocess import SubprocessCommand
from libvcs._internal.types import StrOrBytesPath

if t.TYPE_CHECKING:
    import pathlib


CmdArgs = StrOrBytesPath | t.Sequence[StrOrBytesPath]
Kwargs = dict[str, t.Any]


def idfn(val: CmdArgs | Kwargs | SubprocessCommand | None) -> str:
    """Test ID naming function for SubprocessCommand py.test parametrize."""
    if isinstance(val, list):
        if len(val):
            return str(val[0])
        return "[]]"

    return str(val)


@pytest.mark.parametrize(
    ("cmd_args", "kwargs", "expected_result"),
    [
        ("ls", {}, SubprocessCommand("ls")),
        (["ls", "-l"], {}, SubprocessCommand(["ls", "-l"])),
        (None, {"args": ["ls", "-l"]}, SubprocessCommand(["ls", "-l"])),
        ("ls -l", {"shell": True}, SubprocessCommand("ls -l", shell=True)),
        (
            None,
            {"args": "ls -l", "shell": True},
            SubprocessCommand("ls -l", shell=True),
        ),
        (
            None,
            {"args": ["ls", "-l"], "shell": True},
            SubprocessCommand(["ls", "-l"], shell=True),
        ),
    ],
    ids=idfn,
)
def test_init(
    cmd_args: CmdArgs | None,
    kwargs: Kwargs,
    expected_result: SubprocessCommand,
) -> None:
    """Test SubprocessCommand via list + kwargs, assert attributes."""
    cmd = (
        SubprocessCommand(cmd_args, **kwargs)
        if cmd_args is not None
        else SubprocessCommand(**kwargs)
    )
    assert cmd == expected_result

    # Attributes in cmd should match what's passed in
    for k, v in kwargs.items():
        assert getattr(cmd, k) == v

    proc = cmd.Popen()
    proc.communicate()
    assert proc.returncode == 0


FIXTURES: list[tuple[CmdArgs, Kwargs, SubprocessCommand]] = [
    ("ls", {}, SubprocessCommand("ls")),
    (["ls", "-l"], {}, SubprocessCommand(["ls", "-l"])),
]


@pytest.mark.parametrize(
    ("cmd_args", "kwargs", "expected_result"),
    FIXTURES,
    ids=idfn,
)
def test_init_and_Popen(
    cmd_args: CmdArgs,
    kwargs: Kwargs,
    expected_result: SubprocessCommand,
) -> None:
    """Test SubprocessCommand with Popen."""
    cmd = SubprocessCommand(cmd_args, **kwargs)
    assert cmd == expected_result

    cmd_proc = cmd.Popen()
    cmd_proc.communicate()
    assert cmd_proc.returncode == 0

    proc = subprocess.Popen(cmd_args, **kwargs)
    proc.communicate()
    assert proc.returncode == 0


@pytest.mark.parametrize(
    ("cmd_args", "kwargs", "expected_result"),
    FIXTURES,
    ids=idfn,
)
def test_init_and_Popen_run(
    cmd_args: CmdArgs,
    kwargs: Kwargs,
    expected_result: SubprocessCommand,
) -> None:
    """Test SubprocessCommand with run."""
    cmd = SubprocessCommand(cmd_args, **kwargs)
    assert cmd == expected_result

    cmd_proc = cmd.Popen()
    cmd_proc.communicate()
    assert cmd_proc.returncode == 0

    proc = subprocess.run(cmd_args, **kwargs, check=False)
    assert proc.returncode == 0


@pytest.mark.parametrize(
    ("cmd_args", "kwargs", "expected_result"),
    FIXTURES,
    ids=idfn,
)
def test_init_and_check_call(
    cmd_args: CmdArgs,
    kwargs: Kwargs,
    expected_result: SubprocessCommand,
) -> None:
    """Test SubprocessCommand with Popen.check_call."""
    cmd = SubprocessCommand(cmd_args, **kwargs)
    assert cmd == expected_result

    return_code = cmd.check_call()
    assert return_code == 0

    proc = subprocess.check_call(cmd_args, **kwargs)
    assert proc == return_code


@pytest.mark.parametrize(
    ("cmd_args", "kwargs", "expected_result"),
    FIXTURES,
)
def test_init_and_check_output(
    cmd_args: CmdArgs,
    kwargs: Kwargs,
    expected_result: SubprocessCommand,
) -> None:
    """Test SubprocessCommand with Popen.check_output."""
    cmd = SubprocessCommand(cmd_args, **kwargs)
    assert cmd == expected_result

    return_output = cmd.check_output()
    assert isinstance(return_output, bytes)

    proc = subprocess.check_output(cmd_args, **kwargs)
    assert proc == return_output


@pytest.mark.parametrize(
    ("cmd_args", "kwargs", "run_kwargs"),
    [
        ("ls", {}, {}),
        (["ls", "-l"], {}, {}),
        (["ls", "-al"], {}, {"stdout": subprocess.DEVNULL}),
    ],
    ids=idfn,
)
def test_run(
    tmp_path: pathlib.Path,
    cmd_args: CmdArgs,
    kwargs: Kwargs,
    run_kwargs: Kwargs,
) -> None:
    """Test SubprocessCommand.run()."""
    kwargs["cwd"] = tmp_path
    cmd = SubprocessCommand(cmd_args, **kwargs)
    response = cmd.run(**run_kwargs)

    assert response.returncode == 0
