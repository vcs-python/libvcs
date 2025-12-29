"""Async tool to manage a local SVN (Subversion) working copy from a repository.

Async equivalent of :mod:`libvcs.sync.svn`.

Note
----
This is an internal API not covered by versioning policy.
"""

from __future__ import annotations

import logging
import os
import pathlib
import re
import typing as t

from libvcs._internal.async_run import AsyncProgressCallbackProtocol
from libvcs._internal.types import StrPath
from libvcs.cmd._async.svn import AsyncSvn
from libvcs.sync._async.base import AsyncBaseSync
from libvcs.sync.svn import SvnUrlRevFormattingError

logger = logging.getLogger(__name__)


class AsyncSvnSync(AsyncBaseSync):
    """Async tool to manage a local SVN working copy from a SVN repository.

    Async equivalent of :class:`~libvcs.sync.svn.SvnSync`.

    Examples
    --------
    >>> import asyncio
    >>> async def example():
    ...     repo = AsyncSvnSync(
    ...         url="svn://svn.example.com/repo",
    ...         path="/tmp/myrepo",
    ...     )
    ...     await repo.obtain()
    ...     await repo.update_repo()
    >>> # asyncio.run(example())
    """

    bin_name = "svn"
    schemes = ("svn", "svn+ssh", "svn+http", "svn+https", "svn+svn")
    cmd: AsyncSvn

    def __init__(
        self,
        *,
        url: str,
        path: StrPath,
        progress_callback: AsyncProgressCallbackProtocol | None = None,
        **kwargs: t.Any,
    ) -> None:
        """Initialize async SVN working copy manager.

        Parameters
        ----------
        url : str
            URL of the SVN repository
        path : str | Path
            Local path for the working copy
        progress_callback : AsyncProgressCallbackProtocol, optional
            Async callback for progress updates
        username : str, optional
            Username for SVN authentication
        password : str, optional
            Password for SVN authentication
        svn_trust_cert : bool, optional
            Trust the SVN server certificate, default False
        """
        self.svn_trust_cert = kwargs.pop("svn_trust_cert", False)
        self.username = kwargs.get("username")
        self.password = kwargs.get("password")
        self.rev = kwargs.get("rev")

        super().__init__(
            url=url, path=path, progress_callback=progress_callback, **kwargs
        )

        self.cmd = AsyncSvn(path=path, progress_callback=self.progress_callback)

    async def obtain(
        self, quiet: bool | None = None, *args: t.Any, **kwargs: t.Any
    ) -> None:
        """Check out a working copy from a SVN repository asynchronously.

        Async equivalent of :meth:`~libvcs.sync.svn.SvnSync.obtain`.

        Parameters
        ----------
        quiet : bool, optional
            Suppress output
        """
        url, rev = self.url, self.rev

        if rev is not None:
            kwargs["revision"] = rev
        if self.svn_trust_cert:
            kwargs["trust_server_cert"] = True

        await self.cmd.checkout(
            url=url,
            username=self.username,
            password=self.password,
            non_interactive=True,
            quiet=True,
            check_returncode=True,
            **kwargs,
        )

    async def get_revision_file(self, location: str) -> int:
        """Return revision for a file asynchronously.

        Async equivalent of :meth:`~libvcs.sync.svn.SvnSync.get_revision_file`.

        Parameters
        ----------
        location : str
            Path to the file

        Returns
        -------
        int
            Revision number
        """
        current_rev = await self.cmd.info(target=location)

        INI_RE = re.compile(r"^([^:]+):\s+(\S.*)$", re.MULTILINE)

        info_list = INI_RE.findall(current_rev)
        return int(dict(info_list)["Revision"])

    async def get_revision(self, location: str | None = None) -> int:
        """Return maximum revision for all files under a given location asynchronously.

        Async equivalent of :meth:`~libvcs.sync.svn.SvnSync.get_revision`.

        Parameters
        ----------
        location : str, optional
            Path to check, defaults to self.url

        Returns
        -------
        int
            Maximum revision number
        """
        if not location:
            location = self.url

        if pathlib.Path(location).exists() and not pathlib.Path(location).is_dir():
            return await self.get_revision_file(location)

        # Note: taken from setuptools.command.egg_info
        revision = 0

        for base, dirs, _files in os.walk(location):
            if ".svn" not in dirs:
                dirs[:] = []
                continue  # no sense walking uncontrolled subdirs
            dirs.remove(".svn")
            entries_fn = pathlib.Path(base) / ".svn" / "entries"
            if not entries_fn.exists():
                # FIXME: should we warn?
                continue

            dirurl, localrev = await self._get_svn_url_rev(base)

            if base == location:
                assert dirurl is not None
                base = dirurl + "/"  # save the root url
            elif not dirurl or not dirurl.startswith(base):
                dirs[:] = []
                continue  # not part of the same svn tree, skip it
            revision = max(revision, localrev)
        return revision

    async def update_repo(
        self,
        dest: str | None = None,
        *args: t.Any,
        **kwargs: t.Any,
    ) -> None:
        """Fetch changes from SVN repository to local working copy asynchronously.

        Async equivalent of :meth:`~libvcs.sync.svn.SvnSync.update_repo`.

        Parameters
        ----------
        dest : str, optional
            Destination path (unused, for API compatibility)
        """
        self.ensure_dir()
        if pathlib.Path(self.path / ".svn").exists():
            await self.cmd.checkout(
                url=self.url,
                username=self.username,
                password=self.password,
                non_interactive=True,
                quiet=True,
                check_returncode=True,
                **kwargs,
            )
        else:
            await self.obtain()
            await self.update_repo()

    async def _get_svn_url_rev(self, location: str) -> tuple[str | None, int]:
        """Get SVN URL and revision from a working copy location asynchronously.

        Async equivalent of :meth:`~libvcs.sync.svn.SvnSync._get_svn_url_rev`.

        Parameters
        ----------
        location : str
            Path to the working copy

        Returns
        -------
        tuple[str | None, int]
            Repository URL and revision number
        """
        svn_xml_url_re = re.compile(r'url="([^"]+)"')
        svn_rev_re = re.compile(r'committed-rev="(\d+)"')
        svn_info_xml_rev_re = re.compile(r'\s*revision="(\d+)"')
        svn_info_xml_url_re = re.compile(r"<url>(.*)</url>")

        entries_path = pathlib.Path(location) / ".svn" / "entries"
        if entries_path.exists():
            with entries_path.open() as f:
                data = f.read()
        else:  # subversion >= 1.7 does not have the 'entries' file
            data = ""

        url = None
        if data.startswith(("8", "9", "10")):
            entries = list(map(str.splitlines, data.split("\n\x0c\n")))
            del entries[0][0]  # get rid of the '8'
            url = entries[0][3]
            revs = [int(d[9]) for d in entries if len(d) > 9 and d[9]] + [0]
        elif data.startswith("<?xml"):
            match = svn_xml_url_re.search(data)
            if not match:
                raise SvnUrlRevFormattingError(data=data)
            url = match.group(1)  # get repository URL
            revs = [int(m.group(1)) for m in svn_rev_re.finditer(data)] + [0]
        else:
            try:
                # Note that using get_remote_call_options is not necessary here
                # because `svn info` is being run against a local directory.
                # We don't need to worry about making sure interactive mode
                # is being used to prompt for passwords, because passwords
                # are only potentially needed for remote server requests.
                xml = await AsyncSvn(path=pathlib.Path(location).parent).info(
                    target=pathlib.Path(location),
                    xml=True,
                )
                match = svn_info_xml_url_re.search(xml)
                assert match is not None
                url = match.group(1)
                revs = [int(m.group(1)) for m in svn_info_xml_rev_re.finditer(xml)]
            except Exception:
                url, revs = None, []

        rev = max(revs) if revs else 0

        return url, rev
