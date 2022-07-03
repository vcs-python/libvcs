# flake8: NOQA E501
import inspect
import os
import sys
from os.path import dirname, relpath
from pathlib import Path

import libvcs

# Get the project root dir, which is the parent dir of this
doc_path = Path(__file__).parent
project_root = doc_path.parent

sys.path.insert(0, str(project_root))
sys.path.insert(0, str(doc_path / "_ext"))

# package data
about: dict = {}
with open(project_root / "libvcs" / "__about__.py") as fp:
    exec(fp.read(), about)

extensions = [
    "sphinx.ext.napoleon",  # Should go first
    "autoapi.extension",
    "sphinx.ext.autodoc",
    "sphinx.ext.todo",
    "sphinx.ext.intersphinx",
    "myst_parser",
]

templates_path = ["_templates"]

source_suffix = {".rst": "restructuredtext", ".md": "markdown"}

master_doc = "index"

project = about["__title__"]
copyright = about["__copyright__"]

version = "%s" % (".".join(about["__version__"].split("."))[:2])
release = "%s" % (about["__version__"])

exclude_patterns = ["_build"]

html_theme_path: list = []

# sphinx.ext.autodoc
autoclass_content = "both"
autodoc_member_order = "bysource"

# sphinx-autoapi
autoapi_type = "python"
autoapi_dirs = [project_root / "libvcs"]
autoapi_generate_api_docs = False  # when False, use directives

# sphinx.ext.napoleon
napoleon_google_docstring = True
napoleon_include_init_with_doc = True

# sphinx-issues
issues_github_path = "vcs-python/libvcs"

intersphinx_mapping = {
    "py": ("https://docs.python.org/3", None),
    "pip": ("https://pip.pypa.io/en/latest/", None),
    "vcspull": ("https://vcspull.git-pull.com/", None),
}
