"""Tests for libvcs.cmd.git."""
import pathlib
from typing import Any, Callable, Union

import pytest

from libvcs.cmd import git


@pytest.mark.parametrize("path_type", [str, pathlib.Path])
def test_git_constructor(
    path_type: Callable[[Union[str, pathlib.Path]], Any],
    tmp_path: pathlib.Path,
) -> None:
    """Test Git constructor."""
    repo = git.Git(path=path_type(tmp_path))

    assert repo.path == tmp_path
