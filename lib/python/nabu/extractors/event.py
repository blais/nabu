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
import sys, re, datetime, itertools
from pprint import pformat

# docutils imports
from docutils import nodes

# nabu imports
from nabu import extract


#-------------------------------------------------------------------------------
#
class Extractor(extract.Extractor):
    """
    Extract events happening at date/time specs + description, which are input
    as definition lists, like this::

        2006-01-05
            - Event description with full ISO date.

        01-05
            - Event description with partial ISO date.

        01/05
            - Alternate format.

        jan 05
            - Event description with month + day.

        wed
            - Event description with next weekday found (at the time of upload).

        wed 05
            - Event description with next weekday that has the day number (be
              careful, this could be dangerous if you make a mistake, we search
              for the next weekday that has the appropriate date (at the time of
              upload)).

        wed jan 05
            - Over-specified date/time spec that is useful for reading in your
              input file.  We verify that it matches the specified date.

        jan 05 wed
            - Other acceptable over-specified date/time spec.

    All the date/time specs can be followed by time or time-interval specs if
    desired::

        2006-01-05 20h00
            - With date and time.

        2006-01-05 20h00-21h00
            - With date and time interval.

        2006-01-05 20h
            - Abbreviated time.

    Remember not to leave a blank line between the date/time spec and the event
    definition, because that does not create a docutils term/definition
    structure.

    Also note that we consider list items under a date/time spec as separate
    events with the same date/time spec.
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

            self.desc = None

        def visit_definition_list_item( self, node ):
            # Initialize
            self.dates, self.desc = [], None

        def visit_term( self, node ):
            if len(node.children) != 1:
                return
            text = node.children[0].astext().lower()

            try:
                self.dates = parse_dtspec(text)
            except KeyError:
                self.dates = []

        def visit_definition( self, node ):
            self.desc = []

        def visit_list_item( self, node ):
            if self.desc is not None:
                self.desc.append(node.astext())
            raise nodes.SkipChildren

        def depart_definition_list_item( self, node ):
            for d, t1, t2 in self.dates:
                for child in self.desc:
                    self.storage.store(self.unid, d, t1, t2, child)



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
           time1 TIME,
           time2 TIME,
           description TEXT
        )

        '''
        }

    def store( self, unid, date, time1, time2, description ):
        cursor = self.connection.cursor()
        cursor.execute("""
          INSERT INTO event (unid, date, time1, time2, description)
            VALUES (%s, %s, %s, %s, %s)
          """, (unid, date, time1, time2, description))
        self.connection.commit()



#-------------------------------------------------------------------------------
#
wkdays = {'mon': 0, 'tue': 1, 'wed': 2, 'thu': 3, 'fri': 4, 'sat': 5, 'sun': 6,
          'lun': 0, 'mar': 1, 'mer': 2, 'jeu': 3, 'ven': 4, 'sam': 5, 'dim': 6}

months = {'jan': 1,
          'feb': 2, 'fev': 2,
          'mar': 3,
          'apr': 4, 'avr': 4,
          'may': 5, 'may': 5,
          'jun': 6,
          'jul': 7, 'jui': 7,
          'aug': 8, 'aou': 8,
          'sep': 9,
          'oct': 10,
          'nov': 11,
          'dec': 12}

timespec = '(\d\d)h(\d\d)?'
hlre = re.compile('(.*)\s+(?:%s)(?:\s*--?\s*%s)?' % (timespec, timespec))
## print hlre.match(' 20h').groups()
## print hlre.match(' 20h12').groups()
## print hlre.match(' 20h-21h').groups()
## print hlre.match(' 20h12-21h').groups()
## print hlre.match(' 20h12-21h14').groups()
## print hlre.match(' 20h-21h14').groups()

alldays = '(%s)' % '|'.join(wkdays.iterkeys())
all3 = '(%s)' % '|'.join(itertools.chain(wkdays.iterkeys(), months.iterkeys()))

manydays = '((?:\d\d?|\s*,\s*)*)'

telist = ((0, '(?:(\d\d\d\d)-)?(\d\d?)[-/]%s$' % manydays),
          (1, '%s$' % alldays),
          (2, '%s %s$' % (all3, manydays)),
          (3, '%s\s+(\d+)\s+%s$' % (all3, all3)),
          (4, '%s\s+%s\s+(\d+)$' % (all3, all3)),
          )
tere = [(no, re.compile(x, re.I)) for no, x in telist]

evre_dotw = re.compile('([a-z][a-z][a-z])'
                       '(?:\s+(\d\dh)(\d\d)?)?$')


def parse_dtspec( s ):
    """
    Parse a date/time spec and return a list of (date, time1, time2) tuples.
    """

    #
    # Parse times, if present.
    #
    t1, t2 = None, None
    mo = hlre.match(s)
    if mo:
        s = mo.group(1)
        h1, m1, h2, m2 = [(x and int(x) or None) for x in mo.group(2, 3, 4, 5)]

        assert h1 is not None
        if m1 is not None:
            t1 = datetime.time(h1, m1)
        else:
            t1 = datetime.time(h1)

        if h2 is not None:
            if m2 is not None:
                t2 = datetime.time(h2, m2)
            else:
                t2 = datetime.time(h2)
    s = s.strip()

    #
    # Parse dates.
    #
    case = None
    for x, tre in tere:
        mo = tre.match(s)
        if mo:
            case = x
            break

    today = datetime.date.today()

    dates = []
    if case == 0:
        #print case, mo.groups()

        # month
        month = int(mo.group(2))

        # year
        year = mo.group(1)
        if year is None:
            year = today.year
            if month < today.month:
                year += 1
        else:
            year = int(year)

        # days
        days = [int(x.strip()) for x in mo.group(3).split(',')]

        dates = [datetime.date(year, month, x) for x in days]

    elif case == 1:
        #print case, mo.groups()

        # Our match is necessarity a day.
        wkday = wkdays[mo.group(1)]
        date = today + datetime.timedelta(
            days=(wkday + 7 - today.weekday()) % 7)

        dates = [date]

    elif case == 2:
        #print case, mo.groups()

        # Our first match is either a day or month
        dm, days = mo.groups()
        days = [int(x.strip()) for x in mo.group(2).split(',')]

        if dm in wkdays:
            if len(days) > 1:
                raise RuntimeError(
                    "Error: cannot have multiple days matching dates.")
            day = days[0]

            # Search for the next matching weekday matching the given date

            # Our match is necessarity a day.
            wkday = wkdays[dm]
            date = today + datetime.timedelta(
                days=(wkday + 7 - today.weekday()) % 7)
            aweek = datetime.timedelta(days=7)

            while date.day != day:
                date += aweek

            dates = [date]
        else:
            month = months[dm]

            # year
            year = today.year
            if month < today.month:
                year += 1

            dates = [datetime.date(year, month, x) for x in days]

    elif case in (3, 4):
        #print case, mo.groups()

        if case == 3:
            th1, day, th2 = mo.groups()
        elif case == 4:
            th1, th2, day = mo.groups()

        day = int(day)

        if th1 in wkdays:
            assert th2 in months
            wkday, month = th1, th2
        else:
            assert th1 in months
            assert th2 in wkdays
            wkday, month = th2, th1

        wkday, month = wkdays[wkday], months[month]

        # year
        year = today.year
        if month < today.month:
            year += 1

        date = datetime.date(year, month, day)
        assert date.weekday() == wkday

        dates = [date]
    else:
        pass

    return [(x, t1, t2) for x in dates]


#-------------------------------------------------------------------------------
#
def test():
    """
    Test all date/time spec input formats.
    """

    date = datetime.date(2006, 01, 4)
    oneday = datetime.timedelta(days=1)
    t1 = datetime.time(20)
    t2 = datetime.time(21, 12)
    tests = (('2006-01-04', [(date, None, None)]),
             ('01-4', [(date, None, None)]),
             ('01/4', [(date, None, None)]),
             ('jan 4', [(date, None, None)]),
             ('wed', [(date, None, None)]),
             ('wed 4', [(date, None, None)]),
             ('wed 25', [(datetime.date(2006, 01, 25), None, None)]),
             ('wed jan 4', [(date, None, None)]),
             ('jan 4 wed', [(date, None, None)]),
             ('2006-01-4 20h00 ', [(date, t1, None)]),
             ('2006-01-4 20h00-21h12', [(date, t1, t2)]),
             ('2006-01-4 20h', [(date, t1, None)]),

             # multiple days
             ('2006-01-4, 5 ', [(date, None, None),
                                 (date + oneday, None, None)]),
             ('jan 4, 5 ', [(date, None, None),
                             (date + oneday, None, None)]),
             ('01-4, 5 ', [(date, None, None),
                            (date + oneday, None, None)]),
             ('01/4, 5 ', [(date, None, None),
                            (date + oneday, None, None)]),

             ('2006-01-4, 5, 6 ', [(date, None, None),
                                     (date + oneday, None, None),
                                     (date + oneday + oneday, None, None)]),

             # multiple days and times
             ('2006-01-4, 5 21h12', [(date, t2, None),
                                      (date + oneday, t2, None)]),
             )

    for dt in tests:
        print
        print dt[0]
        res = parse_dtspec(dt[0])
        print 'a', res
        print 'b', dt[1]
        assert res == dt[1]


if __name__ == '__main__':
    test()

