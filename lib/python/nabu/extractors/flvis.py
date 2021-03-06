#
# Copyright (C) 2005  Martin Blais <blais@furius.ca>
# This file is distributed under the terms of the GNU GPL license.
# For more information: http://furius.ca/nabu.
#
# $Id$
#

"""
Field list visitor convenience class for extractors.
"""

# stdlib imports
import types

# docutils imports
from docutils import nodes


class FieldListVisitor(nodes.SparseNodeVisitor):
    """
    A visitor that accumulates field lists, and that returns dictionaries for
    each of the lists.  If there are multiple equal field names, a list of the
    values is associated to that name. The field names are taken to be
    case-insensitive.
    """

    def __init__(self, *args, **kwds):
        nodes.SparseNodeVisitor.__init__(self, *args, **kwds)

    def apply(self):
        self.initialize()
        self.document.walkabout(self)

    def initialize(self):
        self.fieldlists = []
        self.curlist = []

    def getfieldlists(self):
        return self.fieldlists

    def visit_field_list(self, node):
        self.curlist.append( (node, {}) )

    def depart_field_list(self, node):
        self.fieldlists.append(self.curlist.pop(-1))

    visit_docinfo = visit_field_list
    depart_docinfo = depart_field_list

    def visit_field(self, node):
        assert len(node.children) == 2
        name = node.children[0].astext().lower()
        curnode, curmap = self.curlist[-1]
        if name in curmap:
            if not isinstance(curmap[name], types.ListType):
                curmap[name] = [curmap[name]]
            curmap[name].append(node.children[1])
        else:
            curmap[name] = node.children[1]

