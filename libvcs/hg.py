"""Mercurial Repo object for libvcs.

.. todo::

   The following is from pypa/pip (MIT license):

   - [`MercurialRepo.convert_pip_url`](libvcs.hg.convert_pip_url)
   - [`MercurialRepo.get_url`](libvcs.hg.MercurialRepo.get_url)
   - [`MercurialRepo.get_revision`](libvcs.hg.MercurialRepo.get_revision)
"""  # NOQA E5
import logging
import os

from .base import BaseRepo

logger = logging.getLogger(__name__)


class MercurialRepo(BaseRepo):
    bin_name = "hg"
    schemes = ("hg", "hg+http", "hg+https", "hg+file")

    def __init__(self, url, repo_dir, **kwargs):
        BaseRepo.__init__(self, url, repo_dir, **kwargs)

    def obtain(self):
        self.ensure_dir()

        # Double hyphens between [OPTION]... -- SOURCE [DEST] prevent command injections
        # via aliases
        self.run(["clone", "--noupdate", "-q", "--", self.url, self.path])
        self.run(["update", "-q"])

    def get_revision(self):
        return self.run(["parents", "--template={rev}"])

    def update_repo(self):
        self.ensure_dir()
        if not os.path.isdir(os.path.join(self.path, ".hg")):
            self.obtain()
            self.update_repo()
        else:
            self.run(["update"])
            self.run(["pull", "-u"])
