# Most of this is copied from Sphinx
# Credit:
# - https://gist.github.com/agoose77/e8f0f8f7d7133e73483ca5c2dd7b907f
# - https://gist.github.com/asmeurer/5009f8845f864bd671769d10e07d1184
from typing import Generator, List, TypeVar, Union

import sphinx.environment.collectors.toctree as toctree_collector
from docutils import nodes
from docutils.nodes import Element
from sphinx import addnodes
from sphinx.application import Sphinx
from sphinx.environment.adapters.toctree import TocTree
from sphinx.transforms import SphinxContentsFilter
from sphinx.util import logging

N = TypeVar("N")

logger = logging.getLogger(__name__)


class BetterTocTreeCollector(toctree_collector.TocTreeCollector):
    def process_doc(self, app: Sphinx, doctree: nodes.document) -> None:
        """Build a TOC from the doctree and store it in the inventory."""
        docname = app.env.docname
        numentries = [0]  # nonlocal again...

        # This is changed to a generator, and the class condition removed
        def traverse_in_section(node: Element) -> Generator[Element, None, None]:
            """Like traverse(), but stay within the same section."""
            yield node
            for child in node.children:
                if isinstance(child, nodes.section):
                    continue
                elif isinstance(child, nodes.Element):
                    yield from traverse_in_section(child)

        def build_toc(node: Element, depth: int = 1) -> nodes.bullet_list:
            # The logic here is a bit confusing.
            # It looks like section nodes are expected to be top-level within a section.
            entries: List[Element] = []

            current_class = None

            if isinstance(node, addnodes.desc):
                section_nodes: Union[List[nodes.Node], List[addnodes.desc]] = [node]
            else:
                section_nodes = node.children

            for sectionnode in section_nodes:
                # find all toctree nodes in this section and add them
                # to the toc (just copying the toctree node which is then
                # resolved in self.get_and_resolve_doctree)
                if isinstance(sectionnode, nodes.section):
                    title = sectionnode[0]
                    # copy the contents of the section title, but without references
                    # and unnecessary stuff
                    visitor = SphinxContentsFilter(doctree)
                    title.walkabout(visitor)
                    nodetext = visitor.get_entry_text()
                    # if nodetext and nodetext[0] == "ak.ArrayBuilder":
                    # print(node)
                    # break
                    if not numentries[0]:
                        # for the very first toc entry, don't add an anchor
                        # as it is the file's title anyway
                        anchorname = ""
                    else:
                        anchorname = "#" + sectionnode["ids"][0]
                    numentries[0] += 1
                    # make these nodes:
                    # list_item -> compact_paragraph -> reference
                    reference = nodes.reference(
                        "",
                        "",
                        internal=True,
                        refuri=docname,
                        anchorname=anchorname,
                        *nodetext,
                    )
                    para = addnodes.compact_paragraph("", "", reference)
                    i: Element = nodes.list_item("", para)
                    sub_item = build_toc(sectionnode, depth + 1)
                    if sub_item:
                        i += sub_item
                    entries.append(i)
                elif isinstance(sectionnode, addnodes.only):
                    onlynode = addnodes.only(expr=sectionnode["expr"])
                    blist = build_toc(sectionnode, depth)
                    if blist:
                        onlynode += blist.children
                        entries.append(onlynode)
                # Otherwise, for a generic element we allow recursion into the section
                elif isinstance(sectionnode, nodes.Element):
                    for node in traverse_in_section(sectionnode):
                        if isinstance(node, addnodes.toctree):
                            toc_item = node.copy()
                            entries.append(toc_item)
                            # important: do the inventory stuff
                            TocTree(app.env).note(docname, node)
                        # For signatures within some section, we add them to the ToC
                        elif isinstance(node, addnodes.desc):
                            title = node.children[0]

                            fullname = title.attributes["fullname"]
                            classname = title.attributes["class"]
                            nodetype = node.attributes["objtype"]

                            if classname != current_class:
                                current_class = fullname
                            else:
                                subtoc = build_toc(node, depth + 1)
                                if subtoc:
                                    entries.append(subtoc)
                                continue

                            if nodetype in ["function", "method"]:
                                fullname += "()"

                            nodetext = [nodes.Text(fullname)]

                            if not numentries[0]:
                                # for the very first toc entry, don't add an anchor
                                # as it is the file's title anyway
                                anchorname = ""
                            elif not title["ids"]:
                                # Skip entries with :noindex: (they do not get anchors)
                                continue
                            else:
                                anchorname = "#" + title["ids"][0]
                            numentries[0] += 1
                            # make these nodes:
                            # list_item -> compact_paragraph -> reference
                            reference = nodes.reference(
                                "",
                                "",
                                internal=True,
                                refuri=docname,
                                anchorname=anchorname,
                                *nodetext,
                            )

                            para = addnodes.compact_paragraph("", "", reference)
                            item: Element = nodes.list_item("", para)
                            entries.append(item)
                        # Glossary entries
                        elif isinstance(node, nodes.term):
                            nodetext = []
                            for n in node.children:
                                if isinstance(n, addnodes.pending_xref):
                                    nodetext.extend(n.children)
                                else:
                                    nodetext.append(n)

                            if not numentries[0]:
                                # for the very first toc entry, don't add an anchor
                                # as it is the file's title anyway
                                anchorname = ""
                            elif not node["ids"]:
                                continue
                            else:
                                anchorname = "#" + node["ids"][0]
                            numentries[0] += 1
                            # make these nodes:
                            # list_item -> compact_paragraph -> reference
                            reference = nodes.reference(
                                "",
                                "",
                                *nodetext,
                                internal=True,
                                refuri=docname,
                                anchorname=anchorname,
                            )
                            para = addnodes.compact_paragraph("", "", reference)
                            term_item: Element = nodes.list_item("", para)
                            entries.append(term_item)

            if entries:
                return nodes.bullet_list("", *entries)
            return None

        toc = build_toc(doctree)
        assert docname in app.env.tocs
        if toc:
            app.env.tocs[docname] = toc
        else:
            app.env.tocs[docname] = nodes.bullet_list("")
        app.env.toc_num_entries[docname] = numentries[0]


def setup(app: Sphinx) -> None:
    app.add_env_collector(BetterTocTreeCollector)
