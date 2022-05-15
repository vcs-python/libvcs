import pathlib
import subprocess
from typing import Any

import pytest

from libvcs._internal.subprocess import SubprocessCommand


def idfn(val: Any) -> str:
    if isinstance(val, list):
        if len(val):
            return str(val[0])
        return "[]]"

    return str(val)


@pytest.mark.parametrize(
    "args,kwargs,expected_result",
    [
        [["ls"], {}, SubprocessCommand("ls")],
        [[["ls", "-l"]], {}, SubprocessCommand(["ls", "-l"])],
        [[], {"args": ["ls", "-l"]}, SubprocessCommand(["ls", "-l"])],
        [["ls -l"], {"shell": True}, SubprocessCommand("ls -l", shell=True)],
        [[], {"args": "ls -l", "shell": True}, SubprocessCommand("ls -l", shell=True)],
        [
            [],
            {"args": ["ls", "-l"], "shell": True},
            SubprocessCommand(["ls", "-l"], shell=True),
        ],
    ],
    ids=idfn,
)
def test_init(args: list, kwargs: dict, expected_result: Any):
    """Test SubprocessCommand via list + kwargs, assert attributes"""
    cmd = SubprocessCommand(*args, **kwargs)
    assert cmd == expected_result

    # Attributes in cmd should match whats passed in
    for k, v in kwargs.items():
        assert getattr(cmd, k) == v

    proc = cmd.Popen()
    proc.communicate()
    assert proc.returncode == 0


FIXTURES = [
    [["ls"], {}, SubprocessCommand("ls")],
    [[["ls", "-l"]], {}, SubprocessCommand(["ls", "-l"])],
]


@pytest.mark.parametrize(
    "args,kwargs,expected_result",
    FIXTURES,
    ids=idfn,
)
def test_init_and_Popen(args: list, kwargs: dict, expected_result: Any):
    """Test SubprocessCommand with Popen"""
    cmd = SubprocessCommand(*args, **kwargs)
    assert cmd == expected_result

    cmd_proc = cmd.Popen()
    cmd_proc.communicate()
    assert cmd_proc.returncode == 0

    proc = subprocess.Popen(*args, **kwargs)
    proc.communicate()
    assert proc.returncode == 0


@pytest.mark.parametrize(
    "args,kwargs,expected_result",
    FIXTURES,
    ids=idfn,
)
def test_init_and_Popen_run(args: list, kwargs: dict, expected_result: Any):
    """Test SubprocessCommand with run"""
    cmd = SubprocessCommand(*args, **kwargs)
    assert cmd == expected_result

    cmd_proc = cmd.Popen()
    cmd_proc.communicate()
    assert cmd_proc.returncode == 0

    proc = subprocess.run(*args, **kwargs)
    assert proc.returncode == 0


@pytest.mark.parametrize(
    "args,kwargs,expected_result",
    FIXTURES,
    ids=idfn,
)
def test_init_and_check_call(args: list, kwargs: dict, expected_result: Any):
    """Test SubprocessCommand with Popen.check_call"""
    cmd = SubprocessCommand(*args, **kwargs)
    assert cmd == expected_result

    return_code = cmd.check_call()
    assert return_code == 0

    proc = subprocess.check_call(*args, **kwargs)
    assert proc == return_code


@pytest.mark.parametrize(
    "args,kwargs,expected_result",
    FIXTURES,
)
def test_init_and_check_output(args: list, kwargs: dict, expected_result: Any):
    """Test SubprocessCommand with Popen.check_output"""
    cmd = SubprocessCommand(*args, **kwargs)
    assert cmd == expected_result

    return_output = cmd.check_output()
    assert isinstance(return_output, bytes)

    proc = subprocess.check_output(*args, **kwargs)
    assert proc == return_output


@pytest.mark.parametrize(
    "args,kwargs,run_kwargs",
    [
        [["ls"], {}, {}],
        [[["ls", "-l"]], {}, {}],
        [[["ls", "-al"]], {}, {"stdout": subprocess.DEVNULL}],
    ],
    ids=idfn,
)
def test_run(tmp_path: pathlib.Path, args: list, kwargs: dict, run_kwargs: dict):
    cmd = SubprocessCommand(*args, cwd=tmp_path, **kwargs)
    response = cmd.run(**run_kwargs)

    assert response.returncode == 0
