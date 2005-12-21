#!/usr/bin/env python
#
# Copyright (C) 2005  Martin Blais <blais@furius.ca>
# This file is distributed under the terms of the GNU GPL license.
# For more information: http://furius.ca/nabu.
#
# $Id$
#

"""
Extract links with description and keywords from line-blocks.
"""

# stdlib imports
import re

# docutils imports
from docutils import nodes

# nabu imports
from nabu import extract


class Extractor(extract.Extractor):
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
            self.x.storage.store(self.x.unid, lurl, ldesc, lkeys)


class Storage(extract.SQLExtractorStorage):
    """
    Link storage.
    """
    sql_tables = { 'link': '''

        CREATE TABLE link
        (
           unid TEXT NOT NULL,
           url TEXT,
           description TEXT,
           keywords TEXT
        )

        '''
        }

    def store( self, unid, url, description, keywords ):

        cols = ('unid', 'url', 'description', 'keywords')
            
        cursor = self.connection.cursor()
        cursor.execute("""
          INSERT INTO link (unid, url, description, keywords)
            VALUES (%s, %s, %s, %s)
          """, (unid, url, description, keywords))

        self.connection.commit()
        

