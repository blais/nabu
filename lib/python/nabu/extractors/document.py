#!/usr/bin/env python
#
# $Id$
#

"""
Process global information about the upload as a document.
"""

# stdlib imports
import re, datetime

# docutils imports
from docutils import nodes

# other imports
from sqlobject import *

# nabu imports
from nabu import extract


class DocumentExtractor(extract.Extractor):
    """
    Transform that extracts some basic information about the document as a
    whole.  For example, it extracts the title and some bibliographic fields.
    """
    default_priority = 900

    biblifields = ['category', 'serie', 'location']
    
    def apply( self, unid=None, storage=None ):
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

        def visit_author( self, node ):
            if 'author' not in self.extracted:
                self.extracted['author'] = node.astext()

        def visit_date(self, node):
            tdate = node.astext()
            mo = re.match('(\d\d\d\d)-(\d\d)-(\d\d)', tdate)
            if mo:
                self.extracted['date'] = datetime.date(*map(int,mo.groups()))


class Document(SQLObject):
    """
    Storage for document information.
    """
    unid = StringCol(notNull=1)

    title = UnicodeCol()
    author = UnicodeCol()
    date = DateCol()
    abstract = UnicodeCol(notNull=0)
    category = UnicodeCol(notNull=0)
    serie = UnicodeCol(notNull=0)
    location = UnicodeCol(notNull=0)

class DocumentStorage(extract.SQLObjectExtractorStorage):
    """
    Document storage.

    Note: this is not necessarily meant to store the actual document, but rather
    stuff extracted from the document.  You may to use the document from the
    uploaded sources storage to render the entire document as HTML, this is ok.
    """

    sqlobject_classes = [Document]

    def store( self, unid, data ):
        data['unid'] = unid
        for n in ['title', 'author', 'date', 'abstract',
                  'category', 'serie', 'location']:
            data.setdefault(n, '')
        Document(**data)

