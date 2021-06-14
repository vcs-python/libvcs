import pytest

from libvcs.util import mkdir_p, which


def test_mkdir_p(tmpdir):
    path = tmpdir.join('file').ensure()

    with pytest.raises(Exception) as excinfo:
        mkdir_p(str(path))
    excinfo.match(r'Could not create directory %s' % path)

    # already exists is a noop
    mkdir_p(str(tmpdir))


def test_which_no_hg_found(monkeypatch):
    monkeypatch.setenv(str("PATH"), str("/"))
    which('hg')
    which('hg', '/')
