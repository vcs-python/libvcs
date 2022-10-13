"""Mercurial Repo object for libvcs.

.. todo::

   The following is from pypa/pip (MIT license):

   - [`HgSync.convert_pip_url`](libvcs.hg.convert_pip_url)
   - [`HgSync.get_url`](libvcs.hg.HgSync.get_url)
   - [`HgSync.get_revision`](libvcs.hg.HgSync.get_revision)
"""  # NOQA E5
import logging
import pathlib
from typing import Any

from libvcs.cmd.hg import Hg

from .base import BaseSync

logger = logging.getLogger(__name__)


class HgSync(BaseSync):
    bin_name = "hg"
    schemes = ("hg", "hg+http", "hg+https", "hg+file")

    def obtain(self, *args: Any, **kwargs: Any) -> None:
        cmd = Hg(dir=self.dir)
        cmd.clone(
            no_update=True,
            quiet=True,
            url=self.url,
        )
        cmd.update(
            quiet=True,
            check_returncode=True,
        )

    def get_revision(self) -> str:
        return self.run(["parents", "--template={rev}"])

    def update_repo(self, *args: Any, **kwargs: Any) -> None:
        cmd = Hg(dir=self.dir)

        if not pathlib.Path(self.dir / ".hg").exists():
            self.obtain()
            self.update_repo()
        else:
            cmd.update()
            cmd.pull(update=True)
