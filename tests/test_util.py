import pathlib

import pytest

from libvcs.util import mkdir_p, which


def test_mkdir_p(tmp_path: pathlib.Path):
    path = tmp_path / "file"
    path.touch()

    with pytest.raises(Exception) as excinfo:
        mkdir_p(path)
    excinfo.match(r"Could not create directory %s" % path)

    # already exists is a noop
    mkdir_p(tmp_path)


def test_which_no_hg_found(monkeypatch):
    monkeypatch.setenv("PATH", "/")
    which("hg")
    which("hg", "/")
