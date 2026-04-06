"""Sphinx configuration for libvcs."""

from __future__ import annotations

import pathlib
import sys
import typing as t

if t.TYPE_CHECKING:
    from docutils import nodes
    from sphinx import addnodes
    from sphinx.application import Sphinx
    from sphinx.domains.python import PythonDomain
    from sphinx.environment import BuildEnvironment

from gp_sphinx.config import make_linkcode_resolve, merge_sphinx_config

import libvcs

# Get the project root dir, which is the parent dir of this
cwd = pathlib.Path(__file__).parent
project_root = cwd.parent
src_root = project_root / "src"

sys.path.insert(0, str(src_root))

# package data
about: dict[str, str] = {}
with (src_root / "libvcs" / "__about__.py").open() as fp:
    exec(fp.read(), about)

conf = merge_sphinx_config(
    project=about["__title__"],
    version=about["__version__"],
    copyright=about["__copyright__"],
    source_repository=f"{about['__github__']}/",
    docs_url=about["__docs__"],
    source_branch="master",
    light_logo="img/libvcs.svg",
    dark_logo="img/libvcs-dark.svg",
    extra_extensions=[
        "sphinx.ext.todo",
        "sphinx_autodoc_pytest_fixtures",
    ],
    intersphinx_mapping={
        "py": ("https://docs.python.org/3", None),
        "pip": ("https://pip.pypa.io/en/latest/", None),
        "pytest": ("https://docs.pytest.org/en/stable/", None),
        "vcspull": ("https://vcspull.git-pull.com/", None),
        "gp-libs": ("https://gp-libs.git-pull.com/", None),
    },
    linkcode_resolve=make_linkcode_resolve(libvcs, about["__github__"]),
    theme_options={
        "announcement": (
            "<em>Friendly reminder:</em> 📌 Pin the package, libvcs is"
            " pre-1.0 and APIs will be <a href='/migration.html'>changing</a>"
            " throughout 2026."
        ),
    },
    html_favicon="_static/favicon.ico",
    html_extra_path=["manifest.json"],
    rediraffe_redirects="redirects.txt",
)
globals().update(conf)


def _on_missing_class_reference(
    app: Sphinx,
    env: BuildEnvironment,
    node: addnodes.pending_xref,
    contnode: nodes.TextElement,
) -> nodes.reference | None:
    if node.get("refdomain") != "py" or node.get("reftype") != "class":
        return None
    from sphinx.util.nodes import make_refnode

    py_domain: PythonDomain = env.get_domain("py")  # type: ignore[assignment]
    target = node.get("reftarget", "")
    matches = py_domain.find_obj(env, "", "", target, None, 1)
    if not matches:
        return None
    _name, obj_entry = matches[0]
    return make_refnode(
        app.builder,
        node.get("refdoc", ""),
        obj_entry.docname,
        obj_entry.node_id,
        contnode,
    )


def setup(app: Sphinx) -> None:
    """Connect missing-reference handler to resolve py:data as :class: links."""
    app.connect("missing-reference", _on_missing_class_reference)
