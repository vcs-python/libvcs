from typing import Dict, Literal, Type, Union

from libvcs import GitRepo, MercurialRepo, SubversionRepo

#: Default VCS systems by string (in :data:`DEFAULT_VCS_CLASS_MAP`)
DEFAULT_VCS_LITERAL = Literal["git", "hg", "svn"]
#: Union of VCS Classes
DEFAULT_VCS_CLASS_UNION = Type[Union[GitRepo, MercurialRepo, SubversionRepo]]
#: String -> Class Map. ``DEFAULT_VCS_CLASS_MAP['git']`` -> :class:`~libvcs.git.GitRepo`
DEFAULT_VCS_CLASS_MAP: Dict[DEFAULT_VCS_LITERAL, DEFAULT_VCS_CLASS_UNION] = {
    "git": GitRepo,
    "svn": SubversionRepo,
    "hg": MercurialRepo,
}
