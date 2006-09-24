#!/usr/bin/env python
#
# Copyright (C) 2005  Jeff Rush <jeff@taupro.com>
# This file is distributed under the terms of the GNU GPL license.
# For more information: http://furius.ca/nabu.
#
# $Id$
#

"""
Extract selected fields from doculates (small documents).

The 'doctype' field is to permit grouping of documents by type, such as
quickanswers, essays, projects, etc.

The 'title' and 'date' fields are obvious, reflecting the title and some
internal date of the document, usually the authoring date.

The 'discourse' field is for detailing what the document is about.  Similar to
a title, it is less formal.  For example, a title might be "Desktop Publishing with ReportLab"
but the discourse would be "generating PDF files using Python".

The 'uploaded' date reflects the last time the document changed and was
extracted into the record.  Note that with command-line options to Nabu that
it is possible to re-extract a record without the document actually changing
so this date cannot accurately show the document _really_ changed.

The 'locale' field is for indicating the (human) language in which
the document is written, such as 'en', 'fr', 'it', etc.

The 'proglang' field on the other hand is for a single-valued name of the
programming language being discussed in the document.  A special case, I use
it for documents that contrast Python with say, Perl, in which case proglang
is set to 'Perl'.

The 'platform' field is for indicating the operating system platform the
document is written about, such as installation instructions for Red Hat
Linux.

The 'company' field is to indicate a particular company about which the
document is written, such as a Python Success Story.

The 'industry' field is for tagging documents that relate to a specific
industry such as web hosting or book publishing.  I use it with regard to
Python Success Stories so that a reader can look for articles in his specific
industry.

"""

# stdlib imports
import re, datetime, copy
import pickle
##import cPickle as pickle

# docutils imports
from docutils import nodes

# nabu imports
from nabu import extract

#-------------------------------------------------------------------------------
#
class DoculateExtractor(extract.Extractor):
    """
    Transform that extracts some basic information about the doculate as a
    whole.  For example, it extracts the title and author fields.
    """
    default_priority = 900

    biblifields = ['title', 'doctype', 'discourse', 'locale', 'platform', 'company', 'industry', 'proglang', 'date']

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

        def visit_title( self, node ):
            if 'title' not in self.extracted:
                self.extracted['title'] = node.astext()

        def visit_doctype( self, node ):
            if 'doctype' not in self.extracted:
                self.extracted['doctype'] = node.astext()

        def visit_discourse( self, node ):
            if 'discourse' not in self.extracted:
                self.extracted['discourse'] = node.astext()

        def visit_locale( self, node ):
            if 'locale' not in self.extracted:
                self.extracted['locale'] = node.astext()

        def visit_platform( self, node ):
            if 'platform' not in self.extracted:
                self.extracted['platform'] = node.astext()

        def visit_company( self, node ):
            if 'company' not in self.extracted:
                self.extracted['company'] = node.astext()

        def visit_industry( self, node ):
            if 'industry' not in self.extracted:
                self.extracted['industry'] = node.astext()

        def visit_proglang( self, node ):
            if 'proglang' not in self.extracted:
                self.extracted['proglang'] = node.astext()

        def visit_date(self, node):
            tdate = node.astext()
            mo = re.match('(\d\d\d\d)-(\d\d)-(\d\d)', tdate)
            if mo:
                self.extracted['date'] = datetime.date(*map(int,mo.groups()))


class DoculateStorage(extract.SQLExtractorStorage):
    """
    Doculate storage.

    Note: this is not necessarily meant to store the actual doculate, but rather
    stuff extracted from the doculate.  You may to use the doculate from the
    uploaded sources storage to render the entire doculate as HTML, this is ok.

    Because we follow the value <=> document links in both directions, we need
    indices for quickly finding all entries for a specific document to refresh
    the set of values, and we need an index to find all documents with a
    specific value.  And we place a key constraint on the 'unid' column to
    insure an extractor failure does not leave the database in an inconsistent
    state.
    """
    sql_tables = { 'doculate': '''

        CREATE TABLE doculate
        (
           unid       TEXT NOT NULL,
           title      TEXT,
           doctype    TEXT,
           uploaded   DATE DEFAULT CURRENT_DATE,
           date       DATE,
           discourse  TEXT,
           locale     TEXT,
           platform   TEXT,
           company    TEXT,
           industry   TEXT,
           proglang   TEXT

           -- CONSTRAINT doculate_unid_fk
           --            FOREIGN KEY(unid)
           --            REFERENCES __sources__(unid)
           --            ON DELETE CASCADE
        );
        CREATE INDEX doculate_unid_idx ON doculate(unid);
        CREATE INDEX doculate_doctype_idx ON doculate(doctype);
        CREATE INDEX doculate_platform_idx ON doculate(platform);
        CREATE INDEX doculate_proglang_idx ON doculate(proglang);

        '''
        }

    def store( self, unid, data ):

        # Extract the set of authors and insert the new ones into the database.

        data['unid'] = unid

        cols = ['unid', 'title', 'doctype', 'date', 'discourse', 'locale', 'platform', 'company', 'industry', 'proglang']
        for cname in cols:
            data.setdefault(cname, None)

        a = ', '.join(['%%(%s)s' % x for x in cols])
        query = """
          INSERT INTO doculate (%s) VALUES (%s)
          """ % (', '.join(cols), a)

        cursor = self.connection.cursor()
        cursor.execute(query, data)
        self.connection.commit()

