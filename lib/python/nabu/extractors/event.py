#!/usr/bin/env python
#
# Copyright (C) 2005  Martin Blais <blais@furius.ca>
# This file is distributed under the terms of the GNU GPL license.
# For more information: http://furius.ca/nabu.
#
# $Id$
#

"""
Extract calendar events.
"""

# stdlib imports
import sys, re, datetime
from pprint import pformat

# docutils imports
from docutils import nodes

# nabu imports
from nabu import extract


#-------------------------------------------------------------------------------
#
class Extractor(extract.Extractor):
    """
    Extract a field list that has a single field, with a key of Event.
    If the first text in the value is a parseable date, we enter that as the
    date of the event.
    e.g.::

      :Event: 2005-06-29
        Some description of the event here, in any format, as long
        as it's in the value of the field.
    
    """
    default_priority = 900
    
    def apply( self, **kwargs ):
        unid, storage = kwargs['unid'], kwargs['storage']

        v = self.Visitor(self.document, unid, storage)
        self.document.walkabout(v)

        self.document.reporter.info(
            'Event extractor: %s' % pformat(v.extracted))

    class Visitor(nodes.SparseNodeVisitor):

        def __init__( self, document, unid, storage ):
            nodes.SparseNodeVisitor.__init__(self, document)
            self.unid = unid
            self.storage = storage
            self.extracted = {}

        def visit_definition_list_item( self, node ):
            # Initialize
            self.dates, self.desc = [], None

        def visit_term( self, node ):
            if len(node.children) != 1:
                return

            datetext = node.children[0].astext().lower()
            mo = evre.match(datetext)
            if not mo:
                return

            self.dates = parse_date(mo)

        def visit_definition( self, node ):
            self.desc = []               

        def visit_list_item( self, node ):
            if self.desc is not None:
                self.desc.append(node.astext())
            raise nodes.SkipChildren

        def depart_definition_list_item( self, node ):
            for d, t in self.dates:
                for child in self.desc:
                    self.storage.store(self.unid, d, t, child)



#-------------------------------------------------------------------------------
#
evre = re.compile('(?:([a-z][a-z][a-z])\s+)?'
                  '(\d\d\d\d)-(\d\d)-((?:\d\d|\s*,\s*)*)'
                  '(?:\s+(\d\dh)(\d\d)?)?')

def parse_date( mo ):
    """
    Parse a date string, given the match object that corresponds to the re.
    """
    year, month = map(int, mo.group(2, 3))
    days = [int(x.strip()) for x in mo.group(4).split(',')]
    hour = mo.group(5) and int(mo.group(5)[:-1]) or None
    minutes = mo.group(6) and int(mo.group(6)) or None
    if hour:
        if len(days) > 1:
            print >> sys.stderr, 'Warning: multiple days and hours'
            # FIXME: we need a real warning system to return errors to the user.

    all = []
    for day in days:
        date = datetime.date(year, month, day)
        if minutes is not None:
            time = datetime.time(hour, minutes)
        elif hour is not None:
            time = datetime.time(hour)
        else:
            time = None

        all.append( (date, time) )

    return all


#-------------------------------------------------------------------------------
#
class Storage(extract.SQLExtractorStorage):
    """
    Event storage.
    """
    sql_tables = { 'event': '''

        CREATE TABLE event
        (
           id SERIAL PRIMARY KEY,
           unid TEXT NOT NULL,
           date DATE,
           time TIME,
           description TEXT
        )

        '''
        }

    def store( self, unid, date, time, description ):
        cursor = self.connection.cursor()
        cursor.execute("""
          INSERT INTO event (unid, date, time, description)
            VALUES (%s, %s, %s, %s)
          """, (unid, date, time, description))
        self.connection.commit()




#-------------------------------------------------------------------------------
#
def test():
    legal = ('fri 2005-12-30',
             'sat 2005-12-31',
             '2006-01-05',
             '2006-01-13, 14, 16',
             '2006-01-04 20h42',
             '2006-01-04 23h',
             '2006-01-05, 06, 09, 10',)
    for s in legal:
        mo = evre.match(s)
        assert mo
        print s, mo.groups()
        parse_date(mo)



if __name__ == '__main__':
    test()
