"""Constants shared across ``libvcs.url``."""

RE_USER = r"""
    ((?P<user>[^/:@]+)@)?
"""
"""Optional user, e.g. 'git@'"""

# Credit, pip (license: MIT):
# https://github.com/pypa/pip/blob/22.1.2/src/pip/_internal/vcs/git.py#L39-L52
# We modified it to have groupings
SCP_REGEX = r"""
    # Server, e.g. 'github.com'.
    (?P<hostname>([^/:]+))
    (?P<separator>:)
    # The server-side path. e.g. 'user/project.git'. Must start with an
    # alphanumeric character so as not to be confusable with a Windows paths
    # like 'C:/foo/bar' or 'C:\foo\bar'.
    (?P<path>(\w[^:.]+))
"""
"""Regular expression for scp-style of git URLs."""
