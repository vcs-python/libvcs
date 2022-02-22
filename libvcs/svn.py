#!/usr/bin/env python
"""Subversion object for libvcs.

The follow are from saltstack/salt (Apache license):

- [`SubversionRepo.get_revision_file`](libvcs.svn.SubversionRepo.get_revision_file)

The following are pypa/pip (MIT license):

- [`SubversionRepo.convert_pip_url`](libvcs.svn.SubversionRepo.convert_pip_url)
- [`SubversionRepo.get_url`](libvcs.svn.SubversionRepo.get_url)
- [`SubversionRepo.get_revision`](libvcs.svn.SubversionRepo.get_revision)
- [`get_rev_options`](libvcs.svn.get_rev_options)
"""  # NOQA: E5
import logging
import os
import re
from urllib import parse as urlparse

from .base import BaseRepo, VCSLocation, convert_pip_url as base_convert_pip_url

logger = logging.getLogger(__name__)


def convert_pip_url(pip_url: str) -> VCSLocation:
    # hotfix the URL scheme after removing svn+ from svn+ssh:// re-add it
    url, rev = base_convert_pip_url(pip_url)
    if url.startswith("ssh://"):
        url = "svn+" + url
    return VCSLocation(url=url, rev=rev)


class SubversionRepo(BaseRepo):
    bin_name = "svn"
    schemes = ("svn", "svn+ssh", "svn+http", "svn+https", "svn+svn")

    def __init__(self, url, repo_dir, **kwargs):
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
        BaseRepo.__init__(self, url, repo_dir, **kwargs)

    def _user_pw_args(self):
        args = []
        for param_name in ["svn_username", "svn_password"]:
            if hasattr(self, param_name):
                args.extend(["--" + param_name[4:], getattr(self, param_name)])
        return args

    def obtain(self, quiet=None):
        self.ensure_dir()

        url, rev = self.url, self.rev

        cmd = ["checkout", "-q", url, "--non-interactive"]
        if self.svn_trust_cert:
            cmd.append("--trust-server-cert")
        cmd.extend(self._user_pw_args())
        cmd.extend(get_rev_options(url, rev))
        cmd.append(self.path)

        self.run(cmd)

    def get_revision_file(self, location):
        """Return revision for a file."""

        current_rev = self.run(["info", location])

        _INI_RE = re.compile(r"^([^:]+):\s+(\S.*)$", re.M)

        info_list = _INI_RE.findall(current_rev)
        return int(dict(info_list)["Revision"])

    def get_revision(self, location=None):
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

            dirurl, localrev = self._get_svn_url_rev(base)

            if base == location:
                base_url = dirurl + "/"  # save the root url
            elif not dirurl or not dirurl.startswith(base_url):
                dirs[:] = []
                continue  # not part of the same svn tree, skip it
            revision = max(revision, localrev)
        return revision

    def update_repo(self, dest=None):
        self.ensure_dir()
        if os.path.isdir(os.path.join(self.path, ".svn")):
            dest = self.path if not dest else dest

            url, rev = self.url, self.rev

            cmd = ["update"]
            cmd.extend(self._user_pw_args())
            cmd.extend(get_rev_options(url, rev))

            self.run(cmd)
        else:
            self.obtain()
            self.update_repo()


def get_rev_options(url, rev):
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
