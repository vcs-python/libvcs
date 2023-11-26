"""Tests for libvcs.cmd.git."""
import pathlib
from typing import Any, Callable, Union

import pytest

from libvcs.cmd import git


@pytest.mark.parametrize("dir_type", [str, pathlib.Path])
def test_git_constructor(
    dir_type: Callable[[Union[str, pathlib.Path]], Any], tmp_path: pathlib.Path
) -> None:
    """Test Git constructor."""
    repo = git.Git(dir=dir_type(tmp_path))

    assert repo.dir == tmp_path
