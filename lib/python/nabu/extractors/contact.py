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
import sys, re, types
from pprint import pprint, pformat ## FIXME remove

# docutils imports
from docutils import nodes

# nabu imports
from nabu import extract
## from nabu.extractors.flvis import FieldListVisitor


## FIXME: you need to support
##
##   Jan 28, 29, 30, 31, 1, 2, 3, 4
##      * Crossing the month boundary in a single set should be easy
##
##   Jan 28 -- Feb 4
##      * This would be nice too...
##

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

    re_short = re.compile('([a-z])(?: ([^ \t]+))?$')

    def store(self, *data):
        self.storage.store(self.unid, *data)

    def apply(self, **kwargs):
        self.unid, self.storage = kwargs['unid'], kwargs['storage']

        v = FieldListVisitor(self, self.document)
        self.document.walkabout(v)

#-------------------------------------------------------------------------------
#
_translations = {
    'n': 'name',
    'a': 'address',
    'e': 'email',
    'w': 'web',
    'c': 'comment',
    'comment': 'comments',
    'p': 'phone'
    }

class FieldListVisitor(nodes.SparseNodeVisitor):
    """
    A visitor that accumulates field lists, and that returns dictionaries for
    each of the lists.  If there are multiple equal field names, a list of the
    values is associated to that name. The field names are taken to be
    case-insensitive.
    """

    def __init__(self, extractor, *args, **kwds):
        nodes.SparseNodeVisitor.__init__(self, *args, **kwds)
        self.extractor = extractor
        self.fields = None

    def visit_field_list(self, node):
        # Setup accumulator.
        self.fields = []

    def visit_field_name(self, node):
        if self.fields is not None:
            self.field_name = node.astext()

    def visit_field_body(self, node):
        if self.fields is not None:
            self.fields.append( (self.field_name, node.astext()) )
            self.field_name = None

    def depart_field_list(self, node):
        self.process(self.fields)
        self.fields = None

    def process(self, fields):
        """
        Process a field list, attempting to find if it's a contact info.
        """
        tlist = []
        tcount = {}
        cname = None
        if fields is None:
            return
        
        for name, value in fields:
            names = name.lower().split()
            typ = _translations.get(names[0], names[0])

            if typ == 'name':
                # Only grab the first name in a single entry
                if cname is None:
                    cname = value 
                continue
            
            subtyp = ' '.join(names[1:])
            tcount.setdefault(typ, 0)
            tcount[typ] += 1

            tlist.append( (typ, subtyp, value) )

        if cname is None or not ('email' in tcount or
                                 'phone' in tcount or
                                 'address' in tcount):
            return # Not a contact info.
            
        self.extractor.store(cname, tlist)


#-------------------------------------------------------------------------------
#
class Storage(extract.SQLExtractorStorage):
    """
    Contact storage.
    """
    sql_tables = {
        'contact': '''
          CREATE TABLE contact
          (
             id SERIAL PRIMARY KEY,
             unid TEXT NOT NULL,
             name TEXT
          )
        '''}

    sql_tables_other = {
        'contact_field': '''
          CREATE TABLE contact_field
          (
             contact_id TEXT REFERENCES contact (id) ON DELETE CASCADE,
             type TEXT,
             subtype TEXT,
             value TEXT
          )
          ''',
        }

    def store(self, unid, name, tfields):
        """
        'unid' -> str: the unique id
        'name' -> unicode: person or org name
        'tfields' -> list of (type, subtype, value) tuples: list of other entries.
        """
        cursor = self.connection.cursor()
        cols = ('unid', 'name')
        cursor.execute("""
          INSERT INTO contact (%s) VALUES (%%s, %%s);
          SELECT currval('contact_id_seq');
          """ % ', '.join(cols), (unid, name))
        contactid = cursor.fetchone()[0]

        for typ, subtyp, value in tfields:
            cursor.execute("""
              INSERT INTO contact_field (contact_id, type, subtype, value)
                VALUES (%s, %s, %s, %s)
              """, (contactid, typ, subtyp, value))

        self.connection.commit()

