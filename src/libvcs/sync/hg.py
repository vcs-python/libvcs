"""Tool to manage a local hg (Mercurial) working copy from a repository.

.. todo::

   The following is from pypa/pip (MIT license):

   - :meth:`~libvcs.sync.base.BaseSync.from_pip_url`
   - :meth:`~libvcs.sync.hg.HgSync.get_revision`
"""  # E5

from __future__ import annotations

import dataclasses
import logging
import pathlib
import typing as t

from libvcs import exc
from libvcs._internal.run import ProgressCallbackProtocol
from libvcs._internal.types import StrPath
from libvcs.cmd.hg import Hg

from .base import BaseSync, SyncResult, WorkingCopyPosition

logger = logging.getLogger(__name__)


@dataclasses.dataclass(frozen=True)
class HgOptions:
    """Backend-specific options for Mercurial synchronization."""

    ssh: str | None = None
    remote_cmd: str | None = None
    pull: bool = False
    stream: bool = False
    tls_verify: bool = True

    def __post_init__(self) -> None:
        """Validate Mercurial option types without running Mercurial."""
        for name in ("ssh", "remote_cmd"):
            value = getattr(self, name)
            if value is not None and not isinstance(value, str):
                msg = f"{name} must be a string or None"
                raise TypeError(msg)
        for name in ("pull", "stream", "tls_verify"):
            if not isinstance(getattr(self, name), bool):
                msg = f"{name} must be a boolean"
                raise TypeError(msg)


class HgSync(BaseSync):
    """Tool to manage a local hg (Mercurial) repository cloned from a remote one."""

    bin_name = "hg"
    schemes = ("hg", "hg+http", "hg+https", "hg+file")
    cmd: Hg
    options_type = HgOptions

    def __init__(
        self,
        *,
        url: str,
        path: StrPath,
        options: HgOptions | None = None,
        progress_callback: ProgressCallbackProtocol | None = None,
        rev: str | None = None,
    ) -> None:
        """Local Mercurial repository.

        Parameters
        ----------
        url : str
            Mercurial repository URL.
        """
        if options is None:
            options = HgOptions()
        elif not isinstance(options, HgOptions):
            msg = "options must be an HgOptions instance"
            raise TypeError(msg)
        self.options = options
        super().__init__(
            url=url,
            path=path,
            progress_callback=progress_callback,
            rev=rev,
        )

        self.cmd = Hg(path=path, progress_callback=self.progress_callback)

    def obtain(self, *args: t.Any, **kwargs: t.Any) -> None:
        """Clone and update a Mercurial repository to this location."""
        self.cmd.clone(
            no_update=True,
            quiet=True,
            url=self.url,
            ssh=self.options.ssh,
            remote_cmd=self.options.remote_cmd,
            pull=self.options.pull,
            stream=self.options.stream,
            insecure=not self.options.tls_verify,
            check_returncode=True,
        )
        self.cmd.update(
            quiet=True,
            check_returncode=True,
        )

    def get_revision(self) -> str:
        """Get latest revision of this mercurial repository."""
        return self.run(["parents", "--template={rev}"])

    def get_position(self) -> WorkingCopyPosition:
        """Read the parent and active bookmark or named branch without pulling."""
        revision, bookmark = self.cmd.run(
            ["log", "-r", ".", "-T", "{node}\\0{activebookmark}"],
        ).split("\0")
        if bookmark:
            return WorkingCopyPosition(revision, bookmark, "bookmark", follows=True)
        branch = self.cmd.run(["branch"]).strip()
        return WorkingCopyPosition(revision, branch, "branch", follows=True)

    def update_repo(self, *args: t.Any, **kwargs: t.Any) -> SyncResult:
        """Pull changes from remote Mercurial repository into this one.

        Returns
        -------
        SyncResult
            Result of the sync operation, with any errors recorded.
        """
        result = SyncResult()
        if not pathlib.Path(self.path / ".hg").exists():
            try:
                self.obtain()
            except exc.CommandError as e:
                self.log.exception("Failed to obtain repository")
                result.add_error("obtain", str(e), exception=e)
                return result
            return self.update_repo()
        else:
            try:
                self.cmd.update()
                self.cmd.pull(
                    update=True,
                    ssh=self.options.ssh,
                    remote_cmd=self.options.remote_cmd,
                    insecure=not self.options.tls_verify,
                )
            except exc.CommandError as e:
                result.add_error("pull", str(e), exception=e)
        return result
