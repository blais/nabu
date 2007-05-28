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


class SoftwareExtractor(extract.Extractor):
    """A document transform that extracts the 'software' field, reflecting
       one or more software components discussed in the document.  The
       component names are simple strings.  The software field is used to,
       for example, find all documents that discuss Nabu in some way.
    """
    default_priority = 900

    biblifields = ['software', ]

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

        def visit_software( self, node ):
            if 'software' not in self.extracted:
                self.extracted['software'] = node.astext()


class SoftwareStorage(extract.SQLExtractorStorage):
    """
    Software (used) storage.

    The software field is a simple multiline value of strings.  To reflect a
    one-to-many relationship with the document, multiple records are inserted
    into a separate table and linked back to the document.

    Because we follow the software <=> document link in both directions, we
    need an index for quickly finding all entries for a specific document to
    refresh the set of all softwares discussed, and we need an index to find
    all documents that discuss a specific piece of software.  And we place a
    key constraint on the 'unid' column to insure an extractor failure does
    not leave the database in an inconsistent state.
    """

    multifield = 'software'

    sql_tables = { 'software': '''

        CREATE TABLE software
        (
           unid TEXT NOT NULL,
           name TEXT NOT NULL

           -- CONSTRAINT software_unid_fk
           --            FOREIGN KEY(unid)
           --            REFERENCES __sources__(unid)
           --            ON DELETE CASCADE
        );
        CREATE INDEX software_unid_idx ON software(unid);
        CREATE INDEX software_name_idx ON software(name);

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
