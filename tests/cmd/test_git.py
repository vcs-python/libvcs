import pathlib
from typing import Callable

import pytest

from libvcs.cmd import git


@pytest.mark.parametrize("dir_type", [str, pathlib.Path])
def test_run(dir_type: Callable, tmp_path: pathlib.Path):
    repo = git.Git(dir=dir_type(tmp_path))

    assert repo.dir == tmp_path
