#!/usr/bin/env python
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
        self.document.walk(self)
        self.finalize()
        
    def initialize(self):
        self.fieldlists = []
        self.curlist = None
        self.curmap = {}

    def finalize(self):
        if self.curlist is not None:
            self.fieldlists.append( (self.curlist, self.curmap) )
            self.curlist = None
            self.curmap = {}

    def getfieldlists(self):
        assert self.curlist is None # you need to finalize
        assert self.curmap == {} # you need to finalize
        return self.fieldlists

    def visit_field_list(self, node):
        if self.curlist:
            self.fieldlists.append( (self.curlist, self.curmap) )
            self.curlist = None
            self.curmap = {}
        self.curlist = node

    def visit_field(self, node):
        assert len(node.children) == 2
        name = node.children[0].astext().lower()
        if name in self.curmap:
            if not isinstance(self.curmap[name], types.ListType):
                self.curmap[name] = [self.curmap[name]]
            self.curmap[name].append(node.children[1])
        else:
            self.curmap[name] = node.children[1]

