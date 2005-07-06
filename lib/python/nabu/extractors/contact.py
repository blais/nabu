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
import re, types

# docutils imports
from docutils import nodes

# other imports
from sqlobject import *

# nabu imports
from nabu import extract
from nabu.extractors.flvis import FieldListVisitor


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

    def store( self, flist ):
        for k, v in flist.iteritems():
            if isinstance(v, types.ListType):
                flist[k] = ', '.join([x.astext() for x in v])
            else:
                flist[k] = v.astext()

        # it's a contact info! store it.
        self.storage.store(self.unid, flist)

    def apply( self, **kwargs ):
        self.unid, self.storage = kwargs['unid'], kwargs['storage']

        v = FieldListVisitor(self.document)
        v.initialize()
        self.document.walk(v)
        v.finalize()

        for flist in v.getfieldlists():
            # translate short names
            for _from, _to in (('n', 'name'),
                               ('e', 'email'),
                               ('p', 'phone')):
                try:
                    flist[_to] = flist[_from]
                except KeyError:
                    pass
                
            if 'name' in flist and \
               ('email' in flist or 'phone' in flist or 'address' in flist):
                self.store(flist)


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

