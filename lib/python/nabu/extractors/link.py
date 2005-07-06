#!/usr/bin/env python
#
# Copyright (C) 2005  Martin Blais <blais@furius.ca>
# This file is distributed under the terms of the GNU GPL license.
# For more information: http://furius.ca/nabu.
#
# $Id$
#

"""
Process links inside of documents.
"""

# stdlib imports
import re

# docutils imports
from docutils import nodes

# other imports
from sqlobject import *

# nabu imports
from nabu import extract


class LinkExtractor(extract.Extractor):
    """
    Transform that finds links represented as line-blocks of less than lines,
    where if it has three lines, the first line is taken to be a description,
    the second line is a URL (reference), and the third line a comma-separated
    set of keywords.  Like this::
    
      |   From Montreal -- Classifieds for Japanese living in Montreal
      |   http://www.from-montreal.com/
      |   montreal, classified, ads, japan

    The following forms are also accepted.

      | Description of a link, no keywords
      | http://this-is-a-reference.com/target.html

      | http://this-is-a-reference.com/target.html
      | just, the, keywords
    
      | http://this-is-a-reference.com/target.html

    """
    default_priority = 900

    def apply( self, **kwargs ):
        self.unid, self.storage = kwargs['unid'], kwargs['storage']

        v = self.Visitor(self.document)
        v.x = self
        self.document.walk(v)

    class Visitor(nodes.SparseNodeVisitor):

        def visit_line_block( self, node ):
            # check the number of lines
            if len(node.children) not in (1, 2, 3):
                return
            
            ldesc = lurl = lkeys = ''

            # check the various patterns above
            def checkref( lineref ):
                if not lineref.children[0]:
                    return False
                if not isinstance(lineref.children[0], nodes.reference):
                    return False
                return lineref.children[0]
            
            if len(node.children) == 1:
                ref = checkref(node.children[0])
                if not ref:
                    return
                lurl = ref.astext()

            elif len(node.children) == 2:
                ref = checkref(node.children[1])
                if ref:
                    lurl = ref.astext()
                    ldesc = node.children[0].astext()
                else:
                    ref = checkref(node.children[0])
                    if ref:
                        lurl = ref.astext()
                        lkeys = node.children[1].astext()
                    else:
                        return
                    
            elif len(node.children) == 3:
                ref = checkref(node.children[1])
                lurl = ref.astext()
                ldesc = node.children[0].astext()
                lkeys = node.children[2].astext()
            else:
                return
            
            # add a class to the document for later rendering
            node.attributes['classes'].append('bookmark')

            # store the bookmark
            self.x.storage.store(self.x.unid, ldesc, lurl, lkeys)
                

class Link(SQLObject):
    """
    Storage for document information.
    """
    unid = StringCol(notNull=1)

    url = StringCol()
    description = UnicodeCol()
    keywords = UnicodeCol()


class LinkStorage(extract.SQLObjectExtractorStorage):
    """
    Link storage.
    """

    sqlobject_classes = [Link]

    def store( self, unid, url, description, keywords ):
        Link(unid=unid,
             url=url,
             description=description,
             keywords=keywords)
