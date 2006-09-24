#!/usr/bin/env python
#
# Copyright (C) 2006  Jeff Rush <jeff@taupro.com>
# This file is distributed under the terms of the GNU GPL license.
# For more information: http://furius.ca/nabu.
#
# $Id$
#

"""
Extract a single, potentially multline, field from a document and write
multiple database records linking each subfield back to the document.
"""

# docutils imports
from docutils import nodes

# nabu imports
from nabu import extract

#-------------------------------------------------------------------------------
#
class TaskareaExtractor(extract.Extractor):
    """A document transform that extracts the 'taskarea' field, reflecting
       one or more task areas to which the document is directed.  The
       task areas are simple strings.  The task area field is used to,
       for example, find all documents about image processing.
    """
    default_priority = 900

    biblifields = ['taskarea', ]

    def apply( self, unid=None, storage=None, pickle_receiver=None ):
        self.unid = unid
        self.storage = storage

        v = self.Visitor(self.document)
        v.xform = self
        self.document.walk(v)

        from pprint import pformat
        self.document.reporter.info(
            'Document extractor: %s' % pformat(v.extracted))

        self.storage.store(self.unid, v.extracted)


    class Visitor(nodes.SparseNodeVisitor):

        def __init__( self, *args, **kwds ):
            nodes.SparseNodeVisitor.__init__(self, *args, **kwds)
            self.extracted = {}
            self.catchname = None

        def visit_docinfo( self, node ):
            self.in_docinfo = 1

        def depart_docinfo( self, node ):
            self.in_docinfo = 0

        def visit_field_name( self, node ):
            fname = node.astext().lower()
            if fname in self.xform.biblifields:
                self.catchname = fname.encode('ascii')

        def visit_field_body( self, node ):
            if self.catchname:
                self.extracted[self.catchname] = node.astext()
                self.catchname = None

        def visit_taskarea( self, node ):
            if 'taskarea' not in self.extracted:
                self.extracted['taskarea'] = node.astext()


class TaskareaStorage(extract.SQLExtractorStorage):
    """
    Taskarea storage.

    The taskarea field is a simple multiline value of strings.  To reflect a
    one-to-many relationship with the document, multiple records are inserted
    into a separate table and linked back to the document.

    Because we follow the taskarea <=> document link in both directions, we
    need an index for quickly finding all entries for a specific document to
    refresh the set of taskareas, and we need an index to find all documents
    that relate to a specific taskarea.  And we place a key constraint on the
    'unid' column to insure an extractor failure does not leave the database
    in an inconsistent state.

    """

    multifield = 'taskarea'

    sql_tables = { 'taskarea': '''

        CREATE TABLE taskarea
        (
           unid TEXT NOT NULL,
           name TEXT NOT NULL

           -- CONSTRAINT taskarea_unid_fk
           --            FOREIGN KEY(unid)
           --            REFERENCES __sources__(unid)
           --            ON DELETE CASCADE
        );
        CREATE INDEX taskarea_unid_idx ON taskarea(unid);
        CREATE INDEX taskarea_name_idx ON taskarea(name);

        '''
        }

    def store( self, unid, data ):
        """
        Split each line of the multiline field and insert a record for each
        that links back to originating document.  Perform the insertions as
        one batched operation to reduce round-trip overhead to the
        database.
        """

        entries = [field.strip() for field in data[self.multifield].split('\n')]

        stmt = "INSERT INTO %s (name, unid) VALUES (%%s, %%s)" % self.multifield
        stmts = [stmt] * len(entries)
        parms = []
        for entry in entries:
            parms += [entry, unid]

        cursor = self.connection.cursor()
        cursor.execute(';'.join(stmts), parms)
        self.connection.commit()
