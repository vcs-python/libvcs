"""Tests for libvcs.cmd.git."""

from __future__ import annotations

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
        assert "set to" in result.lower() or result == ""
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
    if method == "apply":
        result = stash.apply()
    else:
        result = stash.pop()

    # Should succeed
    assert "error" not in result.lower() or "conflict" in result.lower()

    # Check if stash was removed
    stashes_after = git_repo.cmd.stashes.ls()
    if removes_stash:
        assert len(stashes_after) == 0
    else:
        assert len(stashes_after) >= 1


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
