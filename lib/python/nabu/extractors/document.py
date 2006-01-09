#!/usr/bin/env python
#
# Copyright (C) 2005  Martin Blais <blais@furius.ca>
# This file is distributed under the terms of the GNU GPL license.
# For more information: http://furius.ca/nabu.
#
# $Id$
#

"""
Extract document tree and bibliographic fields.
"""

# stdlib imports
import sys, re, datetime
import pickle
##import cPickle as pickle

# docutils imports
from docutils import nodes

# nabu imports
from nabu import extract


#-------------------------------------------------------------------------------
#
class Extractor(extract.Extractor):
    """
    Transform that extracts some basic information about the document as a
    whole.  For example, it extracts the title and some bibliographic fields.
    """
    default_priority = 900

    biblifields = ['category', 'serie', 'location', 'disclosure']

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
                self.extracted[self.catchname] = node.astext().lower()
                self.catchname = None

        def visit_title( self, node ):
            if 'title' not in self.extracted:
                self.extracted['title'] = node.astext()

        def visit_author( self, node ):
            if 'author' not in self.extracted:
                self.extracted['author'] = node.astext()

        def visit_date(self, node):
            tdate = node.astext()
            mo = re.match('(\d\d\d\d)-(\d\d)-(\d\d)', tdate)
            if mo:
                self.extracted['date'] = datetime.date(*map(int,mo.groups()))


class Storage(extract.SQLExtractorStorage):
    """
    Document storage.

    Note: this is not necessarily meant to store the actual document, but rather
    stuff extracted from the document.  You may to use the document from the
    uploaded sources storage to render the entire document as HTML, this is ok.
    """

    sql_tables = { 'document': '''

        CREATE TABLE document
        (
           unid TEXT NOT NULL,
           title TEXT,
           author TEXT,
           date DATE,
           abstract TEXT,
           category TEXT,
           serie TEXT,
           location TEXT,

           -- Disclosure is
           --  0: public
           --  1: restricted
           --  2: private
           disclosure INT DEFAULT 2
        )

        '''
        }

    # Mapping strings to disclosure levels.
    discmap = {None: 2, # default
               'public': 0,
               'restricted': 1,
               'private': 2}

    def store( self, unid, data ):
        data['unid'] = unid
        
        cols = ['unid', 'title', 'author', 'date',
                'abstract', 'category', 'serie', 'location',
                'disclosure']
        for cname in cols:
            data.setdefault(cname, None)
        
        disc = data.get('disclosure').split()[0]
        data['disclosure'] = self.discmap[disc]

        a = ', '.join(['%%(%s)s' % x for x in cols])
        query = """
          INSERT INTO document (%s) VALUES (%s)
          """ % (', '.join(cols), a)

        cursor = self.connection.cursor()
        cursor.execute(query, data)
        self.connection.commit()

