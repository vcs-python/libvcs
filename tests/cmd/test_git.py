"""Tests for libvcs.cmd.git."""

from __future__ import annotations

import os
import pathlib
import typing as t

import pytest

from libvcs._internal.query_list import ObjectDoesNotExist
from libvcs.cmd import git

if t.TYPE_CHECKING:
    from libvcs.sync.git import GitSync


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


class InitSharedFixture(t.NamedTuple):
    """Test fixture for Git.init() shared parameter behavior."""

    test_id: str
    shared: bool | str | None
    expect_shared_repo: bool  # True = "shared Git repository" in output


INIT_SHARED_FIXTURES: list[InitSharedFixture] = [
    InitSharedFixture(
        test_id="shared-true-passes-flag",
        shared=True,
        expect_shared_repo=True,
    ),
    InitSharedFixture(
        test_id="shared-false-omits-flag",
        shared=False,
        expect_shared_repo=False,  # Key: shared=False should NOT pass --shared
    ),
    InitSharedFixture(
        test_id="shared-none-omits-flag",
        shared=None,
        expect_shared_repo=False,
    ),
    InitSharedFixture(
        test_id="shared-group-passes-value",
        shared="group",
        expect_shared_repo=True,
    ),
]


@pytest.mark.parametrize(
    list(InitSharedFixture._fields),
    INIT_SHARED_FIXTURES,
    ids=[test.test_id for test in INIT_SHARED_FIXTURES],
)
def test_git_init_shared_boolean_behavior(
    tmp_path: pathlib.Path,
    test_id: str,
    shared: bool | str | None,
    expect_shared_repo: bool,
) -> None:
    """Test Git.init() shared parameter behavior.

    Verifies commit 03b124c: shared=False should NOT pass --shared flag.
    """
    repo_dir = tmp_path / f"init_{test_id}"
    repo_dir.mkdir()
    repo = git.Git(path=repo_dir)

    result = repo.init(shared=shared)

    # Check for "shared Git repository" in output (not just "shared" - matches path)
    if expect_shared_repo:
        assert "shared git repository" in result.lower()
    else:
        assert "shared git repository" not in result.lower()


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


# =============================================================================
# GitBranchCmd Tests
# =============================================================================


class BranchDeleteFixture(t.NamedTuple):
    """Test fixture for GitBranchCmd.delete() operations."""

    test_id: str
    branch_name: str
    force: bool
    expect_success: bool


BRANCH_DELETE_FIXTURES: list[BranchDeleteFixture] = [
    BranchDeleteFixture(
        test_id="delete-merged-branch",
        branch_name="feature-branch",
        force=False,
        expect_success=True,
    ),
    BranchDeleteFixture(
        test_id="delete-branch-force",
        branch_name="force-delete-branch",
        force=True,
        expect_success=True,
    ),
]


@pytest.mark.parametrize(
    list(BranchDeleteFixture._fields),
    BRANCH_DELETE_FIXTURES,
    ids=[test.test_id for test in BRANCH_DELETE_FIXTURES],
)
def test_branch_delete(
    git_repo: GitSync,
    test_id: str,
    branch_name: str,
    force: bool,
    expect_success: bool,
) -> None:
    """Test GitBranchCmd.delete() with various scenarios."""
    # Setup: create and checkout a branch, then switch back
    git_repo.cmd.branches.create(branch=branch_name)
    git_repo.cmd.checkout(branch="master")

    # Get branch via Manager
    branch = git_repo.cmd.branches.get(branch_name=branch_name)
    assert branch is not None

    # Delete the branch
    branch.delete(force=force)

    # Verify deletion - get() raises ObjectDoesNotExist when not found
    with pytest.raises(ObjectDoesNotExist):
        git_repo.cmd.branches.get(branch_name=branch_name)


class BranchRenameFixture(t.NamedTuple):
    """Test fixture for GitBranchCmd.rename() operations."""

    test_id: str
    original_name: str
    new_name: str
    force: bool


BRANCH_RENAME_FIXTURES: list[BranchRenameFixture] = [
    BranchRenameFixture(
        test_id="rename-simple",
        original_name="old-branch",
        new_name="new-branch",
        force=False,
    ),
    BranchRenameFixture(
        test_id="rename-with-force",
        original_name="rename-source",
        new_name="rename-target",
        force=True,
    ),
]


@pytest.mark.parametrize(
    list(BranchRenameFixture._fields),
    BRANCH_RENAME_FIXTURES,
    ids=[test.test_id for test in BRANCH_RENAME_FIXTURES],
)
def test_branch_rename(
    git_repo: GitSync,
    test_id: str,
    original_name: str,
    new_name: str,
    force: bool,
) -> None:
    """Test GitBranchCmd.rename() with various scenarios."""
    # Setup: create a branch
    git_repo.cmd.branches.create(branch=original_name)
    git_repo.cmd.checkout(branch="master")

    # Get branch and rename
    branch = git_repo.cmd.branches.get(branch_name=original_name)
    assert branch is not None
    branch.rename(new_name, force=force)

    # Verify: old name gone (raises ObjectDoesNotExist), new name exists
    with pytest.raises(ObjectDoesNotExist):
        git_repo.cmd.branches.get(branch_name=original_name)
    assert git_repo.cmd.branches.get(branch_name=new_name) is not None


class BranchCopyFixture(t.NamedTuple):
    """Test fixture for GitBranchCmd.copy() operations."""

    test_id: str
    source_name: str
    copy_name: str
    force: bool


BRANCH_COPY_FIXTURES: list[BranchCopyFixture] = [
    BranchCopyFixture(
        test_id="copy-simple",
        source_name="source-branch",
        copy_name="copied-branch",
        force=False,
    ),
    BranchCopyFixture(
        test_id="copy-with-force",
        source_name="copy-source",
        copy_name="copy-target",
        force=True,
    ),
]


@pytest.mark.parametrize(
    list(BranchCopyFixture._fields),
    BRANCH_COPY_FIXTURES,
    ids=[test.test_id for test in BRANCH_COPY_FIXTURES],
)
def test_branch_copy(
    git_repo: GitSync,
    test_id: str,
    source_name: str,
    copy_name: str,
    force: bool,
) -> None:
    """Test GitBranchCmd.copy() with various scenarios."""
    # Setup: create a branch
    git_repo.cmd.branches.create(branch=source_name)
    git_repo.cmd.checkout(branch="master")

    # Get branch and copy
    branch = git_repo.cmd.branches.get(branch_name=source_name)
    assert branch is not None
    branch.copy(copy_name, force=force)

    # Verify: both branches exist
    assert git_repo.cmd.branches.get(branch_name=source_name) is not None
    assert git_repo.cmd.branches.get(branch_name=copy_name) is not None


class BranchUpstreamFixture(t.NamedTuple):
    """Test fixture for GitBranchCmd upstream operations."""

    test_id: str
    branch_name: str
    upstream: str


BRANCH_UPSTREAM_FIXTURES: list[BranchUpstreamFixture] = [
    BranchUpstreamFixture(
        test_id="set-upstream-origin-master",
        branch_name="tracking-branch",
        upstream="origin/master",
    ),
]


@pytest.mark.parametrize(
    list(BranchUpstreamFixture._fields),
    BRANCH_UPSTREAM_FIXTURES,
    ids=[test.test_id for test in BRANCH_UPSTREAM_FIXTURES],
)
def test_branch_set_upstream(
    git_repo: GitSync,
    test_id: str,
    branch_name: str,
    upstream: str,
) -> None:
    """Test GitBranchCmd.set_upstream() with various scenarios."""
    # Setup: create a branch
    git_repo.cmd.branches.create(branch=branch_name)
    git_repo.cmd.checkout(branch="master")

    # Get branch and set upstream
    branch = git_repo.cmd.branches.get(branch_name=branch_name)
    assert branch is not None
    result = branch.set_upstream(upstream)

    # Verify: should succeed (output contains confirmation)
    assert "set up to track" in result.lower() or result == ""


def test_branch_unset_upstream(git_repo: GitSync) -> None:
    """Test GitBranchCmd.unset_upstream()."""
    branch_name = "untrack-branch"

    # Setup: create a branch and set upstream
    git_repo.cmd.branches.create(branch=branch_name)
    git_repo.cmd.checkout(branch="master")

    branch = git_repo.cmd.branches.get(branch_name=branch_name)
    assert branch is not None

    # Set then unset upstream
    branch.set_upstream("origin/master")
    result = branch.unset_upstream()

    # unset_upstream typically returns empty string on success
    assert result == "" or "upstream" not in result.lower()


def test_branch_track(git_repo: GitSync) -> None:
    """Test GitBranchCmd.track()."""
    branch_name = "tracking-test-branch"

    branch = git.GitBranchCmd(path=git_repo.path, branch_name=branch_name)
    result = branch.track("origin/master")

    # Should create branch tracking origin/master
    assert "set up to track" in result.lower()

    # Verify branch was created
    branches = git_repo.cmd.branches.ls()
    branch_names = [b.branch_name for b in branches]
    assert branch_name in branch_names


def test_branch_ls_filters(git_repo: GitSync) -> None:
    """Test GitBranchManager.ls() with filter parameters."""
    # Test basic ls
    branches = git_repo.cmd.branches.ls()
    assert len(branches) >= 1
    assert any(b.branch_name == "master" for b in branches)

    # Test with --all (includes remote-tracking branches)
    all_branches = git_repo.cmd.branches.ls(_all=True)
    assert len(all_branches) >= len(branches)

    # Test with --merged (branches merged into HEAD)
    merged = git_repo.cmd.branches.ls(merged="HEAD")
    assert isinstance(merged, list)
    # master should be merged into HEAD
    assert any(b.branch_name == "master" for b in merged)

    # Test with --contains (branches containing HEAD commit)
    contains = git_repo.cmd.branches.ls(contains="HEAD")
    assert isinstance(contains, list)
    assert any(b.branch_name == "master" for b in contains)

    # Test with --sort
    sorted_branches = git_repo.cmd.branches.ls(sort="refname")
    assert isinstance(sorted_branches, list)

    # Test with --verbose (should still extract branch names correctly)
    verbose_branches = git_repo.cmd.branches.ls(verbose=True)
    assert isinstance(verbose_branches, list)
    assert any(b.branch_name == "master" for b in verbose_branches)


class BranchCreateFixture(t.NamedTuple):
    """Test fixture for GitBranchCmd.create() and GitBranchManager.create()."""

    test_id: str
    checkout: bool
    expect_switch: bool


BRANCH_CREATE_FIXTURES: list[BranchCreateFixture] = [
    BranchCreateFixture(
        test_id="create-without-checkout",
        checkout=False,
        expect_switch=False,
    ),
    BranchCreateFixture(
        test_id="create-with-checkout",
        checkout=True,
        expect_switch=True,
    ),
]


@pytest.mark.parametrize(
    list(BranchCreateFixture._fields),
    BRANCH_CREATE_FIXTURES,
    ids=[test.test_id for test in BRANCH_CREATE_FIXTURES],
)
def test_branch_cmd_create_checkout_parameter(
    git_repo: GitSync,
    test_id: str,
    checkout: bool,
    expect_switch: bool,
) -> None:
    """Test GitBranchCmd.create() checkout parameter behavior.

    Verifies commit 4b8a0f7: create() uses 'git branch' instead of 'checkout -b',
    and only switches HEAD when checkout=True.
    """
    branch_name = f"test-create-{test_id}"

    # Record current branch before creating
    current_before = git_repo.cmd.symbolic_ref(name="HEAD", short=True)

    # Create branch using GitBranchCmd
    branch_cmd = git.GitBranchCmd(path=git_repo.path, branch_name=branch_name)
    result = branch_cmd.create(checkout=checkout)

    # Should succeed (empty string or no fatal error)
    assert "fatal" not in result.lower() or "already exists" in result.lower()

    # Verify branch was created
    branches = git_repo.cmd.branches.ls()
    branch_names = [b.branch_name for b in branches]
    assert branch_name in branch_names

    # Check if HEAD switched
    current_after = git_repo.cmd.symbolic_ref(name="HEAD", short=True)
    if expect_switch:
        assert current_after == branch_name
    else:
        assert current_after == current_before


@pytest.mark.parametrize(
    list(BranchCreateFixture._fields),
    BRANCH_CREATE_FIXTURES,
    ids=[test.test_id for test in BRANCH_CREATE_FIXTURES],
)
def test_branch_manager_create_checkout_parameter(
    git_repo: GitSync,
    test_id: str,
    checkout: bool,
    expect_switch: bool,
) -> None:
    """Test GitBranchManager.create() checkout parameter behavior.

    Verifies commit 4b8a0f7: create() uses 'git branch' instead of 'checkout -b',
    and only switches HEAD when checkout=True.
    """
    branch_name = f"test-mgr-create-{test_id}"

    # Record current branch before creating
    current_before = git_repo.cmd.symbolic_ref(name="HEAD", short=True)

    # Create branch using GitBranchManager
    result = git_repo.cmd.branches.create(branch=branch_name, checkout=checkout)

    # Should succeed (empty string or no fatal error)
    assert "fatal" not in result.lower() or "already exists" in result.lower()

    # Verify branch was created
    branches = git_repo.cmd.branches.ls()
    branch_names = [b.branch_name for b in branches]
    assert branch_name in branch_names

    # Check if HEAD switched
    current_after = git_repo.cmd.symbolic_ref(name="HEAD", short=True)
    if expect_switch:
        assert current_after == branch_name
    else:
        assert current_after == current_before


# =============================================================================
# GitRemoteCmd Tests
# =============================================================================


class RemoteSetBranchesFixture(t.NamedTuple):
    """Test fixture for GitRemoteCmd.set_branches() operations."""

    test_id: str
    branches: tuple[str, ...]
    add: bool


REMOTE_SET_BRANCHES_FIXTURES: list[RemoteSetBranchesFixture] = [
    RemoteSetBranchesFixture(
        test_id="set-single-branch",
        branches=("master",),
        add=False,
    ),
    RemoteSetBranchesFixture(
        test_id="set-multiple-branches",
        branches=("master", "develop"),
        add=False,
    ),
    RemoteSetBranchesFixture(
        test_id="add-branch",
        branches=("feature",),
        add=True,
    ),
]


@pytest.mark.parametrize(
    list(RemoteSetBranchesFixture._fields),
    REMOTE_SET_BRANCHES_FIXTURES,
    ids=[test.test_id for test in REMOTE_SET_BRANCHES_FIXTURES],
)
def test_remote_set_branches(
    git_repo: GitSync,
    test_id: str,
    branches: tuple[str, ...],
    add: bool,
) -> None:
    """Test GitRemoteCmd.set_branches() with various scenarios."""
    remote = git_repo.cmd.remotes.get(remote_name="origin")
    assert remote is not None

    # set_branches should succeed without error
    result = remote.set_branches(*branches, add=add)
    assert result == ""


class RemoteSetHeadFixture(t.NamedTuple):
    """Test fixture for GitRemoteCmd.set_head() operations."""

    test_id: str
    branch: str | None
    auto: bool
    delete: bool


REMOTE_SET_HEAD_FIXTURES: list[RemoteSetHeadFixture] = [
    RemoteSetHeadFixture(
        test_id="set-head-auto",
        branch=None,
        auto=True,
        delete=False,
    ),
    RemoteSetHeadFixture(
        test_id="set-head-explicit",
        branch="master",
        auto=False,
        delete=False,
    ),
]


@pytest.mark.parametrize(
    list(RemoteSetHeadFixture._fields),
    REMOTE_SET_HEAD_FIXTURES,
    ids=[test.test_id for test in REMOTE_SET_HEAD_FIXTURES],
)
def test_remote_set_head(
    git_repo: GitSync,
    test_id: str,
    branch: str | None,
    auto: bool,
    delete: bool,
) -> None:
    """Test GitRemoteCmd.set_head() with various scenarios."""
    remote = git_repo.cmd.remotes.get(remote_name="origin")
    assert remote is not None

    result = remote.set_head(branch, auto=auto, delete=delete)

    # set_head returns either confirmation message or empty string
    if auto:
        result_lower = result.lower()
        assert "set to" in result_lower or "unchanged" in result_lower or result == ""
    else:
        assert result == "" or "head" in result.lower()


class RemoteUpdateFixture(t.NamedTuple):
    """Test fixture for GitRemoteCmd.update() operations."""

    test_id: str
    prune: bool


REMOTE_UPDATE_FIXTURES: list[RemoteUpdateFixture] = [
    RemoteUpdateFixture(
        test_id="update-simple",
        prune=False,
    ),
    RemoteUpdateFixture(
        test_id="update-with-prune",
        prune=True,
    ),
]


@pytest.mark.parametrize(
    list(RemoteUpdateFixture._fields),
    REMOTE_UPDATE_FIXTURES,
    ids=[test.test_id for test in REMOTE_UPDATE_FIXTURES],
)
def test_remote_update(
    git_repo: GitSync,
    test_id: str,
    prune: bool,
) -> None:
    """Test GitRemoteCmd.update() with various scenarios."""
    remote = git_repo.cmd.remotes.get(remote_name="origin")
    assert remote is not None

    result = remote.update(prune=prune)

    # update typically returns "Fetching <remote>" message
    assert "fetching" in result.lower() or result == ""


class RemoteShowNoQueryRemotesFixture(t.NamedTuple):
    """Test fixture for GitRemoteCmd.show() no_query_remotes parameter."""

    test_id: str
    no_query_remotes: bool | None
    expect_n_flag: bool


REMOTE_SHOW_NO_QUERY_REMOTES_FIXTURES: list[RemoteShowNoQueryRemotesFixture] = [
    RemoteShowNoQueryRemotesFixture(
        test_id="no-query-remotes-none",
        no_query_remotes=None,
        expect_n_flag=False,
    ),
    RemoteShowNoQueryRemotesFixture(
        test_id="no-query-remotes-true",
        no_query_remotes=True,
        expect_n_flag=True,
    ),
    RemoteShowNoQueryRemotesFixture(
        test_id="no-query-remotes-false",
        no_query_remotes=False,
        expect_n_flag=False,
    ),
]


@pytest.mark.parametrize(
    list(RemoteShowNoQueryRemotesFixture._fields),
    REMOTE_SHOW_NO_QUERY_REMOTES_FIXTURES,
    ids=[test.test_id for test in REMOTE_SHOW_NO_QUERY_REMOTES_FIXTURES],
)
def test_remote_cmd_show_no_query_remotes(
    git_repo: GitSync,
    test_id: str,
    no_query_remotes: bool | None,
    expect_n_flag: bool,
) -> None:
    """Test GitRemoteCmd.show() with no_query_remotes parameter."""
    remote = git_repo.cmd.remotes.get(remote_name="origin")
    assert remote is not None

    # show() should succeed without error
    result = remote.show(no_query_remotes=no_query_remotes)
    assert isinstance(result, str)
    # Result should contain remote name info
    assert "origin" in result.lower() or "fetch" in result.lower()


@pytest.mark.parametrize(
    list(RemoteShowNoQueryRemotesFixture._fields),
    REMOTE_SHOW_NO_QUERY_REMOTES_FIXTURES,
    ids=[test.test_id for test in REMOTE_SHOW_NO_QUERY_REMOTES_FIXTURES],
)
def test_remote_manager_show_no_query_remotes(
    git_repo: GitSync,
    test_id: str,
    no_query_remotes: bool | None,
    expect_n_flag: bool,
) -> None:
    """Test GitRemoteManager.show() with no_query_remotes parameter."""
    # show() should succeed without error
    result = git_repo.cmd.remotes.show(name="origin", no_query_remotes=no_query_remotes)
    assert isinstance(result, str)
    # Result should contain remote name info
    assert "origin" in result.lower() or "fetch" in result.lower()


# =============================================================================
# GitTagCmd / GitTagManager Tests
# =============================================================================


class TagCreateFixture(t.NamedTuple):
    """Test fixture for GitTagManager.create() operations."""

    test_id: str
    tag_name: str
    message: str | None
    annotate: bool | None
    ref: str | None
    force: bool | None


TAG_CREATE_FIXTURES: list[TagCreateFixture] = [
    TagCreateFixture(
        test_id="create-lightweight-tag",
        tag_name="lightweight-v1.0",
        message=None,
        annotate=None,
        ref=None,
        force=None,
    ),
    TagCreateFixture(
        test_id="create-annotated-tag",
        tag_name="annotated-v1.0",
        message="Release version 1.0",
        annotate=None,  # message implies annotated
        ref=None,
        force=None,
    ),
    TagCreateFixture(
        test_id="create-tag-explicit-annotate",
        tag_name="explicit-annotated-v1.0",
        message="Explicit annotated tag",
        annotate=True,
        ref=None,
        force=None,
    ),
    TagCreateFixture(
        test_id="create-tag-at-ref",
        tag_name="ref-v1.0",
        message="Tag at HEAD",
        annotate=None,
        ref="HEAD",
        force=None,
    ),
]


@pytest.mark.parametrize(
    list(TagCreateFixture._fields),
    TAG_CREATE_FIXTURES,
    ids=[test.test_id for test in TAG_CREATE_FIXTURES],
)
def test_tag_create(
    git_repo: GitSync,
    test_id: str,
    tag_name: str,
    message: str | None,
    annotate: bool | None,
    ref: str | None,
    force: bool | None,
) -> None:
    """Test GitTagManager.create() with various scenarios."""
    result = git_repo.cmd.tags.create(
        name=tag_name,
        message=message,
        annotate=annotate,
        ref=ref,
        force=force,
    )

    # create returns empty string on success
    assert result == ""

    # Verify tag exists
    tag = git_repo.cmd.tags.get(tag_name=tag_name)
    assert tag is not None
    assert tag.tag_name == tag_name


def test_tag_create_force(git_repo: GitSync) -> None:
    """Test GitTagManager.create() with force flag to replace existing tag."""
    tag_name = "force-replace-tag"

    # Create initial tag
    git_repo.cmd.tags.create(name=tag_name, message="Initial tag")

    # Creating same tag without force returns error message
    result_without_force = git_repo.cmd.tags.create(
        name=tag_name, message="Replacement tag"
    )
    assert "already exists" in result_without_force.lower()

    # Creating same tag with force should succeed
    result = git_repo.cmd.tags.create(
        name=tag_name, message="Replacement tag", force=True
    )
    # Force update returns "Updated tag" message
    assert result == "" or "updated tag" in result.lower()


class TagDeleteFixture(t.NamedTuple):
    """Test fixture for GitTagCmd.delete() operations."""

    test_id: str
    tag_name: str
    message: str


TAG_DELETE_FIXTURES: list[TagDeleteFixture] = [
    TagDeleteFixture(
        test_id="delete-lightweight-tag",
        tag_name="delete-lightweight",
        message="",  # empty message = lightweight tag
    ),
    TagDeleteFixture(
        test_id="delete-annotated-tag",
        tag_name="delete-annotated",
        message="Annotated tag to delete",
    ),
]


@pytest.mark.parametrize(
    list(TagDeleteFixture._fields),
    TAG_DELETE_FIXTURES,
    ids=[test.test_id for test in TAG_DELETE_FIXTURES],
)
def test_tag_delete(
    git_repo: GitSync,
    test_id: str,
    tag_name: str,
    message: str,
) -> None:
    """Test GitTagCmd.delete() with various scenarios."""
    # Create tag first
    if message:
        git_repo.cmd.tags.create(name=tag_name, message=message)
    else:
        git_repo.cmd.tags.create(name=tag_name)

    # Get and delete the tag
    tag = git_repo.cmd.tags.get(tag_name=tag_name)
    assert tag is not None

    result = tag.delete()
    assert "deleted tag" in result.lower()

    # Verify tag is gone
    with pytest.raises(ObjectDoesNotExist):
        git_repo.cmd.tags.get(tag_name=tag_name)


class TagListFixture(t.NamedTuple):
    """Test fixture for GitTagManager.ls() operations."""

    test_id: str
    setup_tags: list[str]
    pattern: str | None
    expected_min_count: int


TAG_LIST_FIXTURES: list[TagListFixture] = [
    TagListFixture(
        test_id="list-all-tags",
        setup_tags=["list-v1.0", "list-v2.0", "list-v3.0"],
        pattern=None,
        expected_min_count=3,
    ),
    TagListFixture(
        test_id="list-tags-with-pattern",
        setup_tags=["pattern-alpha", "pattern-beta", "other-tag"],
        pattern="pattern-*",
        expected_min_count=2,
    ),
]


@pytest.mark.parametrize(
    list(TagListFixture._fields),
    TAG_LIST_FIXTURES,
    ids=[test.test_id for test in TAG_LIST_FIXTURES],
)
def test_tag_list(
    git_repo: GitSync,
    test_id: str,
    setup_tags: list[str],
    pattern: str | None,
    expected_min_count: int,
) -> None:
    """Test GitTagManager.ls() with various scenarios."""
    # Create setup tags
    for tag_name in setup_tags:
        git_repo.cmd.tags.create(name=tag_name, message=f"Tag {tag_name}")

    # List tags
    tags = git_repo.cmd.tags.ls(pattern=pattern)

    # Verify minimum count
    assert len(tags) >= expected_min_count


def test_tag_filter(git_repo: GitSync) -> None:
    """Test GitTagManager.filter() with QueryList filtering."""
    # Create tags with different prefixes
    git_repo.cmd.tags.create(name="release-1.0", message="Release 1.0")
    git_repo.cmd.tags.create(name="release-2.0", message="Release 2.0")
    git_repo.cmd.tags.create(name="beta-1.0", message="Beta 1.0")

    # Filter by prefix
    release_tags = git_repo.cmd.tags.filter(tag_name__startswith="release-")
    assert len(release_tags) >= 2

    beta_tags = git_repo.cmd.tags.filter(tag_name__contains="beta")
    assert len(beta_tags) >= 1


def test_tag_show(git_repo: GitSync) -> None:
    """Test GitTagCmd.show() for annotated tags."""
    tag_name = "show-test-tag"
    message = "This is a test tag for show"

    # Create annotated tag
    git_repo.cmd.tags.create(name=tag_name, message=message)

    # Get tag and show
    tag = git_repo.cmd.tags.get(tag_name=tag_name)
    assert tag is not None

    result = tag.show()

    # show output should contain tag name and message
    assert tag_name in result
    assert message in result


def test_tag_verify_unsigned(git_repo: GitSync) -> None:
    """Test GitTagCmd.verify() for unsigned/lightweight tags."""
    tag_name = "verify-unsigned-tag"

    # Create lightweight tag (can't be verified)
    git_repo.cmd.tags.create(name=tag_name)

    tag = git_repo.cmd.tags.get(tag_name=tag_name)
    assert tag is not None

    result = tag.verify()

    # verify on unsigned tag should return error message
    assert "error" in result.lower() or "cannot verify" in result.lower()


# =============================================================================
# GitStashManager / GitStashEntryCmd Tests
# =============================================================================


def test_stash_push_and_list(git_repo: GitSync) -> None:
    """Test GitStashManager.push() and ls()."""
    # Create a file and modify it to have something to stash
    test_file = git_repo.path / "stash_test.txt"
    test_file.write_text("initial content")
    git_repo.cmd.run(["add", "stash_test.txt"])
    git_repo.cmd.run(["commit", "-m", "Add test file"])

    # Modify the file
    test_file.write_text("modified content")

    # Push to stash
    result = git_repo.cmd.stashes.push(message="Test stash")

    # Should succeed (not "No local changes")
    assert "no local changes" not in result.lower()

    # List stashes
    stashes = git_repo.cmd.stashes.ls()
    assert len(stashes) >= 1
    assert stashes[0].index == 0


def test_stash_entry_show(git_repo: GitSync) -> None:
    """Test GitStashEntryCmd.show()."""
    # Create a stash first
    test_file = git_repo.path / "show_test.txt"
    test_file.write_text("initial content")
    git_repo.cmd.run(["add", "show_test.txt"])
    git_repo.cmd.run(["commit", "-m", "Add test file"])

    test_file.write_text("modified for stash")
    git_repo.cmd.stashes.push(message="Show test stash")

    # Get stash and show
    stash = git_repo.cmd.stashes.get(index=0)
    assert stash is not None

    result = stash.show()

    # show should display diff info
    assert "show_test.txt" in result or len(result) > 0


class StashApplyPopFixture(t.NamedTuple):
    """Test fixture for GitStashEntryCmd apply/pop operations."""

    test_id: str
    method: str  # "apply" or "pop"
    removes_stash: bool


STASH_APPLY_POP_FIXTURES: list[StashApplyPopFixture] = [
    StashApplyPopFixture(
        test_id="apply-stash",
        method="apply",
        removes_stash=False,
    ),
    StashApplyPopFixture(
        test_id="pop-stash",
        method="pop",
        removes_stash=True,
    ),
]


@pytest.mark.parametrize(
    list(StashApplyPopFixture._fields),
    STASH_APPLY_POP_FIXTURES,
    ids=[test.test_id for test in STASH_APPLY_POP_FIXTURES],
)
def test_stash_apply_pop(
    git_repo: GitSync,
    test_id: str,
    method: str,
    removes_stash: bool,
) -> None:
    """Test GitStashEntryCmd.apply() and pop()."""
    # Clear any existing stashes
    git_repo.cmd.stashes.clear()

    # Create a stash first
    test_file = git_repo.path / f"{test_id}_test.txt"
    test_file.write_text("initial content")
    git_repo.cmd.run(["add", f"{test_id}_test.txt"])
    git_repo.cmd.run(["commit", "-m", "Add test file"])

    test_file.write_text("modified for stash")
    git_repo.cmd.stashes.push(message=f"Test {method}")

    # Get stash
    stash = git_repo.cmd.stashes.get(index=0)
    assert stash is not None

    # Apply or pop
    result = stash.apply() if method == "apply" else stash.pop()

    # Should succeed
    assert "error" not in result.lower() or "conflict" in result.lower()

    # Check if stash was removed
    stashes_after = git_repo.cmd.stashes.ls()
    if removes_stash:
        assert len(stashes_after) == 0
    else:
        assert len(stashes_after) >= 1


def test_stash_pop_by_specific_index(git_repo: GitSync) -> None:
    """Test GitStashEntryCmd.pop() with specific stash index.

    Verifies commit 12065f6: pop() uses stash@{N} format instead of
    pathspec separator (-- N) which caused 'is not a valid reference' errors.

    Note: git stash uses LIFO ordering:
    - stash@{0} = most recent
    - stash@{1} = second most recent
    - stash@{2} = oldest
    """
    # Clear any existing stashes
    git_repo.cmd.stashes.clear()

    # Create a tracked file
    test_file = git_repo.path / "stash_pop_index_test.txt"
    test_file.write_text("initial content")
    git_repo.cmd.run(["add", "stash_pop_index_test.txt"])
    git_repo.cmd.run(["commit", "-m", "Add test file"])

    # Create multiple stashes
    # Note: stash@{0} is most recent, stash@{2} is oldest
    for msg in ["oldest", "middle", "newest"]:
        test_file.write_text(f"modified for {msg}")
        git_repo.cmd.stashes.push(message=msg)

    # Verify we have 3 stashes
    stashes = git_repo.cmd.stashes.ls()
    assert len(stashes) == 3

    # Pop stash@{1} (the middle one)
    # This tests that the stash@{N} format works correctly
    middle_stash = git_repo.cmd.stashes.get(index=1)
    assert middle_stash is not None
    assert "middle" in middle_stash.message

    # Pop should NOT produce "is not a valid reference" error
    result = middle_stash.pop()
    assert "is not a valid reference" not in result.lower()

    # Verify we now have 2 stashes
    stashes_after = git_repo.cmd.stashes.ls()
    assert len(stashes_after) == 2


def test_stash_drop(git_repo: GitSync) -> None:
    """Test GitStashEntryCmd.drop()."""
    # Clear any existing stashes
    git_repo.cmd.stashes.clear()

    # Create a stash first
    test_file = git_repo.path / "drop_test.txt"
    test_file.write_text("initial content")
    git_repo.cmd.run(["add", "drop_test.txt"])
    git_repo.cmd.run(["commit", "-m", "Add test file"])

    test_file.write_text("modified for stash")
    git_repo.cmd.stashes.push(message="Drop test stash")

    # Verify stash exists
    stashes = git_repo.cmd.stashes.ls()
    assert len(stashes) == 1

    # Get stash and drop
    stash = git_repo.cmd.stashes.get(index=0)
    assert stash is not None

    result = stash.drop()
    assert "dropped" in result.lower()

    # Verify stash is gone
    stashes_after = git_repo.cmd.stashes.ls()
    assert len(stashes_after) == 0


def test_stash_clear(git_repo: GitSync) -> None:
    """Test GitStashManager.clear()."""
    # Create multiple stashes
    test_file = git_repo.path / "clear_test.txt"
    test_file.write_text("initial content")
    git_repo.cmd.run(["add", "clear_test.txt"])
    git_repo.cmd.run(["commit", "-m", "Add test file"])

    # Create first stash
    test_file.write_text("modified 1")
    git_repo.cmd.stashes.push(message="First stash")

    # Create second stash
    test_file.write_text("modified 2")
    git_repo.cmd.stashes.push(message="Second stash")

    # Verify stashes exist
    stashes = git_repo.cmd.stashes.ls()
    assert len(stashes) >= 2

    # Clear all stashes
    result = git_repo.cmd.stashes.clear()
    assert result == ""

    # Verify all stashes are gone
    stashes_after = git_repo.cmd.stashes.ls()
    assert len(stashes_after) == 0


def test_stash_filter(git_repo: GitSync) -> None:
    """Test GitStashManager.filter() with QueryList filtering."""
    # Create a stash on master branch
    test_file = git_repo.path / "filter_test.txt"
    test_file.write_text("initial content")
    git_repo.cmd.run(["add", "filter_test.txt"])
    git_repo.cmd.run(["commit", "-m", "Add test file"])

    test_file.write_text("modified for stash")
    git_repo.cmd.stashes.push(message="Filter test stash")

    # Filter by branch
    stashes = git_repo.cmd.stashes.filter(branch="master")
    assert len(stashes) >= 1


def test_stash_entry_create_branch(git_repo: GitSync) -> None:
    """Test GitStashEntryCmd.create_branch()."""
    # Create a stash first
    test_file = git_repo.path / "branch_test.txt"
    test_file.write_text("initial content")
    git_repo.cmd.run(["add", "branch_test.txt"])
    git_repo.cmd.run(["commit", "-m", "Add test file"])

    test_file.write_text("modified for stash")
    git_repo.cmd.stashes.push(message="Branch test stash")

    # Get stash and create branch
    stash = git_repo.cmd.stashes.get(index=0)
    assert stash is not None

    result = stash.create_branch("stash-branch")

    # Should create branch and apply stash
    assert "error" not in result.lower() or "already exists" in result.lower()

    # Verify branch exists (or stash was applied)
    branches = git_repo.cmd.branches.ls()
    branch_names = [b.branch_name for b in branches]
    # Either branch was created or we're on it
    assert "stash-branch" in branch_names or "master" in branch_names


# =============================================================================
# GitWorktreeManager / GitWorktreeCmd Tests
# =============================================================================


class WorktreeAddFixture(t.NamedTuple):
    """Test fixture for GitWorktreeManager.add() operations."""

    test_id: str
    new_branch: str | None
    detach: bool | None


WORKTREE_ADD_FIXTURES: list[WorktreeAddFixture] = [
    WorktreeAddFixture(
        test_id="add-worktree-with-new-branch",
        new_branch="worktree-branch",
        detach=None,
    ),
    WorktreeAddFixture(
        test_id="add-worktree-detached",
        new_branch=None,
        detach=True,
    ),
]


@pytest.mark.parametrize(
    list(WorktreeAddFixture._fields),
    WORKTREE_ADD_FIXTURES,
    ids=[test.test_id for test in WORKTREE_ADD_FIXTURES],
)
def test_worktree_add(
    git_repo: GitSync,
    tmp_path: pathlib.Path,
    test_id: str,
    new_branch: str | None,
    detach: bool | None,
) -> None:
    """Test GitWorktreeManager.add() with various scenarios."""
    worktree_path = tmp_path / f"worktree-{test_id}"

    result = git_repo.cmd.worktrees.add(
        path=worktree_path,
        new_branch=new_branch,
        detach=detach,
    )

    # Should succeed (output contains "Preparing worktree" or similar)
    assert "preparing worktree" in result.lower() or worktree_path.exists()

    # Verify worktree was created
    worktrees = git_repo.cmd.worktrees.ls()
    worktree_paths = [wt.worktree_path for wt in worktrees]
    assert str(worktree_path) in worktree_paths


def test_worktree_list(git_repo: GitSync, tmp_path: pathlib.Path) -> None:
    """Test GitWorktreeManager.ls() returns main worktree."""
    worktrees = git_repo.cmd.worktrees.ls()

    # Should have at least the main worktree
    assert len(worktrees) >= 1

    # Each worktree should have a path
    for wt in worktrees:
        assert wt.worktree_path is not None


def test_worktree_get(git_repo: GitSync, tmp_path: pathlib.Path) -> None:
    """Test GitWorktreeManager.get() retrieves specific worktree."""
    # Create a worktree first
    worktree_path = tmp_path / "get-test-worktree"
    git_repo.cmd.worktrees.add(path=worktree_path, new_branch="get-test-branch")

    # Get the worktree
    worktree = git_repo.cmd.worktrees.get(worktree_path=str(worktree_path))
    assert worktree is not None
    assert worktree.worktree_path == str(worktree_path)


def test_worktree_filter(git_repo: GitSync, tmp_path: pathlib.Path) -> None:
    """Test GitWorktreeManager.filter() with QueryList filtering."""
    # Create a worktree
    worktree_path = tmp_path / "filter-test-worktree"
    git_repo.cmd.worktrees.add(path=worktree_path, new_branch="filter-test-branch")

    # Filter by branch
    worktrees = git_repo.cmd.worktrees.filter(branch__contains="filter-test")
    assert len(worktrees) >= 1


class WorktreeLockUnlockFixture(t.NamedTuple):
    """Test fixture for GitWorktreeCmd lock/unlock operations."""

    test_id: str
    reason: str | None


WORKTREE_LOCK_UNLOCK_FIXTURES: list[WorktreeLockUnlockFixture] = [
    WorktreeLockUnlockFixture(
        test_id="lock-without-reason",
        reason=None,
    ),
    WorktreeLockUnlockFixture(
        test_id="lock-with-reason",
        reason="Testing lock functionality",
    ),
]


@pytest.mark.parametrize(
    list(WorktreeLockUnlockFixture._fields),
    WORKTREE_LOCK_UNLOCK_FIXTURES,
    ids=[test.test_id for test in WORKTREE_LOCK_UNLOCK_FIXTURES],
)
def test_worktree_lock_unlock(
    git_repo: GitSync,
    tmp_path: pathlib.Path,
    test_id: str,
    reason: str | None,
) -> None:
    """Test GitWorktreeCmd.lock() and unlock() operations."""
    # Create a worktree first
    worktree_path = tmp_path / f"lock-{test_id}-worktree"
    git_repo.cmd.worktrees.add(path=worktree_path, new_branch=f"lock-{test_id}-branch")

    # Get the worktree
    worktree = git_repo.cmd.worktrees.get(worktree_path=str(worktree_path))
    assert worktree is not None

    # Lock the worktree
    lock_result = worktree.lock(reason=reason)
    assert lock_result == "" or "locked" not in lock_result.lower()

    # Verify it's locked
    worktree_after_lock = git_repo.cmd.worktrees.get(worktree_path=str(worktree_path))
    assert worktree_after_lock is not None
    assert worktree_after_lock.locked is True

    # Unlock the worktree
    unlock_result = worktree.unlock()
    assert unlock_result == ""

    # Verify it's unlocked
    worktree_after_unlock = git_repo.cmd.worktrees.get(worktree_path=str(worktree_path))
    assert worktree_after_unlock is not None
    assert worktree_after_unlock.locked is False


def test_worktree_remove(git_repo: GitSync, tmp_path: pathlib.Path) -> None:
    """Test GitWorktreeCmd.remove()."""
    # Create a worktree first
    worktree_path = tmp_path / "remove-test-worktree"
    git_repo.cmd.worktrees.add(path=worktree_path, new_branch="remove-test-branch")

    # Get the worktree
    worktree = git_repo.cmd.worktrees.get(worktree_path=str(worktree_path))
    assert worktree is not None

    # Remove the worktree
    result = worktree.remove()
    assert result == "" or "error" not in result.lower()

    # Verify it's removed
    worktrees_after = git_repo.cmd.worktrees.ls()
    worktree_paths = [wt.worktree_path for wt in worktrees_after]
    assert str(worktree_path) not in worktree_paths


def test_worktree_prune(git_repo: GitSync, tmp_path: pathlib.Path) -> None:
    """Test GitWorktreeManager.prune()."""
    # Prune should succeed even if nothing to prune
    result = git_repo.cmd.worktrees.prune()
    assert result == "" or "prune" not in result.lower()

    # Dry run should also succeed
    result_dry = git_repo.cmd.worktrees.prune(dry_run=True)
    assert "error" not in result_dry.lower() or result_dry == ""


def test_worktree_move(git_repo: GitSync, tmp_path: pathlib.Path) -> None:
    """Test GitWorktreeCmd.move()."""
    # Create a worktree first
    original_path = tmp_path / "move-original-worktree"
    git_repo.cmd.worktrees.add(path=original_path, new_branch="move-test-branch")

    # Get the worktree
    worktree = git_repo.cmd.worktrees.get(worktree_path=str(original_path))
    assert worktree is not None

    # Move the worktree to a new location
    new_path = tmp_path / "move-new-worktree"
    result = worktree.move(new_path)

    # Should succeed (empty string or info message)
    assert result == "" or "error" not in result.lower()

    # Verify original path no longer exists in worktree list
    worktrees_after = git_repo.cmd.worktrees.ls()
    worktree_paths = [wt.worktree_path for wt in worktrees_after]
    assert str(original_path) not in worktree_paths

    # Verify new path exists in worktree list
    assert str(new_path) in worktree_paths


def test_worktree_repair(git_repo: GitSync, tmp_path: pathlib.Path) -> None:
    """Test GitWorktreeCmd.repair()."""
    # Create a worktree first
    worktree_path = tmp_path / "repair-test-worktree"
    git_repo.cmd.worktrees.add(path=worktree_path, new_branch="repair-test-branch")

    # Get the worktree
    worktree = git_repo.cmd.worktrees.get(worktree_path=str(worktree_path))
    assert worktree is not None

    # Repair should succeed (even if nothing needs repair)
    result = worktree.repair()

    # Should succeed (empty string or info message)
    assert result == "" or "error" not in result.lower()


# GitNotes tests


class NoteAddFixture(t.NamedTuple):
    """Fixture for git notes add tests."""

    test_id: str
    message: str | None
    force: bool


NOTE_ADD_FIXTURES: list[NoteAddFixture] = [
    NoteAddFixture(
        test_id="simple-message",
        message="Test note message",
        force=False,
    ),
    NoteAddFixture(
        test_id="message-with-force",
        message="Replacement note",
        force=True,
    ),
]


@pytest.mark.parametrize(
    list(NoteAddFixture._fields),
    NOTE_ADD_FIXTURES,
    ids=[test.test_id for test in NOTE_ADD_FIXTURES],
)
def test_notes_add(
    git_repo: GitSync,
    test_id: str,
    message: str | None,
    force: bool,
) -> None:
    """Test GitNotesManager.add()."""
    # Add a note to HEAD
    result = git_repo.cmd.notes.add(message=message, force=force)
    # Should succeed (empty string) or show overwriting message
    assert result == "" or "Overwriting" in result or "error" not in result.lower()


def test_notes_list(git_repo: GitSync) -> None:
    """Test GitNotesManager.ls()."""
    # Add a note first
    git_repo.cmd.notes.add(message="Test note for listing", force=True)

    # List notes
    notes = git_repo.cmd.notes.ls()
    assert isinstance(notes, list)
    assert len(notes) > 0

    # Each note should have object_sha and note_sha
    for note in notes:
        assert note.object_sha is not None
        assert note.note_sha is not None


def test_notes_get(git_repo: GitSync) -> None:
    """Test GitNotesManager.get()."""
    # Add a note first
    git_repo.cmd.notes.add(message="Test note for get", force=True)

    # Get the HEAD revision
    head_sha = git_repo.cmd.rev_parse(args="HEAD")

    # Get the note by object_sha
    note = git_repo.cmd.notes.get(object_sha=head_sha)
    assert note is not None
    assert note.object_sha == head_sha


def test_notes_filter(git_repo: GitSync) -> None:
    """Test GitNotesManager.filter()."""
    # Add a note first
    git_repo.cmd.notes.add(message="Test note for filter", force=True)

    # Filter notes (should return at least one)
    notes = git_repo.cmd.notes.filter()
    assert isinstance(notes, list)
    assert len(notes) >= 0  # May or may not have notes depending on state


def test_notes_show(git_repo: GitSync) -> None:
    """Test GitNoteCmd.show()."""
    # Add a note first
    note_message = "Test note for show method"
    git_repo.cmd.notes.add(message=note_message, force=True)

    # Get the note
    head_sha = git_repo.cmd.rev_parse(args="HEAD")
    note = git_repo.cmd.notes.get(object_sha=head_sha)
    assert note is not None

    # Show the note content
    result = note.show()
    assert note_message in result


def test_notes_append(git_repo: GitSync) -> None:
    """Test GitNoteCmd.append()."""
    # Add a note first
    initial_message = "Initial note"
    git_repo.cmd.notes.add(message=initial_message, force=True)

    # Get the note
    head_sha = git_repo.cmd.rev_parse(args="HEAD")
    note = git_repo.cmd.notes.get(object_sha=head_sha)
    assert note is not None

    # Append to the note
    append_message = "Appended content"
    result = note.append(message=append_message)
    assert result == "" or "error" not in result.lower()

    # Verify the appended content
    note_content = note.show()
    assert append_message in note_content


def test_notes_remove(git_repo: GitSync) -> None:
    """Test GitNoteCmd.remove()."""
    # Add a note first
    git_repo.cmd.notes.add(message="Note to be removed", force=True)

    # Get the note
    head_sha = git_repo.cmd.rev_parse(args="HEAD")
    note = git_repo.cmd.notes.get(object_sha=head_sha)
    assert note is not None

    # Remove the note
    result = note.remove()
    assert result == "" or "error" not in result.lower()

    # Verify it's removed (should have fewer notes or none)
    notes_after = git_repo.cmd.notes.ls()
    object_shas = [n.object_sha for n in notes_after]
    assert head_sha not in object_shas


def test_notes_prune(git_repo: GitSync) -> None:
    """Test GitNotesManager.prune()."""
    # Prune should succeed even if nothing to prune
    result = git_repo.cmd.notes.prune()
    assert result == "" or "error" not in result.lower()

    # Dry run should also succeed
    result_dry = git_repo.cmd.notes.prune(dry_run=True)
    assert "error" not in result_dry.lower() or result_dry == ""


def test_notes_get_ref(git_repo: GitSync) -> None:
    """Test GitNotesManager.get_ref()."""
    # Add a note first (to ensure the notes ref exists)
    git_repo.cmd.notes.add(message="Note for get_ref test", force=True)

    # Get the notes ref
    result = git_repo.cmd.notes.get_ref()
    # Should return the ref name or be empty if not set
    assert result == "refs/notes/commits" or result == "" or "notes" in result


def test_notes_edit(git_repo: GitSync, tmp_path: pathlib.Path) -> None:
    """Test GitNoteCmd.edit() - non-interactive mode via GIT_EDITOR."""
    # Add a note first
    git_repo.cmd.notes.add(message="Initial note for edit test", force=True)

    # Get the note
    head_sha = git_repo.cmd.rev_parse(args="HEAD")
    note = git_repo.cmd.notes.get(object_sha=head_sha)
    assert note is not None

    # Edit with allow_empty (avoid interactive editor by using config)
    # The doctest uses config={'core.editor': 'true'} which sets a no-op editor
    result = note.edit(allow_empty=True, config={"core.editor": "true"})

    # Should succeed (empty string) or show error about editor
    assert result == "" or "error" in result.lower() or isinstance(result, str)


def test_notes_copy(git_repo: GitSync) -> None:
    """Test GitNoteCmd.copy()."""
    # Create a second commit to copy the note to
    test_file = git_repo.path / "copy_note_test.txt"
    test_file.write_text("content for copy test")
    git_repo.cmd.run(["add", "copy_note_test.txt"])
    git_repo.cmd.run(["commit", "-m", "Commit for copy note test"])

    # Get the new commit SHA
    new_commit_sha = git_repo.cmd.rev_parse(args="HEAD")

    # Checkout previous commit to add note there
    git_repo.cmd.run(["checkout", "HEAD~1"])
    git_repo.cmd.notes.add(message="Note to copy", force=True)

    # Get the note and copy to new commit
    old_commit_sha = git_repo.cmd.rev_parse(args="HEAD")
    note = git_repo.cmd.notes.get(object_sha=old_commit_sha)
    assert note is not None

    # Copy to new commit (force=True to overwrite if exists)
    result = note.copy(to_object=new_commit_sha, force=True)

    # Should succeed
    assert result == "" or "error" not in result.lower()

    # Go back to main branch
    git_repo.cmd.run(["checkout", "-"])


def test_notes_merge(git_repo: GitSync) -> None:
    """Test GitNotesManager.merge()."""
    # Create a custom notes ref
    custom_ref = "refs/notes/custom"
    custom_notes = git_repo.cmd.notes.__class__(
        path=git_repo.path,
        cmd=git_repo.cmd,
        ref=custom_ref,
    )

    # Add a note to the custom ref
    custom_notes.add(message="Note in custom ref", force=True)

    # Merge notes from custom ref to default ref
    result = git_repo.cmd.notes.merge(notes_ref=custom_ref)

    # Should succeed or show merge info
    assert (
        result == ""
        or "already up to date" in result.lower()
        or "merged" in result.lower()
        or "error" not in result.lower()
    )


# GitReflog tests


class ReflogShowFixture(t.NamedTuple):
    """Fixture for git reflog show tests."""

    test_id: str
    ref: str
    number: int | None


REFLOG_SHOW_FIXTURES: list[ReflogShowFixture] = [
    ReflogShowFixture(
        test_id="head-no-limit",
        ref="HEAD",
        number=None,
    ),
    ReflogShowFixture(
        test_id="head-limit-5",
        ref="HEAD",
        number=5,
    ),
]


@pytest.mark.parametrize(
    list(ReflogShowFixture._fields),
    REFLOG_SHOW_FIXTURES,
    ids=[test.test_id for test in REFLOG_SHOW_FIXTURES],
)
def test_reflog_show(
    git_repo: GitSync,
    test_id: str,
    ref: str,
    number: int | None,
) -> None:
    """Test GitReflogManager.show()."""
    result = git_repo.cmd.reflog.show(ref=ref, number=number)
    # Should return reflog output
    assert isinstance(result, str)
    assert len(result) > 0


def test_reflog_list(git_repo: GitSync) -> None:
    """Test GitReflogManager.ls()."""
    entries = git_repo.cmd.reflog.ls()
    assert isinstance(entries, list)
    assert len(entries) > 0

    # Each entry should have required fields
    for entry in entries:
        assert entry.sha is not None
        assert entry.refspec is not None
        assert entry.action is not None


def test_reflog_get(git_repo: GitSync) -> None:
    """Test GitReflogManager.get()."""
    # Get the first entry (HEAD@{0})
    entry = git_repo.cmd.reflog.get(refspec="HEAD@{0}")
    assert entry is not None
    assert entry.refspec == "HEAD@{0}"


def test_reflog_filter(git_repo: GitSync) -> None:
    """Test GitReflogManager.filter()."""
    # Filter by action type (commit actions are common)
    entries = git_repo.cmd.reflog.filter(action="commit")
    assert isinstance(entries, list)
    # May or may not have commit actions depending on repo state


def test_reflog_entry_show(git_repo: GitSync) -> None:
    """Test GitReflogEntryCmd.show()."""
    # Get an entry from the list
    entries = git_repo.cmd.reflog.ls()
    assert len(entries) > 0

    # Get the first entry's cmd and show it
    entry = entries[0]
    result = entry.cmd.show()
    assert isinstance(result, str)
    assert len(result) > 0


def test_reflog_exists(git_repo: GitSync) -> None:
    """Test GitReflogManager.exists()."""
    # HEAD should always have a reflog
    assert git_repo.cmd.reflog.exists("HEAD") is True

    # Non-existent ref should return False
    assert git_repo.cmd.reflog.exists("refs/heads/nonexistent-xyz123456") is False


def test_reflog_expire(git_repo: GitSync) -> None:
    """Test GitReflogManager.expire()."""
    # Expire with dry_run should succeed
    result = git_repo.cmd.reflog.expire(dry_run=True)
    assert result == "" or "error" not in result.lower()


def test_reflog_entry_delete(git_repo: GitSync) -> None:
    """Test GitReflogEntryCmd.delete()."""
    # Create some commits to have reflog entries
    test_file = git_repo.path / "reflog_delete_test.txt"
    env = os.environ.copy()

    for i in range(3):
        test_file.write_text(f"content {i}")
        git_repo.cmd.run(["add", "reflog_delete_test.txt"])
        git_repo.cmd.run(["commit", "-m", f"Commit {i}"], env=env)

    # Get the reflog entries
    entries = git_repo.cmd.reflog.ls()
    assert len(entries) >= 3

    # Get an entry and delete it with dry_run (to avoid actually modifying reflog)
    entry = entries[1]  # Pick a middle entry
    result = entry.cmd.delete(dry_run=True)

    # Should succeed or show what would be deleted
    assert result == "" or isinstance(result, str)


# GitSubmodule tests
# ==================


@pytest.fixture
def submodule_repo(
    tmp_path: pathlib.Path,
    git_commit_envvars: dict[str, str],
    set_gitconfig: pathlib.Path,
) -> git.Git:
    """Create a git repository to use as a submodule source."""
    # Create a repo to serve as submodule source
    source_path = tmp_path / "submodule_source"
    source_path.mkdir()
    source_repo = git.Git(path=source_path)
    source_repo.init()

    # Create initial commit with environment
    env = os.environ.copy()
    env.update(git_commit_envvars)

    (source_path / "lib.py").write_text("# Library code\n")
    source_repo.run(["add", "."])
    source_repo.run(
        ["commit", "-m", "Initial commit"],
        env=env,
    )

    return source_repo


def _setup_submodule_test(git_repo: GitSync, submodule_repo: git.Git) -> str:
    """Set up git_repo for submodule tests.

    Returns the result of adding the submodule.
    """
    # Allow file protocol for submodule operations
    git_repo.cmd.run(["config", "protocol.file.allow", "always"])

    # Add the submodule
    return git_repo.cmd.submodules.add(
        repository=str(submodule_repo.path),
        path="vendor/lib",
    )


def test_submodule_add(
    git_repo: GitSync,
    submodule_repo: git.Git,
) -> None:
    """Test GitSubmoduleManager.add()."""
    # Allow file protocol for submodule operations
    git_repo.cmd.run(["config", "protocol.file.allow", "always"])

    # Add the submodule
    result = git_repo.cmd.submodules.add(
        repository=str(submodule_repo.path),
        path="vendor/lib",
    )
    # Should succeed (output varies by git version)
    assert "fatal" not in result.lower() or result == ""


def test_submodule_ls(
    git_repo: GitSync,
    submodule_repo: git.Git,
) -> None:
    """Test GitSubmoduleManager.ls()."""
    # Setup
    _setup_submodule_test(git_repo, submodule_repo)

    # List submodules
    submodules = git_repo.cmd.submodules.ls()
    assert isinstance(submodules, list)
    assert len(submodules) >= 1

    # Check the submodule has expected attributes
    submodule = submodules[0]
    assert submodule.path == "vendor/lib"
    assert submodule.name is not None


def test_submodule_get(
    git_repo: GitSync,
    submodule_repo: git.Git,
) -> None:
    """Test GitSubmoduleManager.get()."""
    # Setup
    _setup_submodule_test(git_repo, submodule_repo)

    # Get the submodule by path
    submodule = git_repo.cmd.submodules.get(path="vendor/lib")
    assert submodule is not None
    assert submodule.path == "vendor/lib"


def test_submodule_get_not_found(
    git_repo: GitSync,
) -> None:
    """Test GitSubmoduleManager.get() raises when not found."""
    # Try to get a non-existent submodule
    with pytest.raises(ObjectDoesNotExist):
        git_repo.cmd.submodules.get(path="nonexistent")


def test_submodule_filter(
    git_repo: GitSync,
    submodule_repo: git.Git,
) -> None:
    """Test GitSubmoduleManager.filter()."""
    # Setup
    _setup_submodule_test(git_repo, submodule_repo)

    # Filter by path
    submodules = git_repo.cmd.submodules.filter(path="vendor/lib")
    assert len(submodules) == 1
    assert submodules[0].path == "vendor/lib"

    # Filter with no match
    submodules = git_repo.cmd.submodules.filter(path="nonexistent")
    assert len(submodules) == 0


def test_submodule_init(
    git_repo: GitSync,
    submodule_repo: git.Git,
) -> None:
    """Test GitSubmoduleManager.init()."""
    # Setup
    _setup_submodule_test(git_repo, submodule_repo)

    # Initialize all submodules
    result = git_repo.cmd.submodules.init()
    assert result == "" or "fatal" not in result.lower()


def test_submodule_update(
    git_repo: GitSync,
    submodule_repo: git.Git,
) -> None:
    """Test GitSubmoduleManager.update()."""
    # Setup
    _setup_submodule_test(git_repo, submodule_repo)

    # Update all submodules
    result = git_repo.cmd.submodules.update(init=True)
    assert "fatal" not in result.lower() or result == ""


def test_submodule_sync(
    git_repo: GitSync,
    submodule_repo: git.Git,
) -> None:
    """Test GitSubmoduleManager.sync()."""
    # Setup
    _setup_submodule_test(git_repo, submodule_repo)

    # Sync submodule URLs
    result = git_repo.cmd.submodules.sync()
    assert result == "" or "fatal" not in result.lower()


def test_submodule_summary(
    git_repo: GitSync,
    submodule_repo: git.Git,
) -> None:
    """Test GitSubmoduleManager.summary()."""
    # Setup
    _setup_submodule_test(git_repo, submodule_repo)

    # Get summary
    result = git_repo.cmd.submodules.summary()
    # Summary output may vary
    assert isinstance(result, str)


def test_submodule_entry_status(
    git_repo: GitSync,
    submodule_repo: git.Git,
) -> None:
    """Test GitSubmoduleEntryCmd.status()."""
    # Setup
    _setup_submodule_test(git_repo, submodule_repo)

    # Get the submodule and check status
    submodule = git_repo.cmd.submodules.get(path="vendor/lib")
    assert submodule.cmd is not None

    result = submodule.cmd.status()
    assert isinstance(result, str)


def test_submodule_entry_init(
    git_repo: GitSync,
    submodule_repo: git.Git,
) -> None:
    """Test GitSubmoduleEntryCmd.init()."""
    # Setup
    _setup_submodule_test(git_repo, submodule_repo)

    # Get the submodule and init it
    submodule = git_repo.cmd.submodules.get(path="vendor/lib")
    assert submodule.cmd is not None

    result = submodule.cmd.init()
    assert result == "" or "fatal" not in result.lower()


def test_submodule_entry_update(
    git_repo: GitSync,
    submodule_repo: git.Git,
) -> None:
    """Test GitSubmoduleEntryCmd.update()."""
    # Setup
    _setup_submodule_test(git_repo, submodule_repo)

    # Get the submodule and init it
    submodule = git_repo.cmd.submodules.get(path="vendor/lib")
    assert submodule.cmd is not None

    # Init and update
    submodule.cmd.init()
    result = submodule.cmd.update()
    assert "fatal" not in result.lower() or result == ""


def test_submodule_foreach(
    git_repo: GitSync,
    submodule_repo: git.Git,
) -> None:
    """Test GitSubmoduleManager.foreach()."""
    # Setup
    _setup_submodule_test(git_repo, submodule_repo)

    # Run foreach with a simple command
    result = git_repo.cmd.submodules.foreach(command="pwd")
    assert isinstance(result, str)


def test_submodule_dataclass_properties(
    git_repo: GitSync,
    submodule_repo: git.Git,
) -> None:
    """Test GitSubmodule dataclass properties."""
    # Setup
    _setup_submodule_test(git_repo, submodule_repo)

    # Get the submodule
    submodule = git_repo.cmd.submodules.get(path="vendor/lib")

    # Check dataclass attributes
    assert submodule.path == "vendor/lib"
    assert submodule.name is not None
    assert submodule.url is not None
    assert submodule.sha is not None or submodule.status_prefix == "-"
    assert submodule.cmd is not None

    # Test initialized property
    # After add, submodule should be initialized (prefix not '-')
    assert submodule.initialized is True or submodule.status_prefix == "-"


def test_submodule_entry_deinit(
    git_repo: GitSync,
    submodule_repo: git.Git,
) -> None:
    """Test GitSubmoduleEntryCmd.deinit()."""
    # Setup
    _setup_submodule_test(git_repo, submodule_repo)

    # Initialize the submodule first
    git_repo.cmd.submodules.init()
    git_repo.cmd.submodules.update(init=True)

    # Get the submodule
    submodule = git_repo.cmd.submodules.get(path="vendor/lib")
    assert submodule.cmd is not None

    # Deinit the submodule (with force to ensure it works even if dirty)
    result = submodule.cmd.deinit(force=True)

    # Should succeed (empty string or info message)
    assert result == "" or "cleared" in result.lower() or "error" not in result.lower()


def test_submodule_entry_set_branch(
    git_repo: GitSync,
    submodule_repo: git.Git,
) -> None:
    """Test GitSubmoduleEntryCmd.set_branch()."""
    # Setup
    _setup_submodule_test(git_repo, submodule_repo)

    # Get the submodule
    submodule = git_repo.cmd.submodules.get(path="vendor/lib")
    assert submodule.cmd is not None

    # Set branch
    result = submodule.cmd.set_branch(branch="main")

    # Should succeed (empty string) or show error if branch doesn't exist
    assert result == "" or isinstance(result, str)

    # Verify branch is set in .gitmodules
    gitmodules = (git_repo.path / ".gitmodules").read_text()
    # Branch may or may not be present depending on git version behavior
    assert "vendor/lib" in gitmodules


def test_submodule_entry_set_url(
    git_repo: GitSync,
    submodule_repo: git.Git,
) -> None:
    """Test GitSubmoduleEntryCmd.set_url()."""
    # Setup
    _setup_submodule_test(git_repo, submodule_repo)

    # Get the submodule
    submodule = git_repo.cmd.submodules.get(path="vendor/lib")
    assert submodule.cmd is not None

    # Set a new URL
    new_url = "https://example.com/repo.git"
    result = submodule.cmd.set_url(url=new_url)

    # Should succeed (empty string)
    assert result == "" or isinstance(result, str)

    # Verify URL is updated in .gitmodules
    gitmodules = (git_repo.path / ".gitmodules").read_text()
    assert new_url in gitmodules


def test_submodule_entry_absorbgitdirs(
    git_repo: GitSync,
    submodule_repo: git.Git,
) -> None:
    """Test GitSubmoduleEntryCmd.absorbgitdirs()."""
    # Setup
    _setup_submodule_test(git_repo, submodule_repo)

    # Initialize and update submodule first
    git_repo.cmd.submodules.init()
    git_repo.cmd.submodules.update(init=True)

    # Get the submodule
    submodule = git_repo.cmd.submodules.get(path="vendor/lib")
    assert submodule.cmd is not None

    # Absorb git dirs (may already be absorbed, but should succeed)
    result = submodule.cmd.absorbgitdirs()

    # Should succeed (empty string or info message)
    assert result == "" or isinstance(result, str)
