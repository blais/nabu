#!/usr/bin/env python
#
# Copyright (C) 2005  Martin Blais <blais@furius.ca>
# This file is distributed under the terms of the GNU GPL license.
# For more information: http://furius.ca/nabu.
#
# $Id$
#

"""
Extract external references, simply.
"""

# docutils imports
from docutils import nodes

# other imports
from sqlobject import *

# nabu imports
from nabu import extract


class ReferenceExtractor(extract.Extractor):
    """
    Stores all external references in a table.
    """
    default_priority = 900

    def apply( self, **kwargs ):
        self.unid, self.storage = kwargs['unid'], kwargs['storage']

        v = self.Visitor(self.document)
        v.x = self
        self.document.walk(v)

    class Visitor(nodes.SparseNodeVisitor):

        def visit_reference( self, node ):
            # store the bookmark
            self.x.storage.store(self.x.unid, node.attributes['refuri'])
                

class Reference(SQLObject):
    """
    Storage for document information.
    """
    unid = StringCol(notNull=1)

    url = StringCol()


class ReferenceStorage(extract.SQLObjectExtractorStorage):
    """
    Reference storage.
    """

    sqlobject_classes = [Reference]

    def store( self, unid, url ):
        Reference(unid=unid, url=url)
