#!/usr/bin/env python
#
# $Source$
# $Id$
#

"""
Process global information about the upload as a document.
"""

import sys
import xmlrpclib
import pickle
import re
import datetime
from pprint import pprint, pformat

import docutils.readers.standalone
import docutils.writers.null
from docutils.transforms import Transform
import docutils.io
import docutils.core
from docutils import nodes

class DocumentTransform(Transform):
    """
    Transform that extracts some basic information about the document as a
    whole.  For example, it extracts the title and some bibliographic fields.
    """
    default_priority = 900

    table = 'Document'

    def apply( self ):
        v = self.Visitor(self.document)
        self.document.walk(v)
        self.extracted = v.extracted

    class Visitor(nodes.SparseNodeVisitor):

        def __init__( self, *args, **kwds ):
            nodes.SparseNodeVisitor.__init__(self, *args, **kwds)
            self.extracted = {}
            
        def visit_title( self, node ):
            if 'title' not in self.extracted:
                self.extracted['title'] = node.astext()

        def visit_date(self, node):
            tdate = node.astext()
            mo = re.match('(\d\d\d\d)-(\d\d)-(\d\d)', tdate)
            if mo:
                self.extracted['date'] = datetime.date(*map(int,mo.groups()))


import nabu.entryforms
nabu.entryforms.registry['document'] = DocumentTransform
