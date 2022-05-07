import pathlib
import subprocess
import sys
import textwrap
from typing import Any
from unittest import mock

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

    # Attributes in cmd should match what's passed in
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
    kwargs["cwd"] = tmp_path
    cmd = SubprocessCommand(*args, **kwargs)
    response = cmd.run(**run_kwargs)

    assert response.returncode == 0


@pytest.mark.parametrize(
    "args,kwargs,run_kwargs",
    [
        [
            ["ls"],
            {},
            {},
        ],
        [[["ls", "-l"]], {}, {}],
        [[["ls", "-al"]], {}, {"stdout": subprocess.DEVNULL}],
    ],
    ids=idfn,
)
@mock.patch("subprocess.Popen")
def test_Popen_mock(
    mock_subprocess_popen,
    tmp_path: pathlib.Path,
    args: list,
    kwargs: dict,
    run_kwargs: dict,
    capsys: pytest.LogCaptureFixture,
):
    process_mock = mock.Mock()
    attrs = {"communicate.return_value": ("output", "error"), "returncode": 1}
    process_mock.configure_mock(**attrs)
    mock_subprocess_popen.return_value = process_mock
    cmd = SubprocessCommand(*args, cwd=tmp_path, **kwargs)
    response = cmd.Popen(**run_kwargs)

    assert response.returncode == 1


@pytest.mark.parametrize(
    "args,kwargs,run_kwargs",
    [
        [[["git", "pull", "--progress"]], {}, {}],
    ],
    ids=idfn,
)
@mock.patch("subprocess.Popen")
def test_Popen_git_mock(
    mock_subprocess_popen,
    tmp_path: pathlib.Path,
    args: list,
    kwargs: dict,
    run_kwargs: dict,
    capsys: pytest.LogCaptureFixture,
):
    process_mock = mock.Mock()
    attrs = {"communicate.return_value": ("output", "error"), "returncode": 1}
    process_mock.configure_mock(**attrs)
    mock_subprocess_popen.return_value = process_mock
    cmd = SubprocessCommand(*args, cwd=tmp_path, **kwargs)
    response = cmd.Popen(**run_kwargs)

    stdout, stderr = response.communicate()

    assert response.returncode == 1
    assert stdout == "output"
    assert stderr == "error"


CODE = (
    textwrap.dedent(
        r"""
        import sys
        import time
        size = 10
        for i in range(10):
            time.sleep(.01)
            sys.stderr.write(
                '[' + "#" * i + "." * (size-i) +  ']' + f' {i}/{size}' + '\n'
            )
            sys.stderr.flush()
"""
    )
    .strip("\n")
    .lstrip()
)


def test_Popen_stderr(
    tmp_path: pathlib.Path,
    capsys: pytest.LogCaptureFixture,
):
    cmd = SubprocessCommand(
        [
            sys.executable,
            "-c",
            CODE,
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=tmp_path,
    )
    response = cmd.Popen()
    while response.poll() is None:
        stdout, stderr = response.communicate()

        assert stdout != "output"
        assert stderr != "1"
    assert response.returncode == 0


def test_CaptureStderrMixin(
    tmp_path: pathlib.Path,
    capsys: pytest.LogCaptureFixture,
):
    cmd = SubprocessCommand(
        [
            sys.executable,
            "-c",
            CODE,
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=tmp_path,
    )
    response = cmd.Popen()
    while response.poll() is None:
        line = response.stderr.readline().decode("utf-8").strip()
        if line:
            assert line.startswith("[")
    assert response.returncode == 0


def test_CaptureStderrMixin_error(
    tmp_path: pathlib.Path,
    capsys: pytest.LogCaptureFixture,
):
    cmd = SubprocessCommand(
        [
            sys.executable,
            "-c",
            CODE
            + textwrap.dedent(
                """
       sys.exit("FATAL")
            """
            ),
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=tmp_path,
    )
    response = cmd.Popen()
    while response.poll() is None:
        line = response.stderr.readline().decode("utf-8").strip()
        if line:
            assert line.startswith("[") or line == "FATAL"

    assert response.returncode == 1
