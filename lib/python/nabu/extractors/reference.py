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

# nabu imports
from nabu import extract


class Extractor(extract.Extractor):
    """
    Stores all external references in a table.
    """
    default_priority = 900

    def apply(self, **kwargs):
        self.unid, self.storage = kwargs['unid'], kwargs['storage']

        v = self.Visitor(self.document)
        v.x = self
        self.document.walk(v)

    class Visitor(nodes.SparseNodeVisitor):

        def visit_reference(self, node):
            # store the bookmark
            if 'refuri' in node.attributes:
                self.x.storage.store(self.x.unid, node.attributes['refuri'])
                

class Storage(extract.SQLExtractorStorage):
    """
    Reference storage.
    """
    sql_tables = { 'reference': '''

        CREATE TABLE reference
        (
           unid TEXT NOT NULL,
           url TEXT
        )

        '''
        }

    def store(self, unid, url):
        cursor = self.connection.cursor()
        cursor.execute("""
          INSERT INTO reference (unid, url) VALUES (%s, %s)
          """, (unid, url))
        self.connection.commit()

