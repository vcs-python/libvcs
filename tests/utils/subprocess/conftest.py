import pathlib

import pytest


@pytest.fixture(autouse=True)
def cwd_default(monkeypatch: pytest.MonkeyPatch, tmp_path: pathlib.Path):
    monkeypatch.chdir(tmp_path)
