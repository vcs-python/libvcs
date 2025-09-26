"""Tests for libvcs.cmd.git."""

from __future__ import annotations

import pathlib
import typing as t

import pytest

from libvcs.cmd import git


@pytest.mark.parametrize("path_type", [str, pathlib.Path])
def test_git_constructor(
    path_type: t.Callable[[str | pathlib.Path], t.Any],
    tmp_path: pathlib.Path,
) -> None:
    """Test Git constructor."""
    repo = git.Git(path=path_type(tmp_path))

    assert repo.path == tmp_path


def test_git_init_basic(tmp_path: pathlib.Path) -> None:
    """Test basic git init functionality."""
    repo = git.Git(path=tmp_path)
    result = repo.init()
    assert "Initialized empty Git repository" in result
    assert (tmp_path / ".git").is_dir()


def test_git_init_bare(tmp_path: pathlib.Path) -> None:
    """Test git init with bare repository."""
    repo = git.Git(path=tmp_path)
    result = repo.init(bare=True)
    assert "Initialized empty Git repository" in result
    # Bare repos have files directly in the directory
    assert (tmp_path / "HEAD").exists()


def test_git_init_template(tmp_path: pathlib.Path) -> None:
    """Test git init with template directory."""
    template_dir = tmp_path / "template"
    template_dir.mkdir()
    (template_dir / "hooks").mkdir()
    (template_dir / "hooks" / "pre-commit").write_text("#!/bin/sh\nexit 0\n")

    repo_dir = tmp_path / "repo"
    repo_dir.mkdir()
    repo = git.Git(path=repo_dir)
    result = repo.init(template=str(template_dir))

    assert "Initialized empty Git repository" in result
    assert (repo_dir / ".git" / "hooks" / "pre-commit").exists()


def test_git_init_separate_git_dir(tmp_path: pathlib.Path) -> None:
    """Test git init with separate git directory."""
    repo_dir = tmp_path / "repo"
    git_dir = tmp_path / "git_dir"
    repo_dir.mkdir()
    git_dir.mkdir()

    repo = git.Git(path=repo_dir)
    result = repo.init(separate_git_dir=str(git_dir.absolute()))

    assert "Initialized empty Git repository" in result
    assert git_dir.is_dir()
    assert (git_dir / "HEAD").exists()


def test_git_init_initial_branch(tmp_path: pathlib.Path) -> None:
    """Test git init with custom initial branch name."""
    repo = git.Git(path=tmp_path)
    result = repo.init(branch="main")

    assert "Initialized empty Git repository" in result
    # Check if HEAD points to the correct branch
    head_content = (tmp_path / ".git" / "HEAD").read_text()
    assert "ref: refs/heads/main" in head_content


def test_git_init_shared(tmp_path: pathlib.Path) -> None:
    """Test git init with shared repository settings."""
    repo = git.Git(path=tmp_path)

    # Test boolean shared
    result = repo.init(shared=True)
    assert "Initialized empty shared Git repository" in result

    # Test string shared value
    repo_dir = tmp_path / "shared_group"
    repo_dir.mkdir()
    repo = git.Git(path=repo_dir)
    result = repo.init(shared="group")
    assert "Initialized empty shared Git repository" in result


def test_git_init_quiet(tmp_path: pathlib.Path) -> None:
    """Test git init with quiet flag."""
    repo = git.Git(path=tmp_path)
    result = repo.init(quiet=True)
    # Quiet mode should suppress normal output
    assert result == "" or "Initialized empty Git repository" not in result


def test_git_init_object_format(tmp_path: pathlib.Path) -> None:
    """Test git init with different object formats."""
    repo = git.Git(path=tmp_path)

    # Test with sha1 (default)
    result = repo.init(object_format="sha1")
    assert "Initialized empty Git repository" in result

    # Note: sha256 test is commented out as it might not be supported in all
    # git versions
    # repo_dir = tmp_path / "sha256"
    # repo_dir.mkdir()
    # repo = git.Git(path=repo_dir)
    # result = repo.init(object_format="sha256")
    # assert "Initialized empty Git repository" in result


def test_git_reinit(tmp_path: pathlib.Path) -> None:
    """Test reinitializing an existing repository."""
    repo = git.Git(path=tmp_path)

    # Initial init
    first_result = repo.init()
    assert "Initialized empty Git repository" in first_result

    # Reinit
    second_result = repo.init()
    assert "Reinitialized existing Git repository" in second_result


def test_git_init_validation_errors(tmp_path: pathlib.Path) -> None:
    """Test validation errors in git init."""
    repo = git.Git(path=tmp_path)

    # Test invalid template type
    with pytest.raises(TypeError, match="template must be a string or Path"):
        repo.init(template=123)  # type: ignore

    # Test non-existent template directory
    with pytest.raises(ValueError, match="template directory does not exist"):
        repo.init(template=str(tmp_path / "nonexistent"))

    # Test invalid object format
    with pytest.raises(
        ValueError,
        match="object_format must be either 'sha1' or 'sha256'",
    ):
        repo.init(object_format="invalid")  # type: ignore

    # Test specifying both branch and initial_branch
    with pytest.raises(
        ValueError,
        match="Cannot specify both branch and initial_branch",
    ):
        repo.init(branch="main", initial_branch="master")

    # Test branch name with whitespace
    with pytest.raises(ValueError, match="Branch name cannot contain whitespace"):
        repo.init(branch="main branch")

    # Test invalid shared value
    with pytest.raises(ValueError, match="Invalid shared value"):
        repo.init(shared="invalid")

    # Test invalid octal number for shared
    with pytest.raises(ValueError, match="Invalid shared value"):
        repo.init(shared="8888")  # Invalid octal number

    # Test octal number out of range
    with pytest.raises(ValueError, match="Invalid shared value"):
        repo.init(shared="1000")  # Octal number > 0777

    # Test non-existent directory with make_parents=False
    non_existent = tmp_path / "non_existent"
    with pytest.raises(FileNotFoundError, match="Directory does not exist"):
        repo = git.Git(path=non_existent)
        repo.init(make_parents=False)


def test_git_init_shared_octal(tmp_path: pathlib.Path) -> None:
    """Test git init with shared octal permissions."""
    repo = git.Git(path=tmp_path)

    # Test valid octal numbers
    for octal in ["0660", "0644", "0755"]:
        repo_dir = tmp_path / f"shared_{octal}"
        repo_dir.mkdir()
        repo = git.Git(path=repo_dir)
        result = repo.init(shared=octal)
        assert "Initialized empty shared Git repository" in result


def test_git_init_shared_values(tmp_path: pathlib.Path) -> None:
    """Test git init with all valid shared values."""
    valid_values = ["false", "true", "umask", "group", "all", "world", "everybody"]

    for value in valid_values:
        repo_dir = tmp_path / f"shared_{value}"
        repo_dir.mkdir()
        repo = git.Git(path=repo_dir)
        result = repo.init(shared=value)
        # The output message varies between git versions and shared values
        assert any(
            msg in result
            for msg in [
                "Initialized empty Git repository",
                "Initialized empty shared Git repository",
            ]
        )


def test_git_init_ref_format(tmp_path: pathlib.Path) -> None:
    """Test git init with different ref formats."""
    repo = git.Git(path=tmp_path)

    # Test with files format (default)
    result = repo.init()
    assert "Initialized empty Git repository" in result

    # Test with reftable format (requires git >= 2.37.0)
    repo_dir = tmp_path / "reftable"
    repo_dir.mkdir()
    repo = git.Git(path=repo_dir)
    try:
        result = repo.init(ref_format="reftable")
        assert "Initialized empty Git repository" in result
    except Exception as e:
        if "unknown option" in str(e):
            pytest.skip("ref-format option not supported in this git version")
        raise


def test_git_init_make_parents(tmp_path: pathlib.Path) -> None:
    """Test git init with make_parents flag."""
    deep_path = tmp_path / "a" / "b" / "c"

    # Test with make_parents=True (default)
    repo = git.Git(path=deep_path)
    result = repo.init()
    assert "Initialized empty Git repository" in result
    assert deep_path.exists()
    assert (deep_path / ".git").is_dir()

    # Test with make_parents=False on existing directory
    existing_path = tmp_path / "existing"
    existing_path.mkdir()
    repo = git.Git(path=existing_path)
    result = repo.init(make_parents=False)
    assert "Initialized empty Git repository" in result
