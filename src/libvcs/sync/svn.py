#!/usr/bin/env python
"""Subversion object for libvcs.

.. todo::

    The follow are from saltstack/salt (Apache license):

    - [`SvnSync.get_revision_file`](libvcs.svn.SvnSync.get_revision_file)

    The following are pypa/pip (MIT license):

    - [`SvnSync.convert_pip_url`](libvcs.svn.SvnSync.convert_pip_url)
    - [`SvnSync.get_url`](libvcs.svn.SvnSync.get_url)
    - [`SvnSync.get_revision`](libvcs.svn.SvnSync.get_revision)
    - [`get_rev_options`](libvcs.svn.get_rev_options)
"""  # NOQA: E5
import logging
import os
import pathlib
import re
from typing import Any, Optional
from urllib import parse as urlparse

from libvcs._internal.run import run
from libvcs._internal.types import StrOrBytesPath, StrPath

from .base import BaseSync, VCSLocation, convert_pip_url as base_convert_pip_url

logger = logging.getLogger(__name__)


def convert_pip_url(pip_url: str) -> VCSLocation:
    # hotfix the URL scheme after removing svn+ from svn+ssh:// re-add it
    url, rev = base_convert_pip_url(pip_url)
    if url.startswith("ssh://"):
        url = "svn+" + url
    return VCSLocation(url=url, rev=rev)


class SvnSync(BaseSync):
    bin_name = "svn"
    schemes = ("svn", "svn+ssh", "svn+http", "svn+https", "svn+svn")

    def __init__(self, *, url: str, dir: StrPath, **kwargs: Any) -> None:
        """A svn repository.

        Parameters
        ----------
        url : str
            URL in subversion repository

        svn_username : str, optional
            username to use for checkout and update

        svn_password : str, optional
            password to use for checkout and update

        svn_trust_cert : bool
            trust the Subversion server site certificate, default False
        """
        if "svn_trust_cert" not in kwargs:
            self.svn_trust_cert = False

        self.rev = kwargs.get("rev")
        super().__init__(url=url, dir=dir, **kwargs)

    def _user_pw_args(self) -> list[Any]:
        args = []
        for param_name in ["svn_username", "svn_password"]:
            if hasattr(self, param_name):
                args.extend(["--" + param_name[4:], getattr(self, param_name)])
        return args

    def obtain(self, quiet: Optional[bool] = None, *args: Any, **kwargs: Any) -> None:
        self.ensure_dir()

        url, rev = self.url, self.rev

        cmd: list[StrOrBytesPath] = ["checkout", "-q", url, "--non-interactive"]
        if self.svn_trust_cert:
            cmd.append("--trust-server-cert")
        cmd.extend(self._user_pw_args())
        cmd.extend(get_rev_options(url, rev))
        cmd.append(self.dir)

        self.run(cmd)

    def get_revision_file(self, location: str) -> int:
        """Return revision for a file."""

        current_rev = self.run(["info", location])

        _INI_RE = re.compile(r"^([^:]+):\s+(\S.*)$", re.M)

        info_list = _INI_RE.findall(current_rev)
        return int(dict(info_list)["Revision"])

    def get_revision(self, location: Optional[str] = None) -> int:
        """Return maximum revision for all files under a given location"""

        if not location:
            location = self.url

        if os.path.exists(location) and not os.path.isdir(location):
            return self.get_revision_file(location)

        # Note: taken from setuptools.command.egg_info
        revision = 0

        for base, dirs, files in os.walk(location):
            if ".svn" not in dirs:
                dirs[:] = []
                continue  # no sense walking uncontrolled subdirs
            dirs.remove(".svn")
            entries_fn = os.path.join(base, ".svn", "entries")
            if not os.path.exists(entries_fn):
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
        self, dest: Optional[str] = None, *args: Any, **kwargs: Any
    ) -> None:
        self.ensure_dir()
        if pathlib.Path(self.dir / ".svn").exists():
            if dest is None:
                dest = str(self.dir)

            url, rev = self.url, self.rev

            cmd = ["update"]
            cmd.extend(self._user_pw_args())
            cmd.extend(get_rev_options(url, rev))
            cmd.append(dest)

            self.run(cmd)
        else:
            self.obtain()
            self.update_repo()

    @classmethod
    def _get_svn_url_rev(cls, location: str) -> tuple[Optional[str], int]:
        _svn_xml_url_re = re.compile('url="([^"]+)"')
        _svn_rev_re = re.compile(r'committed-rev="(\d+)"')
        _svn_info_xml_rev_re = re.compile(r'\s*revision="(\d+)"')
        _svn_info_xml_url_re = re.compile(r"<url>(.*)</url>")

        entries_path = os.path.join(location, ".svn", "entries")
        if os.path.exists(entries_path):
            with open(entries_path) as f:
                data = f.read()
        else:  # subversion >= 1.7 does not have the 'entries' file
            data = ""

        url = None
        if data.startswith("8") or data.startswith("9") or data.startswith("10"):
            entries = list(map(str.splitlines, data.split("\n\x0c\n")))
            del entries[0][0]  # get rid of the '8'
            url = entries[0][3]
            revs = [int(d[9]) for d in entries if len(d) > 9 and d[9]] + [0]
        elif data.startswith("<?xml"):
            match = _svn_xml_url_re.search(data)
            if not match:
                raise ValueError(f"Badly formatted data: {data!r}")
            url = match.group(1)  # get repository URL
            revs = [int(m.group(1)) for m in _svn_rev_re.finditer(data)] + [0]
        else:
            try:
                # subversion >= 1.7
                # Note that using get_remote_call_options is not necessary here
                # because `svn info` is being run against a local directory.
                # We don't need to worry about making sure interactive mode
                # is being used to prompt for passwords, because passwords
                # are only potentially needed for remote server requests.
                xml = run(
                    ["svn", "info", "--xml", location],
                )
                match = _svn_info_xml_url_re.search(xml)
                assert match is not None
                url = match.group(1)
                revs = [int(m.group(1)) for m in _svn_info_xml_rev_re.finditer(xml)]
            except Exception:
                url, revs = None, []

        if revs:
            rev = max(revs)
        else:
            rev = 0

        return url, rev


def get_rev_options(url: str, rev: None) -> list[Any]:
    """Return revision options. From pip pip.vcs.subversion."""
    if rev:
        rev_options = ["-r", rev]
    else:
        rev_options = []

    r = urlparse.urlsplit(url)
    if hasattr(r, "username"):
        # >= Python-2.5
        username, password = r.username, r.password
    else:
        netloc = r[1]
        if "@" in netloc:
            auth = netloc.split("@")[0]
            if ":" in auth:
                username, password = auth.split(":", 1)
            else:
                username, password = auth, None
        else:
            username, password = None, None

    if username:
        rev_options += ["--username", username]
    if password:
        rev_options += ["--password", password]
    return rev_options
