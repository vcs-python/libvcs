"""Git Repo object for libvcs.

.. todo::

    From https://github.com/saltstack/salt (Apache License):

    - [`GitRepo.remote`](libvcs.git.GitRepo.remote) (renamed to ``remote``)
    - [`GitRepo.remote`](libvcs.git.GitRepo.remote_set) (renamed to ``set_remote``)

    From pip (MIT Licnese):

    - [`GitRepo.remote`](libvcs.git.GitRepo.remote_set) (renamed to ``set_remote``)
    - [`GitRepo.convert_pip_url`](libvcs.git.GitRepo.convert_pip_url`) (``get_url_rev``)
    - [`GitRepo.get_revision`](libvcs.git.GitRepo.get_revision)
    - [`GitRepo.get_git_version`](libvcs.git.GitRepo.get_git_version)
"""  # NOQA: E501
import logging
import os
import re
from typing import Dict, NamedTuple, Optional, TypedDict, Union
from urllib import parse as urlparse

from . import exc
from .base import BaseRepo, VCSLocation, convert_pip_url as base_convert_pip_url

logger = logging.getLogger(__name__)


class GitRemote(NamedTuple):
    """Structure containing git repo information.

    Supports `collections.namedtuple._asdict()`
    """

    name: str
    fetch_url: str
    push_url: str


class GitStatus(NamedTuple):
    branch_oid: Optional[str]
    branch_head: Optional[str]
    branch_upstream: Optional[str]
    branch_ab: Optional[str]
    branch_ahead: Optional[str]
    branch_behind: Optional[str]


def extract_status(value) -> GitStatus:
    """Returns ``git status -sb --porcelain=2`` extracted to a dict

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
    return GitStatus(**matches.groupdict())


def convert_pip_url(pip_url: str) -> VCSLocation:
    """
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
        raise exc.LibVCSException(
            "Repo %s is malformatted, please use the convention %s for"
            "ssh / private GitHub repositories."
            % (pip_url, "git+https://github.com/username/repo.git")
        )
    else:
        url, rev = base_convert_pip_url(pip_url)

    return VCSLocation(url=url, rev=rev)


class RemoteDict(TypedDict):
    fetch_url: str
    push_url: str


GitRepoRemoteDict = Dict[str, GitRemote]
FullRemoteDict = Dict[str, RemoteDict]
RemotesArgs = Union[None, FullRemoteDict, Dict[str, str]]


class GitRepo(BaseRepo):
    bin_name = "git"
    schemes = ("git", "git+http", "git+https", "git+ssh", "git+git", "git+file")

    def __init__(
        self, url: str, repo_dir: str, remotes: RemotesArgs = None, *args, **kwargs
    ):
        """A git repository.

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
            from libvcs.git import GitRepo

            checkout = os.path.dirname(os.path.abspath(__name__)) + '/' + 'my_libvcs'

            repo = GitRepo(
               url="https://github.com/vcs-python/libvcs",
               repo_dir=checkout,
               remotes={
                   'gitlab': 'https://gitlab.com/vcs-python/libvcs'
               }
            )

        .. code-block:: python

            import os
            from libvcs.git import GitRepo

            checkout = os.path.dirname(os.path.abspath(__name__)) + '/' + 'my_libvcs'

            repo = GitRepo(
               url="https://github.com/vcs-python/libvcs",
               repo_dir=checkout,
               remotes={
                   'gitlab': {
                       'fetch': 'https://gitlab.com/vcs-python/libvcs',
                       'push': 'https://gitlab.com/vcs-python/libvcs',
                   },
               }
            )
        """
        if "git_shallow" not in kwargs:
            self.git_shallow = False
        if "tls_verify" not in kwargs:
            self.tls_verify = False

        self._remotes: GitRepoRemoteDict

        if remotes is None:
            self._remotes: GitRepoRemoteDict = {
                "origin": GitRemote(name="origin", fetch_url=url, push_url=url)
            }
        elif isinstance(remotes, dict):
            self._remotes = {}
            for remote_name, url in remotes.items():
                if isinstance(url, str):
                    self._remotes[remote_name] = GitRemote(
                        name=remote_name,
                        fetch_url=url,
                        push_url=url,
                    )
                elif isinstance(url, GitRemote):
                    self._remotes[remote_name] = url

        BaseRepo.__init__(self, url, repo_dir, *args, **kwargs)
        self.url = (
            self._remotes.get("origin").fetch_url
            if "origin" in self._remotes
            else next(iter(self._remotes.items()))[1].fetch_url
        )

    @classmethod
    def from_pip_url(cls, pip_url, *args, **kwargs):
        url, rev = convert_pip_url(pip_url)
        self = cls(url=url, rev=rev, *args, **kwargs)

        return self

    def get_revision(self):
        """Return current revision. Initial repositories return 'initial'."""
        try:
            return self.run(["rev-parse", "--verify", "HEAD"])
        except exc.CommandError:
            return "initial"

    def set_remotes(self, overwrite: bool = False):
        remotes = self._remotes
        if isinstance(remotes, dict):
            for remote_name, git_remote in remotes.items():

                existing_remote = self.remote(remote_name)
                if isinstance(git_remote, GitRemote):
                    if (
                        not existing_remote
                        or existing_remote.fetch_url != git_remote.fetch_url
                    ):
                        self.set_remote(
                            name=remote_name,
                            url=git_remote.fetch_url,
                            overwrite=overwrite,
                        )
                        # refresh if we're setting it, so push can be checked
                        existing_remote = self.remote(remote_name)
                    if git_remote.push_url:
                        if (
                            not existing_remote
                            or existing_remote.push_url != git_remote.push_url
                        ):
                            self.set_remote(
                                name=remote_name,
                                url=git_remote.push_url,
                                push=True,
                                overwrite=overwrite,
                            )
                else:
                    if (
                        not existing_remote
                        or existing_remote.fetch_url != git_remote.fetch_url
                    ):
                        self.set_remote(
                            name=remote_name,
                            url=git_remote.fetch_url,
                            overwrite=overwrite,
                        )

    def obtain(self, *args, **kwargs):
        """Retrieve the repository, clone if doesn't exist."""
        self.ensure_dir()

        url = self.url

        cmd = ["clone", "--progress"]
        if self.git_shallow:
            cmd.extend(["--depth", "1"])
        if self.tls_verify:
            cmd.extend(["-c", "http.sslVerify=false"])
        cmd.extend([url, self.path])

        self.info("Cloning.")
        self.run(cmd, log_in_real_time=True)

        self.info("Initializing submodules.")
        self.run(["submodule", "init"], log_in_real_time=True)
        cmd = ["submodule", "update", "--recursive", "--init"]
        self.run(cmd, log_in_real_time=True)

        self.set_remotes()

    def update_repo(self, set_remotes: bool = False, *args, **kwargs):
        self.ensure_dir()

        if not os.path.isdir(os.path.join(self.path, ".git")):
            self.obtain()
            self.update_repo(set_remotes=set_remotes)
            return

        if set_remotes:
            self.set_remotes(overwrite=True)

        # Get requested revision or tag
        url, git_tag = self.url, getattr(self, "rev", None)

        if not git_tag:
            self.debug("No git revision set, defaulting to origin/master")
            symref = self.run(["symbolic-ref", "--short", "HEAD"])
            if symref:
                git_tag = symref.rstrip()
            else:
                git_tag = "origin/master"
        self.debug("git_tag: %s" % git_tag)

        self.info("Updating to '%s'." % git_tag)

        # Get head sha
        try:
            head_sha = self.run(["rev-list", "--max-count=1", "HEAD"])
        except exc.CommandError:
            self.error("Failed to get the hash for HEAD")
            return

        self.debug("head_sha: %s" % head_sha)

        # If a remote ref is asked for, which can possibly move around,
        # we must always do a fetch and checkout.
        show_ref_output = self.run(["show-ref", git_tag], check_returncode=False)
        self.debug("show_ref_output: %s" % show_ref_output)
        is_remote_ref = "remotes" in show_ref_output
        self.debug("is_remote_ref: %s" % is_remote_ref)

        # show-ref output is in the form "<sha> refs/remotes/<remote>/<tag>"
        # we must strip the remote from the tag.
        git_remote_name = self.get_current_remote_name()

        if "refs/remotes/%s" % git_tag in show_ref_output:
            m = re.match(
                r"^[0-9a-f]{40} refs/remotes/"
                r"(?P<git_remote_name>[^/]+)/"
                r"(?P<git_tag>.+)$",
                show_ref_output,
                re.MULTILINE,
            )
            git_remote_name = m.group("git_remote_name")
            git_tag = m.group("git_tag")
        self.debug("git_remote_name: %s" % git_remote_name)
        self.debug("git_tag: %s" % git_tag)

        # This will fail if the tag does not exist (it probably has not
        # been fetched yet).
        try:
            error_code = 0
            tag_sha = self.run(
                [
                    "rev-list",
                    "--max-count=1",
                    git_remote_name + "/" + git_tag if is_remote_ref else git_tag,
                ]
            )
        except exc.CommandError as e:
            error_code = e.returncode
            tag_sha = ""
        self.debug("tag_sha: %s" % tag_sha)

        # Is the hash checkout out what we want?
        somethings_up = (error_code, is_remote_ref, tag_sha != head_sha)
        if all(not x for x in somethings_up):
            self.info("Already up-to-date.")
            return

        try:
            process = self.run(["fetch_url"], log_in_real_time=True)
        except exc.CommandError:
            self.error("Failed to fetch repository '%s'" % url)
            return

        if is_remote_ref:
            # Check if stash is needed
            try:
                process = self.run(["status", "--porcelain"])
            except exc.CommandError:
                self.error("Failed to get the status")
                return
            need_stash = len(process) > 0

            # If not in clean state, stash changes in order to be able
            # to be able to perform git pull --rebase
            if need_stash:
                # If Git < 1.7.6, uses --quiet --all
                git_stash_save_options = "--quiet"
                try:
                    process = self.run(["stash", "save", git_stash_save_options])
                except exc.CommandError:
                    self.error("Failed to stash changes")

            # Checkout the remote branch
            try:
                process = self.run(["checkout", git_tag])
            except exc.CommandError:
                self.error("Failed to checkout tag: '%s'" % git_tag)
                return

            # Rebase changes from the remote branch
            try:
                process = self.run(["rebase", git_remote_name + "/" + git_tag])
            except exc.CommandError as e:
                if "invalid_upstream" in str(e):
                    self.error(e)
                else:
                    # Rebase failed: Restore previous state.
                    self.run(["rebase", "--abort"])
                    if need_stash:
                        self.run(["stash", "pop", "--index", "--quiet"])

                    self.error(
                        "\nFailed to rebase in: '%s'.\n"
                        "You will have to resolve the conflicts manually" % self.path
                    )
                    return

            if need_stash:
                try:
                    process = self.run(["stash", "pop", "--index", "--quiet"])
                except exc.CommandError:
                    # Stash pop --index failed: Try again dropping the index
                    self.run(["reset", "--hard", "--quiet"])
                    try:
                        process = self.run(["stash", "pop", "--quiet"])
                    except exc.CommandError:
                        # Stash pop failed: Restore previous state.
                        self.run(["reset", "--hard", "--quiet", head_sha])
                        self.run(["stash", "pop", "--index", "--quiet"])
                        self.error(
                            "\nFailed to rebase in: '%s'.\n"
                            "You will have to resolve the "
                            "conflicts manually" % self.path
                        )
                        return

        else:
            try:
                process = self.run(["checkout", git_tag])
            except exc.CommandError:
                self.error("Failed to checkout tag: '%s'" % git_tag)
                return

        cmd = ["submodule", "update", "--recursive", "--init"]
        self.run(cmd, log_in_real_time=True)

    def remotes(self, flat=False) -> Dict:
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

        cmd = self.run(["remote"])
        ret = filter(None, cmd.split("\n"))

        for remote_name in ret:
            remotes[remote_name] = (
                self.remote(remote_name) if flat else self.remote(remote_name)._asdict()
            )
        return remotes

    def remote(self, name, **kwargs) -> GitRemote:
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
            ret = self.run(["remote", "show", "-n", name])
            lines = ret.split("\n")
            remote_fetch_url = lines[1].replace("Fetch URL: ", "").strip()
            remote_push_url = lines[2].replace("Push  URL: ", "").strip()
            if remote_fetch_url != name and remote_push_url != name:
                return GitRemote(
                    name=name, fetch_url=remote_fetch_url, push_url=remote_push_url
                )
            else:
                return None
        except exc.LibVCSException:
            return None

    def set_remote(self, name, url, push: bool = False, overwrite=False):
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
            self.run(["remote", "set-url", name, url])
        else:
            self.run(["remote", "add", name, url])
        return self.remote(name=name)

    @staticmethod
    def chomp_protocol(url) -> str:
        """Return clean VCS url from RFC-style url

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
        scheme, netloc, path, query, frag = urlparse.urlsplit(url)
        rev = None
        if "@" in path:
            path, rev = path.rsplit("@", 1)
        url = urlparse.urlunsplit((scheme, netloc, path, query, ""))
        if url.startswith("ssh://git@github.com/"):
            url = url.replace("ssh://", "git+ssh://")
        elif "://" not in url:
            assert "file:" not in url
            url = url.replace("git+", "git+ssh://")
            url = url.replace("ssh://", "")
        return url

    def get_git_version(self) -> str:
        """Return current version of git binary

        Returns
        -------
        git version
        """
        VERSION_PFX = "git version "
        version = self.run(["version"])
        if version.startswith(VERSION_PFX):
            version = version[len(VERSION_PFX) :].split()[0]
        else:
            version = ""
        return ".".join(version.split(".")[:3])

    def status(self) -> dict:
        """Retrieve status of project in dict format.

        Wraps ``git status --sb --porcelain=2``. Does not include changed files, yet.

        Returns
        -------
        Status of current checked out repository

        Examples
        --------

        >>> git_repo.status()
        {
            "branch_oid": 'de6185fde0806e5c7754ca05676325a1ea4d6348',
            "branch_head": 'fix-current-remote-name',
            "branch_upstream": 'origin/fix-current-remote-name',
            "branch_ab": '+0 -0',
            "branch_ahead": '0',
            "branch_behind": '0'
        }
        """
        return extract_status(self.run(["status", "-sb", "--porcelain=2"]))

    def get_current_remote_name(self) -> str:
        """Retrieve name of the remote / upstream of currently checked out branch.

        Returns
        -------
        If upstream the same, returns ``branch_name``.
        If upstream mismatches, returns ``remote_name/branch_name``.
        """
        match = self.status()

        if match.branch_upstream is None:  # no upstream set
            return match.branch_head
        return match.branch_upstream.replace("/" + match.branch_head, "")
