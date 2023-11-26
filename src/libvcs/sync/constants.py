"""Constants for use by libvcs.sync."""
from typing import Literal, Union

from libvcs import GitSync, HgSync, SvnSync

#: Default VCS systems by string (in :data:`DEFAULT_VCS_CLASS_MAP`)
DEFAULT_VCS_LITERAL = Literal["git", "hg", "svn"]
#: Union of VCS Classes
DEFAULT_VCS_CLASS_UNION = type[Union[GitSync, HgSync, SvnSync]]
#: ``str`` -> ``class`` Map. ``DEFAULT_VCS_CLASS_MAP['git']`` ->
#: :class:`~libvcs.sync.git.GitSync`
DEFAULT_VCS_CLASS_MAP: dict[DEFAULT_VCS_LITERAL, DEFAULT_VCS_CLASS_UNION] = {
    "git": GitSync,
    "svn": SvnSync,
    "hg": HgSync,
}
