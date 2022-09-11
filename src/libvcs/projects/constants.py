from typing import Literal, Union

from libvcs import GitProject, MercurialProject, SubversionProject

#: Default VCS systems by string (in :data:`DEFAULT_VCS_CLASS_MAP`)
DEFAULT_VCS_LITERAL = Literal["git", "hg", "svn"]
#: Union of VCS Classes
DEFAULT_VCS_CLASS_UNION = type[Union[GitProject, MercurialProject, SubversionProject]]
#: ``str`` -> ``class`` Map. ``DEFAULT_VCS_CLASS_MAP['git']`` ->
#: :class:`~libvcs.projects.git.GitProject`
DEFAULT_VCS_CLASS_MAP: dict[DEFAULT_VCS_LITERAL, DEFAULT_VCS_CLASS_UNION] = {
    "git": GitProject,
    "svn": SubversionProject,
    "hg": MercurialProject,
}
