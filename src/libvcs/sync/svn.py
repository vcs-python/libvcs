#!/usr/bin/env python
"""Tool to manage a local SVN (Subversion) working copy from a repository.

.. todo::

    The follow are from saltstack/salt (Apache license):

    - [`SvnSync.get_revision_file`](libvcs.svn.SvnSync.get_revision_file)

    The following are pypa/pip (MIT license):

    - [`SvnSync.get_url`](libvcs.svn.SvnSync.get_url)
    - [`SvnSync.get_revision`](libvcs.svn.SvnSync.get_revision)
"""

from __future__ import annotations

import logging
import os
import pathlib
import re
import typing as t

from libvcs.cmd.svn import Svn

from .base import BaseSync

if t.TYPE_CHECKING:
    from libvcs._internal.types import StrPath

logger = logging.getLogger(__name__)


class SvnUrlRevFormattingError(ValueError):
    """Raised when SVN Revision output is not in the expected format."""

    def __init__(self, data: str, *args: object) -> None:
        return super().__init__(f"Badly formatted data: {data!r}")


class SvnSync(BaseSync):
    """Tool to manage a local SVN (Subversion) working copy from a SVN repository."""

    bin_name = "svn"
    schemes = ("svn", "svn+ssh", "svn+http", "svn+https", "svn+svn")
    cmd: Svn

    def __init__(
        self,
        *,
        url: str,
        path: StrPath,
        **kwargs: t.Any,
    ) -> None:
        """Working copy of a SVN repository.

        Parameters
        ----------
        url : str
            URL in subversion repository

        username : str, optional
            username to use for checkout and update

        password : str, optional
            password to use for checkout and update

        svn_trust_cert : bool
            trust the Subversion server site certificate, default False
        """
        self.svn_trust_cert = kwargs.pop("svn_trust_cert", False)

        self.username = kwargs.get("username")
        self.password = kwargs.get("password")

        self.rev = kwargs.get("rev")

        super().__init__(url=url, path=path, **kwargs)

        self.cmd = Svn(path=path, progress_callback=self.progress_callback)

    def _user_pw_args(self) -> list[t.Any]:
        args = []
        for param_name in ["svn_username", "svn_password"]:
            if hasattr(self, param_name):
                args.extend(["--" + param_name[4:], getattr(self, param_name)])
        return args

    def obtain(self, quiet: bool | None = None, *args: t.Any, **kwargs: t.Any) -> None:
        """Check out a working copy from a SVN repository."""
        url, rev = self.url, self.rev

        if rev is not None:
            kwargs["revision"] = rev
        if self.svn_trust_cert:
            kwargs["trust_server_cert"] = True
        self.cmd.checkout(
            url=url,
            username=self.username,
            password=self.password,
            non_interactive=True,
            quiet=True,
            check_returncode=True,
            **kwargs,
        )

    def get_revision_file(self, location: str) -> int:
        """Return revision for a file."""
        current_rev = self.cmd.info(location)

        INI_RE = re.compile(r"^([^:]+):\s+(\S.*)$", re.MULTILINE)

        info_list = INI_RE.findall(current_rev)
        return int(dict(info_list)["Revision"])

    def get_revision(self, location: str | None = None) -> int:
        """Return maximum revision for all files under a given location."""
        if not location:
            location = self.url

        if pathlib.Path(location).exists() and not pathlib.Path(location).is_dir():
            return self.get_revision_file(location)

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

            dirurl, localrev = SvnSync._get_svn_url_rev(base)

            if base == location:
                assert dirurl is not None
                base = dirurl + "/"  # save the root url
            elif not dirurl or not dirurl.startswith(base):
                dirs[:] = []
                continue  # not part of the same svn tree, skip it
            revision = max(revision, localrev)
        return revision

    def update_repo(
        self,
        dest: str | None = None,
        *args: t.Any,
        **kwargs: t.Any,
    ) -> None:
        """Fetch changes from SVN repository to local working copy."""
        self.ensure_dir()
        if pathlib.Path(self.path / ".svn").exists():
            self.cmd.checkout(
                url=self.url,
                username=self.username,
                password=self.password,
                non_interactive=True,
                quiet=True,
                check_returncode=True,
                **kwargs,
            )
        else:
            self.obtain()
            self.update_repo()

    @classmethod
    def _get_svn_url_rev(cls, location: str) -> tuple[str | None, int]:
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
                xml = Svn(path=pathlib.Path(location).parent).info(
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
