import pathlib
import shutil
import textwrap

import pytest

from libvcs.pytest_plugin import CreateProjectCallbackFixtureProtocol


@pytest.mark.skipif(not shutil.which("git"), reason="git is not available")
def test_create_git_remote_repo(
    create_git_remote_repo: CreateProjectCallbackFixtureProtocol,
    tmp_path: pathlib.Path,
    projects_path: pathlib.Path,
) -> None:
    git_remote_1 = create_git_remote_repo()
    git_remote_2 = create_git_remote_repo()

    assert git_remote_1 != git_remote_2


@pytest.mark.skipif(not shutil.which("svn"), reason="svn is not available")
def test_create_svn_remote_repo(
    create_svn_remote_repo: CreateProjectCallbackFixtureProtocol,
    tmp_path: pathlib.Path,
    projects_path: pathlib.Path,
) -> None:
    svn_remote_1 = create_svn_remote_repo()
    svn_remote_2 = create_svn_remote_repo()

    assert svn_remote_1 != svn_remote_2


def test_plugin(
    pytester: pytest.Pytester,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Initialize variables
    pytester.plugins = ["pytest_plugin"]
    pytester.makefile(
        ".ini",
        pytest=textwrap.dedent(
            """
[pytest]
addopts=-vv
        """.strip()
        ),
    )
    pytester.makeconftest(
        textwrap.dedent(
            r"""
import pathlib
import pytest

@pytest.fixture(autouse=True)
def setup(
    request: pytest.FixtureRequest,
    gitconfig: pathlib.Path,
    set_home: pathlib.Path,
) -> None:
    pass
    """
        )
    )
    tests_path = pytester.path / "tests"
    files = {
        "example.py": textwrap.dedent(
            """
import pathlib

from libvcs.sync.git import GitSync
from libvcs.pytest_plugin import CreateProjectCallbackFixtureProtocol

def test_repo_git_remote_checkout(
    create_git_remote_repo: CreateProjectCallbackFixtureProtocol,
    tmp_path: pathlib.Path,
    projects_path: pathlib.Path,
) -> None:
    git_server = create_git_remote_repo()
    git_repo_checkout_dir = projects_path / "my_git_checkout"
    git_repo = GitSync(dir=str(git_repo_checkout_dir), url=f"file://{git_server!s}")

    git_repo.obtain()
    git_repo.update_repo()

    assert git_repo.get_revision() == "initial"

    assert git_repo_checkout_dir.exists()
    assert pathlib.Path(git_repo_checkout_dir / ".git").exists()
        """
        )
    }
    first_test_key = list(files.keys())[0]
    first_test_filename = str(tests_path / first_test_key)

    # Setup: Files
    tests_path.mkdir()
    for file_name, text in files.items():
        test_file = tests_path / file_name
        test_file.write_text(
            text,
            encoding="utf-8",
        )

    # Test
    result = pytester.runpytest(str(first_test_filename))
    result.assert_outcomes(passed=1)
