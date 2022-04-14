from typing import Dict, Literal, Type, Union

from libvcs import GitProject, MercurialProject, SubversionProject

#: Default VCS systems by string (in :data:`DEFAULT_VCS_CLASS_MAP`)
DEFAULT_VCS_LITERAL = Literal["git", "hg", "svn"]
#: Union of VCS Classes
DEFAULT_VCS_CLASS_UNION = Type[Union[GitProject, MercurialProject, SubversionProject]]
#: ``str`` -> ``class`` Map. ``DEFAULT_VCS_CLASS_MAP['git']`` ->
#: :class:`~libvcs.projects.git.GitProject`
DEFAULT_VCS_CLASS_MAP: Dict[DEFAULT_VCS_LITERAL, DEFAULT_VCS_CLASS_UNION] = {
    "git": GitProject,
    "svn": SubversionProject,
    "hg": MercurialProject,
}
