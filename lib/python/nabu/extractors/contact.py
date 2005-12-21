#!/usr/bin/env python
#
# Copyright (C) 2005  Martin Blais <blais@furius.ca>
# This file is distributed under the terms of the GNU GPL license.
# For more information: http://furius.ca/nabu.
#
# $Id$
#

"""
Extract contact info.
"""

# stdlib imports
import re, types

# docutils imports
from docutils import nodes

# nabu imports
from nabu import extract
from nabu.extractors.flvis import FieldListVisitor


class Extractor(extract.Extractor):
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

    The empty 'Contact' field is not absolutely necessary, we perform some
    simple heuristics to find out if a field list is a contact info.  The field
    names are case insensitive.
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

                from pprint import pprint, pformat ## FIXME remove
                import sys
                print >> sys.stderr, pformat(flist['name'])

                self.store(flist)


class Storage(extract.SQLExtractorStorage):
    """
    Contact storage.
    """
    sql_tables = { 'contact': '''

        CREATE TABLE contact
        (
           unid TEXT NOT NULL,
           name TEXT,
           email TEXT,
           address TEXT,
           bday TEXT
        )

        '''
        }

    def store( self, unid, *args ):
        data, = args
        
        cols = ('unid', 'name', 'email', 'address', 'bday')
        values = [unid]
        for n in cols[1:]:
            values.append( data.get(n, '') )
            
        cursor = self.connection.cursor()
        cursor.execute("""
          INSERT INTO contact (%s) VALUES (%%s, %%s, %%s, %%s, %%s)
          """ % ', '.join(cols), values)

        self.connection.commit()
        
