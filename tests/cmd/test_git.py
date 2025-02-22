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
