import pathlib
from typing import Callable

import pytest

from libvcs._internal.subprocess import SubprocessCommand
from libvcs.cmd import git


@pytest.mark.parametrize("dir_type", [str, pathlib.Path])
def test_run(dir_type: Callable, tmp_path: pathlib.Path):
    repo = git.Git(dir=dir_type(tmp_path))

    assert repo.dir == tmp_path


@pytest.mark.parametrize("dir_type", [str, pathlib.Path])
def test_run_deferred(dir_type: Callable, tmp_path: pathlib.Path):
    class GitDeferred(git.Git):
        def run(self, args, **kwargs):
            return SubprocessCommand(["git", *args], **kwargs)

    g = GitDeferred(dir=dir_type(tmp_path))
    cmd = g.run(["help"])

    assert g.dir == tmp_path
    assert cmd.args == ["git", "help"]

    assert cmd.run(capture_output=True, text=True).stdout.startswith(
        "usage: git [--version] [--help] [-C <path>]"
    )
