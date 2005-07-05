#!/usr/bin/env python
#
# Copyright (C) 2005  Martin Blais <blais@furius.ca>
# This file is distributed under the terms of the GNU GPL license.
# For more information: http://furius.ca/nabu.
#
# $Id$
#

"""
Process global information about the upload as a contact.
"""

# stdlib imports
import re

# docutils imports
from docutils import nodes

# other imports
from sqlobject import *

# nabu imports
from nabu import extract


class ContactExtractor(extract.Extractor):
    """
    Transform that looks at field lists, like this::

       :Contact:
       :n: Martin Blais
       :e: blais@furius.ca
       :a: 1 rue de la Montagne, Mongueuil, France

    or ::

       :Contact:
       :Name: Martin Blais
       :Email: blais@furius.ca
       :Address: 1 rue de la Montagne, Mongueuil, France

    The empty Contact field is not absolutely necessary, we perform some simple
    heuristics to find out if a field list is a contact info.  The field names
    are case insensitive.
    """

    default_priority = 900

    def apply( self, **kwargs ):
        self.unid, self.storage = kwargs['unid'], kwargs['storage']

        v = self.Visitor(self.document)
        v.x = self
        self.document.walk(v)

    class Visitor(nodes.SparseNodeVisitor):

        def __init__( self, *args, **kwds ):
            nodes.SparseNodeVisitor.__init__(self, *args, **kwds)
            self.extracted = {}

        def visit_field_list( self, node ):
            import sys; from pprint import pprint, pformat
            print >> sys.stderr,  pformat(node.astext())
##         self.storage.store(self.unid, v.extracted)
## FIXME todo


class Contact(SQLObject):
    """
    Storage for contact information.
    """
    unid = StringCol(notNull=1)

    name = UnicodeCol()
    email = UnicodeCol()
    address = UnicodeCol()
    bday = UnicodeCol()

class ContactStorage(extract.SQLObjectExtractorStorage):
    """
    Contact storage.
    """

    sqlobject_classes = [Contact]

    def store( self, unid, *args ):
        data, = args
        Contact(unid=unid,
                name=data.get('name', ''),
                email=data.get('email'),
                address=data.get('address', ''),
                bday=data.get('bday', ''))

