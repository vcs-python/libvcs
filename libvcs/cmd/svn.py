import pathlib
from typing import TYPE_CHECKING, Literal, Sequence, Union

from .core import run

if TYPE_CHECKING:
    from subprocess import _CMD


class Svn:
    def __init__(self, dir: pathlib.Path):
        self.dir: pathlib.Path = dir

    def run(self, args: "_CMD", quiet: Union[bool, None] = None, **kwargs):
        """
        Passing None means the flag won't be passed unless otherwise stated.

        Wraps svn's `Options
        <https://svnbook.red-bean.com/en/1.7/svn.ref.svn.html#svn.ref.svn.sw>`_.

        Parameters
        ----------
        quiet :
            -q / --quiet
        username :
            --username
        password :
            --password
        no_auth_cache :
            --no-auth-cache
        non_interactive :
            --non-interactive
        trust_server_cert :
            --trust-server-cert
        config_dir :
            --config-dir
        config_option :
            --config-option. ``FILE:SECTION:OPTION=[VALUE]``
        """

        if isinstance(args, Sequence):
            cli_args = ["svn", *args]
        else:
            cli_args = f"svn {args}"
        return run(cmd=cli_args)

    def checkout(
        self,
        depth: Union[Literal["infinity", "empty", "files", "immediates"], None] = None,
    ):
        """
        Passing None means the flag won't be passed unless otherwise stated.

        Wraps `svn checkout
        <https://svnbook.red-bean.com/en/1.7/svn.ref.svn.c.checkout.html>`_ (co).

        Parameters
        ----------
        depth :
            Sparse checkut support, Optional
        """
        local_flags: list[str] = []

        if depth is not None:
            local_flags.append(depth)

        self.run(["checkout", *local_flags])
