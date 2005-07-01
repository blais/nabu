#!/usr/bin/env python
#
# $Id$
#

"""
Process global information about the upload as a event.
"""

# stdlib imports
import re, datetime

# docutils imports
from docutils import nodes

# other imports
from sqlobject import *

# nabu imports
from nabu import extract


class EventExtractor(extract.Extractor):
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

    evre = re.compile('event')
    evcontentsre = re.compile('\s*(\d\d\d\d)-(\d\d)-(\d\d)(.*)', re.DOTALL)
    
    def apply( self, **kwargs ):
        unid, storage = kwargs['unid'], kwargs['storage']

        v = self.Visitor(self.document, unid, storage)
        self.document.walk(v)

        from pprint import pformat
        self.document.reporter.info(
            'Event extractor: %s' % pformat(v.extracted))

    class Visitor(nodes.SparseNodeVisitor):

        def __init__( self, document, unid, storage ):
            nodes.SparseNodeVisitor.__init__(self, document)
            self.unid = unid
            self.storage = storage
            self.extracted = {}
            
        def visit_field_list( self, node ):
            if len(node.children) != 1:
                return
            if not EventExtractor.evre.match(node.children[0].astext().lower()):
                return
                
            text = node.children[0].children[1].astext()

            mo = EventExtractor.evcontentsre.match(text)
            if mo:
                dt = datetime.date(*map(int, mo.group(1,2,3)))
                desc = mo.group(4)
            else:
                dt = datetime.date.today()
                desc = text
            
            self.storage.store(self.unid, dt, desc)

class Event(SQLObject):
    """
    Storage for event information.
    """
    unid = StringCol(notNull=1)

    date = DateCol()
    description = UnicodeCol(notNull=0)

class EventStorage(extract.SQLObjectExtractorStorage):
    """
    Event storage.
    """
    sqlobject_classes = [Event]

    def store( self, unid, dt, description ):
        Event(unid=unid,
              date=dt,
              description=description)
