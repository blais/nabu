#!/usr/bin/env python
#
# $Source$
# $Id$
#

"""
Server-side handlers for requests.
"""

# stdlib imports
import sys
import md5
import datetime
from pprint import pprint, pformat

# other imports
from sqlobject import *

# nabu imports
from nabu.process import process_source

class History(SQLObject):
    """
    History of uploads.
    This is used to figure out what needs to be refreshed.
    """
    unid = StringCol(alternateID=1, length=36, notNull=1)
    filename = StringCol(length=256)
    digest = StringCol(length=32, notNull=1)
    time = DateTimeCol()

class Document(SQLObject):
    """
    Stored document.
    """
    unid = StringCol(alternateID=1, length=36, notNull=1)
    contents = BLOBCol() # pickled document


sqlobject_classes = [History, Document]


def init_connection( connection ):
    """
    Initializes the connection for the SQLObject classes.
    """
    # Note: the following connection sharing makes it impossible to use
    # threads.
    for cls in sqlobject_classes:
        cls._connection = connection


class ServerHandler:
    """
    Nabu protocol server handler.
    """
    def __init__( self, connection ):
        self.connection = connection

        init_connection(connection)

        "A DBAPI-2.0 open connection to a database."
        self.__checktables()

    def __checktables( self ):
        """
        Checks that the database tables exist and if they don't, creates them.
        """
        for cls in sqlobject_classes:
            cls.createTable(ifNotExists=True)

    def gethistory( self, idlist=None ):
        """
        Returns the digests for the list of requested ids.
        """
        ret = {}

        if idlist is None:
            for r in History.select():
                ret[r.unid] = r.digest
        else:
            for unid in idlist:
                r = History.select(History.q.unid == unid)
                if r.count() > 0:
                    rr = r[0]
                    ret[rr.unid] = rr.digest

        return ret

    def process_file( self, unid, filename, contents_bin ):
        """
        Process a single file.
        We assume that the file comes wrapped in a Binary, encoded in UTF-8.
        """
        print >> sys.stderr, 'Processing %s' % unid

        # convert XML-RPC Binary into string
        contents_utf8 = contents_bin.data

        # compute digest of contents
        m = md5.new(contents_utf8)
        digest = m.hexdigest()

        # process and store contents as a Unicode string
        contents = contents_utf8.decode('UTF-8')
        del contents_utf8

        # remove all previous objects that were previously extracted from this
        # document
        for cls in sqlobject_classes:
            sr = cls.select(cls.q.unid == unid)
            for r in sr:
                cls.delete(id=r.id)

        # process the new file
        entries = process_source(contents)

        try:
            del entries['History']
        except KeyError:
            pass

        for cls in sqlobject_classes:
            try:
                entry = entries[cls.__name__]
            except KeyError:
                continue

            entry['unid'] = unid

            params = dict( (k._name, entry[k._name]) for k in cls._columns )
            newinst = cls(**params)

        # finally, create a new history for the document
        newhist = History(unid=unid, filename=filename, digest=digest,
                          time=datetime.datetime.now())

        return 0

