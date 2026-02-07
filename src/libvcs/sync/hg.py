"""Tool to manage a local hg (Mercurial) working copy from a repository.

.. todo::

   The following is from pypa/pip (MIT license):

   - [`HgSync.convert_pip_url`](libvcs.hg.convert_pip_url)
   - [`HgSync.get_url`](libvcs.hg.HgSync.get_url)
   - [`HgSync.get_revision`](libvcs.hg.HgSync.get_revision)
"""  # E5

from __future__ import annotations

import logging
import pathlib
import typing as t

from libvcs import exc
from libvcs._internal.types import StrPath
from libvcs.cmd.hg import Hg

from .base import BaseSync, SyncResult

logger = logging.getLogger(__name__)


class HgSync(BaseSync):
    """Tool to manage a local hg (Mercurial) repository cloned from a remote one."""

    bin_name = "hg"
    schemes = ("hg", "hg+http", "hg+https", "hg+file")
    cmd: Hg

    def __init__(
        self,
        *,
        url: str,
        path: StrPath,
        **kwargs: t.Any,
    ) -> None:
        """Local Mercurial repository.

        Parameters
        ----------
        url : str
            URL in subversion repository
        """
        super().__init__(url=url, path=path, **kwargs)

        self.cmd = Hg(path=path, progress_callback=self.progress_callback)

    def obtain(self, *args: t.Any, **kwargs: t.Any) -> None:
        """Clone and update a Mercurial repository to this location."""
        self.cmd.clone(
            no_update=True,
            quiet=True,
            url=self.url,
        )
        self.cmd.update(
            quiet=True,
            check_returncode=True,
        )

    def get_revision(self) -> str:
        """Get latest revision of this mercurial repository."""
        return self.run(["parents", "--template={rev}"])

    def update_repo(self, *args: t.Any, **kwargs: t.Any) -> SyncResult:
        """Pull changes from remote Mercurial repository into this one."""
        result = SyncResult()
        if not pathlib.Path(self.path / ".hg").exists():
            self.obtain()
            return self.update_repo()
        else:
            try:
                self.cmd.update()
                self.cmd.pull(update=True)
            except exc.CommandError as e:
                result.add_error("pull", str(e), exception=e)
        return result
