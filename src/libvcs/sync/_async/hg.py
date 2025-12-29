"""Async tool to manage a local hg (Mercurial) working copy from a repository.

Async equivalent of :mod:`libvcs.sync.hg`.

Note
----
This is an internal API not covered by versioning policy.
"""

from __future__ import annotations

import pathlib
import typing as t

from libvcs._internal.async_run import AsyncProgressCallbackProtocol
from libvcs._internal.types import StrPath
from libvcs.cmd._async.hg import AsyncHg
from libvcs.sync._async.base import AsyncBaseSync


class AsyncHgSync(AsyncBaseSync):
    """Async tool to manage a local hg (Mercurial) repository cloned from a remote one.

    Async equivalent of :class:`~libvcs.sync.hg.HgSync`.

    Examples
    --------
    >>> import asyncio
    >>> async def example():
    ...     repo = AsyncHgSync(
    ...         url="https://hg.example.com/repo",
    ...         path="/tmp/myrepo",
    ...     )
    ...     await repo.obtain()
    ...     await repo.update_repo()
    >>> # asyncio.run(example())
    """

    bin_name = "hg"
    schemes = ("hg", "hg+http", "hg+https", "hg+file")
    cmd: AsyncHg

    def __init__(
        self,
        *,
        url: str,
        path: StrPath,
        progress_callback: AsyncProgressCallbackProtocol | None = None,
        **kwargs: t.Any,
    ) -> None:
        """Initialize async Mercurial repository manager.

        Parameters
        ----------
        url : str
            URL of the Mercurial repository
        path : str | Path
            Local path for the repository
        progress_callback : AsyncProgressCallbackProtocol, optional
            Async callback for progress updates
        """
        super().__init__(
            url=url, path=path, progress_callback=progress_callback, **kwargs
        )

        self.cmd = AsyncHg(path=path, progress_callback=self.progress_callback)

    async def obtain(self, *args: t.Any, **kwargs: t.Any) -> None:
        """Clone and update a Mercurial repository to this location asynchronously.

        Async equivalent of :meth:`~libvcs.sync.hg.HgSync.obtain`.
        """
        self.ensure_dir()

        self.log.info("Cloning.")
        await self.cmd.clone(
            no_update=True,
            quiet=True,
            url=self.url,
            log_in_real_time=True,
        )
        await self.cmd.update(
            quiet=True,
            check_returncode=True,
            log_in_real_time=True,
        )

    async def get_revision(self) -> str:
        """Get latest revision of this mercurial repository asynchronously.

        Async equivalent of :meth:`~libvcs.sync.hg.HgSync.get_revision`.

        Returns
        -------
        str
            Current revision number
        """
        return await self.run(["parents", "--template={rev}"])

    async def update_repo(self, *args: t.Any, **kwargs: t.Any) -> None:
        """Pull changes from remote Mercurial repository asynchronously.

        Async equivalent of :meth:`~libvcs.sync.hg.HgSync.update_repo`.
        """
        self.ensure_dir()

        if not pathlib.Path(self.path / ".hg").exists():
            await self.obtain()
            await self.update_repo()
        else:
            await self.cmd.update()
            await self.cmd.pull(update=True)
