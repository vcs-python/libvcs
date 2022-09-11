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

from .base import BaseSync

logger = logging.getLogger(__name__)


class HgSync(BaseSync):
    bin_name = "hg"
    schemes = ("hg", "hg+http", "hg+https", "hg+file")

    def obtain(self, *args: Any, **kwargs: Any) -> None:
        self.ensure_dir()

        # Double hyphens between [OPTION]... -- SOURCE [DEST] prevent command injections
        # via aliases
        self.run(["clone", "--noupdate", "-q", "--", self.url, str(self.dir)])
        self.run(["update", "-q"])

    def get_revision(self) -> str:
        return self.run(["parents", "--template={rev}"])

    def update_repo(self, *args: Any, **kwargs: Any) -> None:
        self.ensure_dir()
        if not pathlib.Path(self.dir / ".hg").exists():
            self.obtain()
            self.update_repo()
        else:
            self.run(["update"])
            self.run(["pull", "-u"])
