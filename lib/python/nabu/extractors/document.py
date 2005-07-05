#!/usr/bin/env python
#
# Copyright (C) 2005  Martin Blais <blais@furius.ca>
# This file is distributed under the terms of the GNU GPL license.
# For more information: http://furius.ca/nabu.
#
# $Id$
#

"""
Process global information about the upload as a document.
"""

# stdlib imports
import re, datetime, copy
import pickle
##import cPickle as pickle

# docutils imports
from docutils import nodes

# other imports
from sqlobject import *

# nabu imports
from nabu import extract

#-------------------------------------------------------------------------------
#
class DoctreeExtractor(extract.Extractor):
    """
    Document tree storage. This is used to store the document tree at the point
    of a transform.  Typically, we would not necessarily want the document tree
    that is stored in the sources upload table to be reused, we would rather
    store it explicitly for presentation and leave the Nabu mechanism alone.

    Note that this results in more database storage.  I suppose that we could
    forego storing the source and/or document tree in the sources upload
    storage.
    """

    default_priority = 999

    def apply( self, unid=None, storage=None, pickle_receiver=None ):
        self.unid = unid
        self.storage = storage
        # Store the document at this point.
        pickled = self.storage.store(self.unid, self.document)
        if pickled:
            pickle_receiver.append(pickled)


class Doctree(SQLObject):
    """
    Schema for document tree.
    """
    unid = StringCol(alternateID=1, notNull=1)

    doctree = BLOBCol() # pickled doctree.

class DoctreeStorage(extract.SQLObjectExtractorStorage):
    """
    Document tree storage.
    """
    sqlobject_classes = [Doctree]

    def store( self, unid, doctree ):

        # Temporarily remove the reporter and transformer, just for pickling.
        saved_reporter = doctree.reporter
        saved_transformer = doctree.transformer
        try:
            doctree.reporter = None
            doctree.transformer = None
            doctree_pickled = pickle.dumps(doctree)
        finally:
            doctree.reporter = saved_reporter
            doctree.transformer = saved_transformer

        Doctree(unid=unid, doctree=doctree_pickled)

        return doctree_pickled

#-------------------------------------------------------------------------------
#
class DocumentExtractor(extract.Extractor):
    """
    Transform that extracts some basic information about the document as a
    whole.  For example, it extracts the title and some bibliographic fields.
    """
    default_priority = 900

    biblifields = ['category', 'serie', 'location']

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
    unid = StringCol(alternateID=1, notNull=1)

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
