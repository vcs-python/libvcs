# `libvcs` &middot; [![Python Package](https://img.shields.io/pypi/v/libvcs.svg)](https://pypi.org/project/libvcs/) [![License](https://img.shields.io/github/license/vcs-python/libvcs.svg)](https://github.com/vcs-python/libvcs/blob/master/LICENSE) [![Code Coverage](https://codecov.io/gh/vcs-python/libvcs/branch/master/graph/badge.svg)](https://codecov.io/gh/vcs-python/libvcs)

Example of [sphinx-autoapi] documenting imports, issue
https://github.com/readthedocs/sphinx-autoapi/issues/342

## Reproduction

https://github.com/vcs-python/libvcs/tree/autoapi-duplicates

### Versions

sphinx 5.1.2 sphinx-autoapi 1.9.0

### Configuration

[conf.py](https://github.com/vcs-python/libvcs/blob/autoapi-duplicates/docs/conf.py)

```
extensions = [
    "sphinx.ext.napoleon",
    "autoapi.extension",
    "sphinx.ext.autodoc",
    "sphinx.ext.todo",
    "sphinx.ext.intersphinx",
    "myst_parser",
]

# sphinx-autoapi
autoapi_type = "python"
autoapi_dirs = [project_root / "libvcs"]
autoapi_generate_api_docs = False  # when False, use directives
```
