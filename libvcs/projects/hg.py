"""Mercurial Repo object for libvcs.

.. todo::

   The following is from pypa/pip (MIT license):

   - [`MercurialProject.convert_pip_url`](libvcs.hg.convert_pip_url)
   - [`MercurialProject.get_url`](libvcs.hg.MercurialProject.get_url)
   - [`MercurialProject.get_revision`](libvcs.hg.MercurialProject.get_revision)
"""  # NOQA E5
import logging
import pathlib

from .base import BaseProject

logger = logging.getLogger(__name__)


class MercurialProject(BaseProject):
    bin_name = "hg"
    schemes = ("hg", "hg+http", "hg+https", "hg+file")

    def obtain(self, *args, **kwargs):
        self.ensure_dir()

        # Double hyphens between [OPTION]... -- SOURCE [DEST] prevent command injections
        # via aliases
        self.run(["clone", "--noupdate", "-q", "--", self.url, self.dir])
        self.run(["update", "-q"])

    def get_revision(self):
        return self.run(["parents", "--template={rev}"])

    def update_repo(self, *args, **kwargs):
        self.ensure_dir()
        if not pathlib.Path(self.dir / ".hg").exists():
            self.obtain()
            self.update_repo()
        else:
            self.run(["update"])
            self.run(["pull", "-u"])
