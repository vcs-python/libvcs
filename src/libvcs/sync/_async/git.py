"""Async tool to manage a local git clone from an external git repository.

Async equivalent of :mod:`libvcs.sync.git`.

Note
----
This is an internal API not covered by versioning policy.
"""

from __future__ import annotations

import pathlib
import re
import typing as t

from libvcs import exc
from libvcs._internal.async_run import AsyncProgressCallbackProtocol
from libvcs._internal.types import StrPath
from libvcs.cmd._async.git import AsyncGit
from libvcs.sync._async.base import AsyncBaseSync
from libvcs.sync.base import VCSLocation, convert_pip_url as base_convert_pip_url
from libvcs.sync.git import (
    GitRemote,
    GitRemoteOriginMissing,
    GitRemoteRefNotFound,
    GitRemotesArgs,
    GitRemoteSetError,
    GitStatus,
    GitSyncRemoteDict,
)


def convert_pip_url(pip_url: str) -> VCSLocation:
    """Convert pip-style URL to a VCSLocation.

    Prefixes stub URLs like 'user@hostname:user/repo.git' with 'ssh://'.
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
        raise exc.LibVCSException(msg)
    else:
        url, rev = base_convert_pip_url(pip_url)

    return VCSLocation(url=url, rev=rev)


class AsyncGitSync(AsyncBaseSync):
    """Async tool to manage a local git clone from an external git repository.

    Async equivalent of :class:`~libvcs.sync.git.GitSync`.

    Examples
    --------
    >>> import asyncio
    >>> async def example():
    ...     repo = AsyncGitSync(
    ...         url="https://github.com/vcs-python/libvcs",
    ...         path="/tmp/libvcs",
    ...     )
    ...     await repo.obtain()
    ...     await repo.update_repo()
    >>> # asyncio.run(example())
    """

    bin_name = "git"
    schemes = ("git+http", "git+https", "git+file")
    cmd: AsyncGit
    _remotes: GitSyncRemoteDict

    def __init__(
        self,
        *,
        url: str,
        path: StrPath,
        remotes: GitRemotesArgs = None,
        progress_callback: AsyncProgressCallbackProtocol | None = None,
        **kwargs: t.Any,
    ) -> None:
        """Initialize async git repository manager.

        Parameters
        ----------
        url : str
            URL of the repository
        path : str | Path
            Local path for the repository
        remotes : dict, optional
            Additional remotes to configure
        progress_callback : AsyncProgressCallbackProtocol, optional
            Async callback for progress updates
        """
        self.git_shallow = kwargs.pop("git_shallow", False)
        self.tls_verify = kwargs.pop("tls_verify", False)

        self._remotes: GitSyncRemoteDict

        if remotes is None:
            self._remotes = {
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

        super().__init__(
            url=url, path=path, progress_callback=progress_callback, **kwargs
        )

        self.cmd = AsyncGit(path=path, progress_callback=self.progress_callback)

        origin = (
            self._remotes.get("origin")
            if "origin" in self._remotes
            else next(iter(self._remotes.items()))[1]
        )
        if origin is None:
            raise GitRemoteOriginMissing(remotes=list(self._remotes.keys()))
        self.url = self.chomp_protocol(origin.fetch_url)

    @classmethod
    def from_pip_url(cls, pip_url: str, **kwargs: t.Any) -> AsyncGitSync:
        """Clone a git repository from a pip-style URL."""
        url, rev = convert_pip_url(pip_url)
        return cls(url=url, rev=rev, **kwargs)

    @staticmethod
    def chomp_protocol(url: str) -> str:
        """Remove VCS protocol prefix from URL.

        Parameters
        ----------
        url : str
            URL possibly with git+ prefix

        Returns
        -------
        str
            URL without git+ prefix
        """
        if url.startswith("git+"):
            return url[4:]
        return url

    async def get_revision(self) -> str:
        """Return current revision. Initial repositories return 'initial'."""
        try:
            return await self.cmd.rev_parse(
                verify=True, args="HEAD", check_returncode=True
            )
        except exc.CommandError:
            return "initial"

    async def obtain(self, *args: t.Any, **kwargs: t.Any) -> None:
        """Retrieve the repository, clone if doesn't exist."""
        self.ensure_dir()

        url = self.url

        self.log.info("Cloning.")
        await self.cmd.clone(
            url=url,
            progress=True,
            depth=1 if self.git_shallow else None,
            config={"http.sslVerify": False} if self.tls_verify else None,
            log_in_real_time=True,
        )

        self.log.info("Initializing submodules.")
        await self.cmd.submodule.init(log_in_real_time=True)
        await self.cmd.submodule.update(
            init=True,
            recursive=True,
            log_in_real_time=True,
        )

        await self.set_remotes(overwrite=True)

    async def update_repo(
        self,
        set_remotes: bool = False,
        *args: t.Any,
        **kwargs: t.Any,
    ) -> None:
        """Pull latest changes from git remote."""
        self.ensure_dir()

        if not pathlib.Path(self.path / ".git").is_dir():
            await self.obtain()
            await self.update_repo(set_remotes=set_remotes)
            return

        if set_remotes:
            await self.set_remotes(overwrite=True)

        # Get requested revision or tag
        url, git_tag = self.url, getattr(self, "rev", None)

        if not git_tag:
            self.log.debug("No git revision set, defaulting to origin/master")
            symref = await self.cmd.symbolic_ref(name="HEAD", short=True)
            git_tag = symref.rstrip() if symref else "origin/master"
        self.log.debug("git_tag: %s", git_tag)

        self.log.info("Updating to '%s'.", git_tag)

        # Get head sha
        try:
            head_sha = await self.cmd.rev_list(
                commit="HEAD",
                max_count=1,
                check_returncode=True,
            )
        except exc.CommandError:
            self.log.exception("Failed to get the hash for HEAD")
            return

        self.log.debug("head_sha: %s", head_sha)

        # Check if it's a remote ref
        show_ref_output = await self.cmd.show_ref(
            pattern=git_tag, check_returncode=False
        )
        self.log.debug("show_ref_output: %s", show_ref_output)
        is_remote_ref = "remotes" in show_ref_output
        self.log.debug("is_remote_ref: %s", is_remote_ref)

        # Get remote name
        git_remote_name = await self.get_current_remote_name()

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
        self.log.debug("git_remote_name: %s", git_remote_name)
        self.log.debug("git_tag: %s", git_tag)

        # Get tag sha
        try:
            error_code = 0
            tag_sha = await self.cmd.rev_list(
                commit=git_remote_name + "/" + git_tag if is_remote_ref else git_tag,
                max_count=1,
            )
        except exc.CommandError as e:
            error_code = e.returncode if e.returncode is not None else 0
            tag_sha = ""
        self.log.debug("tag_sha: %s", tag_sha)

        # Is the hash checkout out what we want?
        somethings_up = (error_code, is_remote_ref, tag_sha != head_sha)
        if all(not x for x in somethings_up):
            self.log.info("Already up-to-date.")
            return

        try:
            await self.cmd.fetch(log_in_real_time=True, check_returncode=True)
        except exc.CommandError:
            self.log.exception("Failed to fetch repository '%s'", url)
            return

        if is_remote_ref:
            # Check if stash is needed
            try:
                process = await self.cmd.status(porcelain=True, untracked_files="no")
            except exc.CommandError:
                self.log.exception("Failed to get the status")
                return
            need_stash = len(process) > 0

            # Stash changes if needed
            if need_stash:
                git_stash_save_options = "--quiet"
                try:
                    await self.cmd.stash.save(message=git_stash_save_options)
                except exc.CommandError:
                    self.log.exception("Failed to stash changes")

            # Checkout the remote branch
            try:
                await self.cmd.checkout(branch=git_tag)
            except exc.CommandError:
                self.log.exception("Failed to checkout tag: '%s'", git_tag)
                return

            # Rebase changes from the remote branch
            try:
                await self.cmd.rebase(upstream=git_remote_name + "/" + git_tag)
            except exc.CommandError as e:
                if any(msg in str(e) for msg in ["invalid_upstream", "Aborting"]):
                    self.log.exception("Invalid upstream remote. Rebase aborted.")
                else:
                    # Rebase failed: Restore previous state
                    await self.cmd.rebase(abort=True)
                    if need_stash:
                        await self.cmd.stash.pop(index=True, quiet=True)

                    self.log.exception(
                        f"\nFailed to rebase in: '{self.path}'.\n"
                        "You will have to resolve the conflicts manually",
                    )
                    return

            if need_stash:
                try:
                    await self.cmd.stash.pop(index=True, quiet=True)
                except exc.CommandError:
                    # Stash pop --index failed: Try again dropping the index
                    await self.cmd.reset(hard=True, quiet=True)
                    try:
                        await self.cmd.stash.pop(quiet=True)
                    except exc.CommandError:
                        # Stash pop failed: Restore previous state
                        await self.cmd.reset(pathspec=head_sha, hard=True, quiet=True)
                        await self.cmd.stash.pop(index=True, quiet=True)
                        self.log.exception(
                            f"\nFailed to rebase in: '{self.path}'.\n"
                            "You will have to resolve the conflicts manually",
                        )
                        return

        else:
            try:
                await self.cmd.checkout(branch=git_tag)
            except exc.CommandError:
                self.log.exception("Failed to checkout tag: '%s'", git_tag)
                return

        await self.cmd.submodule.update(
            recursive=True, init=True, log_in_real_time=True
        )

    async def set_remotes(self, overwrite: bool = False) -> None:
        """Apply remotes in local repository to match configuration."""
        remotes = self._remotes
        if isinstance(remotes, dict):
            for remote_name, git_remote_repo in remotes.items():
                existing_remote = await self.remote(remote_name)
                if isinstance(git_remote_repo, GitRemote):
                    if (
                        not existing_remote
                        or existing_remote.fetch_url != git_remote_repo.fetch_url
                    ):
                        await self.set_remote(
                            name=remote_name,
                            url=git_remote_repo.fetch_url,
                            overwrite=overwrite,
                        )
                        existing_remote = await self.remote(remote_name)
                    if git_remote_repo.push_url and (
                        not existing_remote
                        or existing_remote.push_url != git_remote_repo.push_url
                    ):
                        await self.set_remote(
                            name=remote_name,
                            url=git_remote_repo.push_url,
                            push=True,
                            overwrite=overwrite,
                        )
                elif (
                    not existing_remote
                    or existing_remote.fetch_url != git_remote_repo.fetch_url
                ):
                    await self.set_remote(
                        name=remote_name,
                        url=git_remote_repo.fetch_url,
                        overwrite=overwrite,
                    )

    async def remotes_get(self) -> GitSyncRemoteDict:
        """Return remotes like git remote -v.

        Returns
        -------
        dict
            Dictionary of remote names to GitRemote objects
        """
        remotes: GitSyncRemoteDict = {}

        ret = await self.cmd.remotes.ls()
        for remote_name in ret:
            remote_name = remote_name.strip()
            if not remote_name:
                continue
            try:
                remote_output = await self.cmd.remotes.show(
                    name=remote_name,
                    verbose=True,
                )
            except exc.CommandError:
                self.log.exception("Failed to get remote info for %s", remote_name)
                continue

            # Parse remote output
            fetch_url = ""
            push_url = ""
            for line in remote_output.splitlines():
                line = line.strip()
                if "(fetch)" in line:
                    fetch_url = line.replace("(fetch)", "").strip()
                elif "(push)" in line:
                    push_url = line.replace("(push)", "").strip()

            remotes[remote_name] = GitRemote(
                name=remote_name,
                fetch_url=fetch_url,
                push_url=push_url,
            )

        return remotes

    async def remote(self, name: str) -> GitRemote | None:
        """Get a specific remote by name.

        Parameters
        ----------
        name : str
            Remote name

        Returns
        -------
        GitRemote | None
            Remote info or None if not found
        """
        remotes = await self.remotes_get()
        return remotes.get(name)

    async def set_remote(
        self,
        *,
        name: str,
        url: str,
        push: bool = False,
        overwrite: bool = False,
    ) -> None:
        """Set or add a remote.

        Parameters
        ----------
        name : str
            Remote name
        url : str
            Remote URL
        push : bool
            Set push URL instead of fetch URL
        overwrite : bool
            Overwrite existing remote
        """
        existing_remotes = await self.cmd.remotes.ls()

        if name in existing_remotes:
            if push:
                # Set push URL using git remote set-url --push
                await self.cmd.run(["remote", "set-url", "--push", name, url])
            elif overwrite:
                await self.cmd.run(["remote", "set-url", name, url])
        else:
            await self.cmd.remotes.add(name=name, url=url)

        # Verify
        remote = await self.remote(name)
        if not remote:
            raise GitRemoteSetError(remote_name=name)

    async def get_current_remote_name(self) -> str:
        """Get the current remote name.

        Returns
        -------
        str
            Remote name (defaults to 'origin')
        """
        try:
            # Try to get the upstream remote
            branch = await self.cmd.symbolic_ref(name="HEAD", short=True)
            branch = branch.strip()
            if branch:
                # Get the remote for this branch
                try:
                    remote = await self.cmd.run(
                        ["config", f"branch.{branch}.remote"],
                        check_returncode=False,
                    )
                    if remote.strip():
                        return remote.strip()
                except exc.CommandError:
                    pass
        except exc.CommandError:
            pass
        return "origin"

    async def get_git_version(self) -> str:
        """Return git version.

        Returns
        -------
        str
            Git version string
        """
        return await self.cmd.version()

    async def status(self) -> GitStatus:
        """Return GitStatus with parsed git status information.

        Returns
        -------
        GitStatus
            Parsed git status information
        """
        output = await self.cmd.status(short=True, branch=True, porcelain="2")
        return GitStatus.from_stdout(output)
