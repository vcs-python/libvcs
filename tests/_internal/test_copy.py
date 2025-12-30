"""Tests for libvcs._internal.copy."""

from __future__ import annotations

import shutil
import subprocess
import typing as t
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from libvcs._internal.copy import _apply_ignore_patterns, copytree_reflink

# =============================================================================
# copytree_reflink Tests
# =============================================================================


class CopyFixture(t.NamedTuple):
    """Test fixture for copytree_reflink scenarios."""

    test_id: str
    setup_files: dict[str, str]  # filename -> content
    ignore_pattern: str | None
    expected_files: list[str]
    description: str


COPY_FIXTURES = [
    CopyFixture(
        test_id="simple_copy",
        setup_files={"file.txt": "hello", "subdir/nested.txt": "world"},
        ignore_pattern=None,
        expected_files=["file.txt", "subdir/nested.txt"],
        description="Copy all files without ignore patterns",
    ),
    CopyFixture(
        test_id="ignore_pyc",
        setup_files={
            "keep.py": "code",
            "skip.pyc": "compiled",
            "subdir/keep2.py": "more code",
            "subdir/skip2.pyc": "also compiled",
        },
        ignore_pattern="*.pyc",
        expected_files=["keep.py", "subdir/keep2.py"],
        description="Ignore .pyc files",
    ),
    CopyFixture(
        test_id="ignore_directory",
        setup_files={
            "keep.txt": "keep",
            "__pycache__/cached.pyc": "cache",
            "src/code.py": "code",
        },
        ignore_pattern="__pycache__",
        expected_files=["keep.txt", "src/code.py"],
        description="Ignore __pycache__ directory",
    ),
    CopyFixture(
        test_id="empty_directory",
        setup_files={},
        ignore_pattern=None,
        expected_files=[],
        description="Copy empty directory",
    ),
]


class TestCopytreeReflink:
    """Tests for copytree_reflink function."""

    @pytest.mark.parametrize(
        list(CopyFixture._fields),
        COPY_FIXTURES,
        ids=[f.test_id for f in COPY_FIXTURES],
    )
    def test_copy_scenarios(
        self,
        tmp_path: Path,
        test_id: str,
        setup_files: dict[str, str],
        ignore_pattern: str | None,
        expected_files: list[str],
        description: str,
    ) -> None:
        """Test various copy scenarios."""
        # Setup source directory
        src = tmp_path / "source"
        src.mkdir()
        for filename, content in setup_files.items():
            file_path = src / filename
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text(content)

        dst = tmp_path / "dest"
        ignore = shutil.ignore_patterns(ignore_pattern) if ignore_pattern else None

        # Perform copy
        result = copytree_reflink(src, dst, ignore=ignore)

        # Verify result
        assert result == dst
        assert dst.exists()

        # Verify expected files exist
        for expected_file in expected_files:
            expected_path = dst / expected_file
            assert expected_path.exists(), f"Expected {expected_file} to exist"

        # Verify ignored files don't exist (if pattern was provided)
        if ignore_pattern and setup_files:
            for filename in setup_files:
                if filename.endswith(ignore_pattern.replace("*", "")):
                    file_exists = (dst / filename).exists()
                    assert not file_exists, f"{filename} should be ignored"

    def test_preserves_content(self, tmp_path: Path) -> None:
        """Test that file contents are preserved."""
        src = tmp_path / "source"
        src.mkdir()
        (src / "file.txt").write_text("original content")

        dst = tmp_path / "dest"
        copytree_reflink(src, dst)

        assert (dst / "file.txt").read_text() == "original content"

    def test_creates_parent_directories(self, tmp_path: Path) -> None:
        """Test that parent directories are created if needed."""
        src = tmp_path / "source"
        src.mkdir()
        (src / "file.txt").write_text("content")

        dst = tmp_path / "deep" / "nested" / "dest"
        copytree_reflink(src, dst)

        assert dst.exists()
        assert (dst / "file.txt").exists()

    def test_fallback_on_cp_failure(self, tmp_path: Path) -> None:
        """Test fallback to shutil.copytree when cp fails."""
        src = tmp_path / "source"
        src.mkdir()
        (src / "file.txt").write_text("content")

        dst = tmp_path / "dest"

        # Mock subprocess.run to simulate cp failure
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = subprocess.CalledProcessError(1, "cp")
            result = copytree_reflink(src, dst)

        assert result == dst
        assert (dst / "file.txt").exists()

    def test_fallback_on_cp_not_found(self, tmp_path: Path) -> None:
        """Test fallback when cp command is not found (e.g., Windows)."""
        src = tmp_path / "source"
        src.mkdir()
        (src / "file.txt").write_text("content")

        dst = tmp_path / "dest"

        # Mock subprocess.run to simulate FileNotFoundError
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = FileNotFoundError("cp not found")
            result = copytree_reflink(src, dst)

        assert result == dst
        assert (dst / "file.txt").exists()

    def test_fallback_on_os_error(self, tmp_path: Path) -> None:
        """Test fallback on OSError."""
        src = tmp_path / "source"
        src.mkdir()
        (src / "file.txt").write_text("content")

        dst = tmp_path / "dest"

        # Mock subprocess.run to simulate OSError
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = OSError("Unexpected error")
            result = copytree_reflink(src, dst)

        assert result == dst
        assert (dst / "file.txt").exists()

    def test_uses_cp_reflink_auto(self, tmp_path: Path) -> None:
        """Test that cp --reflink=auto is attempted first."""
        src = tmp_path / "source"
        src.mkdir()
        (src / "file.txt").write_text("content")

        dst = tmp_path / "dest"

        with patch("subprocess.run") as mock_run:
            # Simulate successful cp
            mock_run.return_value = MagicMock(returncode=0)
            copytree_reflink(src, dst)

        # Verify cp was called with correct arguments
        mock_run.assert_called_once()
        call_args = mock_run.call_args
        assert call_args[0][0] == ["cp", "-a", "--reflink=auto", str(src), str(dst)]

    def test_returns_pathlib_path(self, tmp_path: Path) -> None:
        """Test that result is always a pathlib.Path."""
        src = tmp_path / "source"
        src.mkdir()

        dst = tmp_path / "dest"
        result = copytree_reflink(src, dst)

        assert isinstance(result, Path)


# =============================================================================
# _apply_ignore_patterns Tests
# =============================================================================


class IgnorePatternFixture(t.NamedTuple):
    """Test fixture for ignore pattern scenarios."""

    test_id: str
    setup_files: list[str]
    ignore_pattern: str
    expected_remaining: list[str]
    description: str


IGNORE_PATTERN_FIXTURES = [
    IgnorePatternFixture(
        test_id="ignore_pyc",
        setup_files=["keep.py", "skip.pyc"],
        ignore_pattern="*.pyc",
        expected_remaining=["keep.py"],
        description="Remove .pyc files",
    ),
    IgnorePatternFixture(
        test_id="ignore_directory",
        setup_files=["keep.txt", "__pycache__/file.pyc"],
        ignore_pattern="__pycache__",
        expected_remaining=["keep.txt"],
        description="Remove __pycache__ directory",
    ),
    IgnorePatternFixture(
        test_id="nested_pattern",
        setup_files=["a/keep.txt", "a/b/skip.tmp", "a/c/keep2.txt"],
        ignore_pattern="*.tmp",
        expected_remaining=["a/keep.txt", "a/c/keep2.txt"],
        description="Remove nested .tmp files",
    ),
]


class TestApplyIgnorePatterns:
    """Tests for _apply_ignore_patterns function."""

    @pytest.mark.parametrize(
        list(IgnorePatternFixture._fields),
        IGNORE_PATTERN_FIXTURES,
        ids=[f.test_id for f in IGNORE_PATTERN_FIXTURES],
    )
    def test_ignore_pattern_scenarios(
        self,
        tmp_path: Path,
        test_id: str,
        setup_files: list[str],
        ignore_pattern: str,
        expected_remaining: list[str],
        description: str,
    ) -> None:
        """Test various ignore pattern scenarios."""
        # Setup directory with files
        for filepath in setup_files:
            file_path = tmp_path / filepath
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text("content")

        # Apply ignore patterns
        ignore = shutil.ignore_patterns(ignore_pattern)
        _apply_ignore_patterns(tmp_path, ignore)

        # Verify expected files remain
        for expected in expected_remaining:
            assert (tmp_path / expected).exists(), f"Expected {expected} to remain"

        # Verify ignored files are removed
        for filepath in setup_files:
            if filepath not in expected_remaining:
                # Check if file or any parent directory was removed
                full_path = tmp_path / filepath
                assert not full_path.exists(), f"Expected {filepath} to be removed"

    def test_empty_directory(self, tmp_path: Path) -> None:
        """Test ignore patterns on empty directory."""
        ignore = shutil.ignore_patterns("*.pyc")
        # Should not raise
        _apply_ignore_patterns(tmp_path, ignore)

    def test_no_matches(self, tmp_path: Path) -> None:
        """Test when no files match ignore pattern."""
        (tmp_path / "file.txt").write_text("content")
        (tmp_path / "other.py").write_text("code")

        ignore = shutil.ignore_patterns("*.pyc")
        _apply_ignore_patterns(tmp_path, ignore)

        # All files should remain
        assert (tmp_path / "file.txt").exists()
        assert (tmp_path / "other.py").exists()


# =============================================================================
# Integration Tests
# =============================================================================


class TestCopyIntegration:
    """Integration tests for copy operations."""

    def test_copy_git_like_structure(self, tmp_path: Path) -> None:
        """Test copying a git-like directory structure."""
        src = tmp_path / "repo"
        src.mkdir()

        # Create git-like structure
        (src / ".git" / "HEAD").parent.mkdir(parents=True)
        (src / ".git" / "HEAD").write_text("ref: refs/heads/main")
        (src / ".git" / "config").write_text("[core]\nrepositoryformatversion = 0")
        (src / "README.md").write_text("# Project")
        (src / "src" / "main.py").parent.mkdir(parents=True)
        (src / "src" / "main.py").write_text("print('hello')")

        dst = tmp_path / "clone"
        copytree_reflink(src, dst)

        # Verify structure
        assert (dst / ".git" / "HEAD").exists()
        assert (dst / ".git" / "config").exists()
        assert (dst / "README.md").exists()
        assert (dst / "src" / "main.py").exists()

        # Verify content
        assert (dst / ".git" / "HEAD").read_text() == "ref: refs/heads/main"
        assert (dst / "README.md").read_text() == "# Project"

    def test_copy_with_marker_file_ignore(self, tmp_path: Path) -> None:
        """Test ignoring marker files like fixtures do."""
        src = tmp_path / "master"
        src.mkdir()

        (src / ".libvcs_master_initialized").write_text("")
        (src / ".git" / "HEAD").parent.mkdir(parents=True)
        (src / ".git" / "HEAD").write_text("ref: refs/heads/main")
        (src / "file.txt").write_text("content")

        dst = tmp_path / "workspace"
        copytree_reflink(
            src,
            dst,
            ignore=shutil.ignore_patterns(".libvcs_master_initialized"),
        )

        # Marker file should be ignored
        assert not (dst / ".libvcs_master_initialized").exists()

        # Other files should be copied
        assert (dst / ".git" / "HEAD").exists()
        assert (dst / "file.txt").exists()

    def test_workspace_is_writable(self, tmp_path: Path) -> None:
        """Test that copied files are writable (important for test fixtures)."""
        src = tmp_path / "source"
        src.mkdir()
        (src / "file.txt").write_text("original")

        dst = tmp_path / "dest"
        copytree_reflink(src, dst)

        # Modify copied file (tests should be able to do this)
        (dst / "file.txt").write_text("modified")
        assert (dst / "file.txt").read_text() == "modified"

        # Original should be unchanged
        assert (src / "file.txt").read_text() == "original"
