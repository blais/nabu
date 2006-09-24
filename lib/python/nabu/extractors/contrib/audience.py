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
class AudienceExtractor(extract.Extractor):
    """ A document transform that extracts the 'audience' field, reflecting
        one or more targets to whom the document is directed.  The targets
        are simple strings.
    """
    default_priority = 900

    biblifields = ['audience', ]

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

        def visit_audience( self, node ):
            if 'audience' not in self.extracted:
                self.extracted['audience'] = node.astext()


class AudienceStorage(extract.SQLExtractorStorage):
    """
    Audience storage.

    The audience field is a simple multiline value of strings.  To reflect a
    one-to-many relationship with the document, multiple records are inserted
    into a separate table and linked back to the document.

    Because we follow the audience <=> document link in both directions, we
    need an index for quickly finding all entries for a specific document to
    refresh the set of audiences, and we need an index to find all documents
    written to a specific audience.  And we place a key constraint on the
    'unid' column to insure an extractor failure does not leave the database
    in an inconsistent state.
    """

    multifield = 'audience'

    sql_tables = { 'audience': '''

        CREATE TABLE audience
        (
           unid TEXT NOT NULL,
           name TEXT NOT NULL

           -- CONSTRAINT audience_unid_fk
           --            FOREIGN KEY(unid)
           --            REFERENCES __sources__(unid)
           --            ON DELETE CASCADE
        );
        CREATE INDEX audience_unid_idx ON audience(unid);
        CREATE INDEX audience_name_idx ON audience(name);

        '''
        }

    def store( self, unid, data ):
        """Split each line of the multiline field and insert a record for each
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
