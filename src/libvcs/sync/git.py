"""Tool to manage a local git clone from an external git repository.

.. todo::

    From https://github.com/saltstack/salt (Apache License):

    - [`GitSync.remote`](libvcs.git.GitProject.remote) (renamed to ``remote``)
    - [`GitSync.remote`](libvcs.git.GitProject.remote_set) (renamed to ``set_remote``)

    From pip (MIT Licnese):

    - [`GitSync.remote`](libvcs.git.GitProject.remote_set) (renamed to ``set_remote``)
    - [`GitSync.convert_pip_url`](libvcs.git.GitProject.convert_pip_url`) (``get_url_rev``)
    - [`GitSync.get_revision`](libvcs.git.GitProject.get_revision)
    - [`GitSync.get_git_version`](libvcs.git.GitProject.get_git_version)
"""  # NOQA: E501

from __future__ import annotations

import dataclasses
import logging
import pathlib
import re
import typing as t
from urllib import parse as urlparse

from libvcs import exc
from libvcs.cmd.git import Git
from libvcs.sync.base import (
    BaseSync,
    VCSLocation,
    convert_pip_url as base_convert_pip_url,
)

if t.TYPE_CHECKING:
    from libvcs._internal.types import StrPath

logger = logging.getLogger(__name__)


class GitStatusParsingException(exc.LibVCSException):
    """Raised when git status output is not in the expected format."""

    def __init__(self, git_status_output: str, *args: object) -> None:
        return super().__init__(
            "Could not find match for git-status(1)" + f"Output: {git_status_output}",
        )


class GitRemoteOriginMissing(exc.LibVCSException):
    """Raised when git origin remote was not found."""

    def __init__(self, remotes: list[str], *args: object) -> None:
        return super().__init__(f"Missing origin. Remotes: {', '.join(remotes)}")


class GitRemoteSetError(exc.LibVCSException):
    """Raised when a git remote could not be set."""

    def __init__(self, remote_name: str) -> None:
        return super().__init__(f"Remote {remote_name} not found after setting")


class GitNoBranchFound(exc.LibVCSException):
    """Raised with git branch could not be found."""

    def __init__(self, *args: object) -> None:
        return super().__init__("No branch found for git repository")


class GitRemoteRefNotFound(exc.CommandError):
    """Raised when a git remote ref (tag, branch) could not be found."""

    def __init__(self, git_tag: str, ref_output: str, *args: object) -> None:
        return super().__init__(
            f"Could not fetch remote in refs/remotes/{git_tag}. Output: {ref_output}",
        )


@dataclasses.dataclass
class GitRemote:
    """Structure containing git working copy information."""

    name: str
    fetch_url: str
    push_url: str


GitSyncRemoteDict = dict[str, GitRemote]
GitRemotesArgs = t.Union[None, GitSyncRemoteDict, dict[str, str]]


@dataclasses.dataclass
class GitStatus:
    """Git status information."""

    branch_oid: str | None = None
    branch_head: str | None = None
    branch_upstream: str | None = None
    branch_ab: str | None = None
    branch_ahead: str | None = None
    branch_behind: str | None = None

    @classmethod
    def from_stdout(cls, value: str) -> GitStatus:
        """Return ``git status -sb --porcelain=2`` extracted to a dict.

        Returns
        -------
        Dictionary of git repo's status
        """
        pattern = re.compile(
            r"""[\n\r]?
            (
                #
                \W+
                branch.oid\W+
                (?P<branch_oid>
                    [a-f0-9]{40}
                )
            )?
            (
                #
                \W+
                branch.head
                [\W]+
                (?P<branch_head>
                    .*
                )

            )?
            (
                #
                \W+
                branch.upstream
                [\W]+
                (?P<branch_upstream>
                    .*
                )
            )?
            (
                #
                \W+
                branch.ab
                [\W]+
                (?P<branch_ab>
                    \+(?P<branch_ahead>\d+)
                    \W{1}
                    \-(?P<branch_behind>\d+)
                )
            )?
            """,
            re.VERBOSE | re.MULTILINE,
        )
        matches = pattern.search(value)

        if matches is None:
            raise GitStatusParsingException(git_status_output=value)
        return cls(**matches.groupdict())


def convert_pip_url(pip_url: str) -> VCSLocation:
    """Convert pip-style URL to a VCSLocation.

    Prefixes stub URLs like 'user@hostname:user/repo.git' with 'ssh://'.
    That's required because although they use SSH they sometimes doesn't
    work with a ssh:// scheme (e.g. Github). But we need a scheme for
    parsing. Hence we remove it again afterwards and return it as a stub.
    The manpage for git-clone(1) refers to this as the "scp-like styntax".
    """
    if "://" not in pip_url:
        assert "file:" not in pip_url
        pip_url = pip_url.replace("git+", "git+ssh://")
        url, rev = base_convert_pip_url(pip_url)
        url = url.replace("ssh://", "")
    elif "github.com:" in pip_url:
        msg = (
            "Repo {} is malformatted, please use the convention {} for "
            "ssh / private GitHub repositories.".format(
                pip_url,
                "git+https://github.com/username/repo.git",
            )
        )
        raise exc.LibVCSException(
            msg,
        )
    else:
        url, rev = base_convert_pip_url(pip_url)

    return VCSLocation(url=url, rev=rev)


class GitSync(BaseSync):
    """Tool to manage a local git clone from an external git repository."""

    bin_name = "git"
    schemes = ("git+http", "git+https", "git+file")
    cmd: Git
    _remotes: GitSyncRemoteDict

    def __init__(
        self,
        *,
        url: str,
        path: StrPath,
        remotes: GitRemotesArgs = None,
        **kwargs: t.Any,
    ) -> None:
        """Local git repository.

        Parameters
        ----------
        url : str
            URL of repo

        tls_verify : bool
            Should certificate for https be checked (default False)

        Examples
        --------
        .. code-block:: python

            import os
            from libvcs.sync.git import GitSync

            checkout = pathlib.Path(__name__) + '/' + 'my_libvcs'

            repo = GitSync(
               url="https://github.com/vcs-python/libvcs",
               path=checkout,
               remotes={
                   'gitlab': 'https://gitlab.com/vcs-python/libvcs'
               }
            )

        .. code-block:: python

            import os
            from libvcs.sync.git import GitSync

            checkout = pathlib.Path(__name__) + '/' + 'my_libvcs'

            repo = GitSync(
               url="https://github.com/vcs-python/libvcs",
               path=checkout,
               remotes={
                   'gitlab': {
                       'fetch_url': 'https://gitlab.com/vcs-python/libvcs',
                       'push_url': 'https://gitlab.com/vcs-python/libvcs',
                   },
               }
            )
        """
        if "git_shallow" not in kwargs:
            self.git_shallow = False
        if "tls_verify" not in kwargs:
            self.tls_verify = False

        self._remotes: GitSyncRemoteDict

        if remotes is None:
            self._remotes: GitSyncRemoteDict = {
                "origin": GitRemote(name="origin", fetch_url=url, push_url=url),
            }
        elif isinstance(remotes, dict):
            self._remotes = {}
            for remote_name, remote_url in remotes.items():
                if isinstance(remote_url, str):
                    self._remotes[remote_name] = GitRemote(
                        name=remote_name,
                        fetch_url=remote_url,
                        push_url=remote_url,
                    )
                elif isinstance(remote_url, dict):
                    self._remotes[remote_name] = GitRemote(
                        fetch_url=remote_url["fetch_url"],
                        push_url=remote_url["push_url"],
                        name=remote_name,
                    )
                elif isinstance(remote_url, GitRemote):
                    self._remotes[remote_name] = remote_url

        if url and "origin" not in self._remotes:
            self._remotes["origin"] = GitRemote(
                name="origin",
                fetch_url=url,
                push_url=url,
            )
        super().__init__(url=url, path=path, **kwargs)

        self.cmd = Git(path=path, progress_callback=self.progress_callback)

        origin = (
            self._remotes.get("origin")
            if "origin" in self._remotes
            else next(iter(self._remotes.items()))[1]
        )
        if origin is None:
            raise GitRemoteOriginMissing(remotes=list(self._remotes.keys()))
        self.url = self.chomp_protocol(origin.fetch_url)

    @classmethod
    def from_pip_url(cls, pip_url: str, **kwargs: t.Any) -> GitSync:
        """Clone a git repository from a pip-style URL."""
        url, rev = convert_pip_url(pip_url)
        return cls(url=url, rev=rev, **kwargs)

    def get_revision(self) -> str:
        """Return current revision. Initial repositories return 'initial'."""
        try:
            return self.cmd.rev_parse(verify=True, args="HEAD", check_returncode=True)
        except exc.CommandError:
            return "initial"

    def set_remotes(self, overwrite: bool = False) -> None:
        """Apply remotes in local repository to match GitSync's configuration."""
        remotes = self._remotes
        if isinstance(remotes, dict):
            for remote_name, git_remote_repo in remotes.items():
                existing_remote = self.remote(remote_name)
                if isinstance(git_remote_repo, GitRemote):
                    if (
                        not existing_remote
                        or existing_remote.fetch_url != git_remote_repo.fetch_url
                    ):
                        self.set_remote(
                            name=remote_name,
                            url=git_remote_repo.fetch_url,
                            overwrite=overwrite,
                        )
                        # refresh if we're setting it, so push can be checked
                        existing_remote = self.remote(remote_name)
                    if git_remote_repo.push_url and (
                        not existing_remote
                        or existing_remote.push_url != git_remote_repo.push_url
                    ):
                        self.set_remote(
                            name=remote_name,
                            url=git_remote_repo.push_url,
                            push=True,
                            overwrite=overwrite,
                        )
                elif (
                    not existing_remote
                    or existing_remote.fetch_url != git_remote_repo.fetch_url
                ):
                    self.set_remote(
                        name=remote_name,
                        url=git_remote_repo.fetch_url,
                        overwrite=overwrite,
                    )

    def obtain(self, *args: t.Any, **kwargs: t.Any) -> None:
        """Retrieve the repository, clone if doesn't exist."""
        self.ensure_dir()

        url = self.url

        self.log.info("Cloning.")
        self.cmd.clone(
            url=url,
            progress=True,
            depth=1 if self.git_shallow else None,
            config={"http.sslVerify": False} if self.tls_verify else None,
            log_in_real_time=True,
        )

        self.log.info("Initializing submodules.")
        self.cmd.submodule.init(
            log_in_real_time=True,
        )
        self.cmd.submodule.update(
            init=True,
            recursive=True,
            log_in_real_time=True,
        )

        self.set_remotes(overwrite=True)

    def update_repo(
        self,
        set_remotes: bool = False,
        *args: t.Any,
        **kwargs: t.Any,
    ) -> None:
        """Pull latest changes from git remote."""
        self.ensure_dir()

        if not pathlib.Path(self.path / ".git").is_dir():
            self.obtain()
            self.update_repo(set_remotes=set_remotes)
            return

        if set_remotes:
            self.set_remotes(overwrite=True)

        # Get requested revision or tag
        url, git_tag = self.url, getattr(self, "rev", None)

        if not git_tag:
            self.log.debug("No git revision set, defaulting to origin/master")
            symref = self.cmd.symbolic_ref(name="HEAD", short=True)
            git_tag = symref.rstrip() if symref else "origin/master"
        self.log.debug(f"git_tag: {git_tag}")

        self.log.info(f"Updating to '{git_tag}'.")

        # Get head sha
        try:
            head_sha = self.cmd.rev_list(
                commit="HEAD",
                max_count=1,
                check_returncode=True,
            )
        except exc.CommandError:
            self.log.exception("Failed to get the hash for HEAD")
            return

        self.log.debug(f"head_sha: {head_sha}")

        # If a remote ref is asked for, which can possibly move around,
        # we must always do a fetch and checkout.
        show_ref_output = self.cmd.show_ref(pattern=git_tag, check_returncode=False)
        self.log.debug(f"show_ref_output: {show_ref_output}")
        is_remote_ref = "remotes" in show_ref_output
        self.log.debug(f"is_remote_ref: {is_remote_ref}")

        # show-ref output is in the form "<sha> refs/remotes/<remote>/<tag>"
        # we must strip the remote from the tag.
        git_remote_name = self.get_current_remote_name()

        if f"refs/remotes/{git_tag}" in show_ref_output:
            m = re.match(
                r"^[0-9a-f]{40} refs/remotes/"
                r"(?P<git_remote_name>[^/]+)/"
                r"(?P<git_tag>.+)$",
                show_ref_output,
                re.MULTILINE,
            )
            if m is None:
                raise GitRemoteRefNotFound(git_tag=git_tag, ref_output=show_ref_output)
            git_remote_name = m.group("git_remote_name")
            git_tag = m.group("git_tag")
        self.log.debug(f"git_remote_name: {git_remote_name}")
        self.log.debug(f"git_tag: {git_tag}")

        # This will fail if the tag does not exist (it probably has not
        # been fetched yet).
        try:
            error_code = 0
            tag_sha = self.cmd.rev_list(
                commit=git_remote_name + "/" + git_tag if is_remote_ref else git_tag,
                max_count=1,
            )

        except exc.CommandError as e:
            error_code = e.returncode if e.returncode is not None else 0
            tag_sha = ""
        self.log.debug(f"tag_sha: {tag_sha}")

        # Is the hash checkout out what we want?
        somethings_up = (error_code, is_remote_ref, tag_sha != head_sha)
        if all(not x for x in somethings_up):
            self.log.info("Already up-to-date.")
            return

        try:
            process = self.cmd.fetch(log_in_real_time=True, check_returncode=True)
        except exc.CommandError:
            self.log.exception(f"Failed to fetch repository '{url}'")
            return

        if is_remote_ref:
            # Check if stash is needed
            try:
                process = self.cmd.status(porcelain=True, untracked_files="no")
            except exc.CommandError:
                self.log.exception("Failed to get the status")
                return
            need_stash = len(process) > 0

            # If not in clean state, stash changes in order to be able
            # to be able to perform git pull --rebase
            if need_stash:
                # If Git < 1.7.6, uses --quiet --all
                git_stash_save_options = "--quiet"
                try:
                    process = self.cmd.stash.save(message=git_stash_save_options)
                except exc.CommandError:
                    self.log.exception("Failed to stash changes")

            # Checkout the remote branch
            try:
                process = self.cmd.checkout(branch=git_tag)
            except exc.CommandError:
                self.log.exception(f"Failed to checkout tag: '{git_tag}'")
                return

            # Rebase changes from the remote branch
            try:
                process = self.cmd.rebase(upstream=git_remote_name + "/" + git_tag)
            except exc.CommandError as e:
                if any(msg in str(e) for msg in ["invalid_upstream", "Aborting"]):
                    self.log.exception("Invalid upstream remote. Rebase aborted.")
                else:
                    # Rebase failed: Restore previous state.
                    self.cmd.rebase(abort=True)
                    if need_stash:
                        self.cmd.stash.pop(index=True, quiet=True)

                    self.log.exception(
                        f"\nFailed to rebase in: '{self.path}'.\n"
                        "You will have to resolve the conflicts manually",
                    )
                    return

            if need_stash:
                try:
                    process = self.cmd.stash.pop(index=True, quiet=True)
                except exc.CommandError:
                    # Stash pop --index failed: Try again dropping the index
                    self.cmd.reset(hard=True, quiet=True)
                    try:
                        process = self.cmd.stash.pop(quiet=True)
                    except exc.CommandError:
                        # Stash pop failed: Restore previous state.
                        self.cmd.reset(pathspec=head_sha, hard=True, quiet=True)
                        self.cmd.stash.pop(index=True, quiet=True)
                        self.log.exception(
                            f"\nFailed to rebase in: '{self.path}'.\n"
                            "You will have to resolve the "
                            "conflicts manually",
                        )
                        return

        else:
            try:
                process = self.cmd.checkout(branch=git_tag)
            except exc.CommandError:
                self.log.exception(f"Failed to checkout tag: '{git_tag}'")
                return

        self.cmd.submodule.update(recursive=True, init=True, log_in_real_time=True)

    def remotes(self) -> GitSyncRemoteDict:
        """Return remotes like git remote -v.

        Parameters
        ----------
        flat : bool
            Return a dict of ``tuple`` instead of ``dict``, default `False`.

        Returns
        -------
        dict of git upstream / remote URLs
        """
        remotes = {}

        cmd = self.cmd.remote.run()
        ret: filter[str] = filter(None, cmd.split("\n"))

        for remote_name in ret:
            remote = self.remote(remote_name)
            if remote is not None:
                remotes[remote_name] = remote
        return remotes

    def remote(self, name: str, **kwargs: t.Any) -> GitRemote | None:
        """Get the fetch and push URL for a specified remote name.

        Parameters
        ----------
        name : str
            The remote name used to define the fetch and push URL

        Returns
        -------
        Remote name and url in tuple form
        """
        try:
            ret = self.cmd.remote.show(
                name=name,
                no_query_remotes=True,
                log_in_real_time=True,
            )
            lines = ret.split("\n")
            remote_fetch_url = lines[1].replace("Fetch URL: ", "").strip()
            remote_push_url = lines[2].replace("Push  URL: ", "").strip()
            if name not in {remote_fetch_url, remote_push_url}:
                return GitRemote(
                    name=name,
                    fetch_url=remote_fetch_url,
                    push_url=remote_push_url,
                )
        except exc.LibVCSException:
            pass
        return None

    def set_remote(
        self,
        name: str,
        url: str,
        push: bool = False,
        overwrite: bool = False,
    ) -> GitRemote:
        """Set remote with name and URL like git remote add.

        Parameters
        ----------
        name : str
            defines the remote name.

        url : str
            defines the remote URL
        """
        url = self.chomp_protocol(url)

        if self.remote(name) and overwrite:
            self.cmd.remote.set_url(name=name, url=url, check_returncode=True)
        else:
            self.cmd.remote.add(name=name, url=url, check_returncode=True)

        remote = self.remote(name=name)
        if remote is None:
            raise GitRemoteSetError(remote_name=name)
        return remote

    @staticmethod
    def chomp_protocol(url: str) -> str:
        """Return clean VCS url from RFC-style url.

        Parameters
        ----------
        url : str
            PIP-style url

        Returns
        -------
        URL as VCS software would accept it
        """
        if "+" in url:
            url = url.split("+", 1)[1]
        scheme, netloc, path, query, _frag = urlparse.urlsplit(url)
        url = urlparse.urlunsplit((scheme, netloc, path, query, ""))
        if url.startswith("ssh://git@github.com/"):
            url = url.replace("ssh://", "git+ssh://")
        elif "://" not in url:
            assert "file:" not in url
            url = url.replace("git+", "git+ssh://")
            url = url.replace("ssh://", "")
        return url

    def get_git_version(self) -> str:
        """Return current version of git binary.

        Returns
        -------
        git version
        """
        VERSION_PFX = "git version "
        version = self.cmd.version()
        if version.startswith(VERSION_PFX):
            version = version[len(VERSION_PFX) :].split()[0]
        else:
            version = ""
        return ".".join(version.split(".")[:3])

    def status(self) -> GitStatus:
        """Retrieve status of project in dict format.

        Wraps ``git status --sb --porcelain=2``. Does not include changed files, yet.

        Returns
        -------
        Status of current checked out repository

        Examples
        --------
        >>> git_repo = GitSync(
        ...     url=f'file://{create_git_remote_repo()}',
        ...     path=tmp_path
        ... )
        >>> git_repo.obtain()
        >>> git_repo.status()
        GitStatus(\
branch_oid='...', branch_head='master', \
branch_upstream='origin/master', \
branch_ab='+0 -0', \
branch_ahead='0', \
branch_behind='0'\
)
        """
        return GitStatus.from_stdout(
            self.cmd.status(short=True, branch=True, porcelain="2"),
        )

    def get_current_remote_name(self) -> str:
        """Retrieve name of the remote / upstream of currently checked out branch.

        Returns
        -------
        If upstream the same, returns ``branch_name``.
        If upstream mismatches, returns ``remote_name/branch_name``.
        """
        match = self.status()

        if match.branch_upstream is None:  # no upstream set
            if match.branch_head is None:
                raise GitNoBranchFound
            return match.branch_head
        if match.branch_head is None:
            return match.branch_upstream

        return match.branch_upstream.replace("/" + match.branch_head, "")
