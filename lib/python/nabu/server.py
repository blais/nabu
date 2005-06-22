#!/usr/bin/env python
#
# $Source$
# $Id$
#

"""
Server-side handlers for requests.
"""

# stdlib imports
import md5
import datetime
import threading
import StringIO
import cPickle as pickle
from pprint import pprint, pformat

# docutils imports
import docutils.core

# other imports
from sqlobject import *

# nabu imports
from nabu.process import extract

class Source(SQLObject):
    """
    Source and history of uploads.
    This is used to figure out what needs to be refreshed.

    We also keep a copy of the original document tree, before our extraction was
    run, so that we can reprocess the extraction on the server without having to
    reparse nor upload the documents.
    """
    class sqlmeta:
        table = '__sources__'

    unid = StringCol(alternateID=1, length=36, notNull=1)
    filename = StringCol(length=256)
    digest = StringCol(length=32, notNull=1)
    username = StringCol(length=32)
    time = DateTimeCol()
    source = UnicodeCol()
    doctree = BLOBCol() # pickled doctree, before custom transforms.
    errors = UnicodeCol()


## FIXME move this into being simply the result of one of the transforms
class Document(SQLObject):
    """
    Stored document.
    """
    unid = StringCol(alternateID=1, length=36, notNull=1)
    contents = BLOBCol() # pickled doctree, after custom transforms.




sqlobject_classes = [Source, Document]

def init_connection( connection ):
    """
    Initializes the connection for the SQLObject classes.
    """
    # Note: the following connection sharing makes it impossible to use
    # threads.
    for cls in sqlobject_classes:
        cls._connection = connection

    # Checks that the database tables exist and if they don't, creates them.
    for cls in sqlobject_classes:
        cls.createTable(ifNotExists=True)

class ServerHandler:
    """
    Protocol server handler.
    """
    username = 'guest'
    
    def __init__( self, connection, username=None ):
        self.connection = connection
        if username:
            self.username = username
        
        init_connection(connection)

    def getallids( self ):
## FIXME for this user only
        return [r.unid for r in Source.select()]

    def gethistory( self, idlist=None ):
        """
        Returns the digests for the list of requested ids.
        """
        ret = {}

        if idlist is None:
            for r in Source.select():
                ret[r.unid] = r.digest
        else:
            for unid in idlist:
                r = Source.select(Source.q.unid == unid)
                if r.count() > 0:
                    rr = r[0]
                    ret[rr.unid] = rr.digest

        return ret

    def clearuser( self ):
        """
        Clear the entire database.
        This is requested from the client interface.
        """
        # drop the tables.  We're bold.
        for cls in sqlobject_classes:
            cls.dropTable(ifExists=True, cascade=True)
## FIXME implement clearing for user only
        return 0

    def clearids( self, idlist ):
        """
        Clear all entries for a set of ids.
        """
        for unid in idlist:
            self.__clear_id(unid)

## FIXME implement clearing of specific ids only

##         # drop the tables.  We're bold.
##         for cls in sqlobject_classes:
##             cls.dropTable(ifExists=True, cascade=True)
        return 0

    def __clear_id( self, unid ):
        """
        Removes all entries associated with a specific id.
        """
        for cls in sqlobject_classes:
            for r in cls.select(cls.q.unid == unid):
                cls.delete(r.id)

        
    def process_source( self, unid, filename, contents_bin ):
        """
        Process a single file.
        We assume that the file comes wrapped in a Binary, encoded in UTF-8.
        """
        # convert XML-RPC Binary into string
        contents_utf8 = contents_bin.data
        
        # compute digest of contents
        m = md5.new(contents_utf8)
        digest = m.hexdigest()

        # process and store contents as a Unicode string
        errstream = StringIO.StringIO()
        doctree, parts = docutils.core.publish_doctree(
            source=contents_utf8, source_path=filename,
            settings_overrides={
            'input_encoding': 'UTF-8',
            'warning_stream': errstream,
            'halt_level': 100, # never halt
            },
            )
        errortext = errstream.getvalue()

        self.__process(unid, filename, digest,
                       contents_utf8, doctree, None, errortext)

        return errortext or ''

    def process_doctree( self, unid, filename, digest,
                         contents_bin, doctree_bin, errortext ):
        """
        Process a single file.  We assume that the file and document tree comes
        wrapped in a Binary, encoded in UTF-8.
        """
        contents_utf8 = contents_bin.data

        docpickled = doctree_bin.data
        doctree = pickle.loads(docpickled)
## FIXME return error to the client if there is an exception in unpickling here.

        self.__process(unid, filename, digest,
                       contents_utf8, doctree, docpickled, errortext)
        return 0
    
    def __process( self, unid, filename, digest, contents_utf8,
                   doctree, docpickled, errortext ):
        """
        Process the given tree, extracting the information entries from it and
        replacing the existing entries with the newly extracted ones.

        :Parameters:
          ...
          - `docpickled`: an optimization because we might already have a
            pickled version of the tree.  If left to None we create our own.
        """

        # remove all previous objects that were previously extracted from this
        # document
        for cls in sqlobject_classes:
            sr = cls.select(cls.q.unid == unid)
            for r in sr:
                cls.delete(id=r.id)

        # create a new history for the document
        if docpickled is None:
            docpickled = pickle.dumps(doctree)

        newhist = Source(unid=unid,
                         filename=filename.replace('\\', '/'),
                         digest=digest,
                         username=self.username,
                         time=datetime.datetime.now(),
                         source=contents_utf8.decode('utf-8'),
                         doctree=docpickled,
                         errors=errortext.decode('utf-8'))

##         # process the custom transforms.
##         entries = process_source(contents)
## FIXME how do I detect errors here?



## FIXME this should be in the "whole document" transform
        entries = {
            'Document': {'contents': pickle.dumps(doctree)}
            }

## FIXME entries should be the result of running all the transforms
        assert 'Source' not in entries

## FIXME create tables dynamically depending on what entries are returned


        # For each available schema
        for cls in sqlobject_classes:
            try:
                entry = entries[cls.__name__]
            except KeyError:
                continue

            entry['unid'] = unid

            params = dict( (k._name, entry[k._name]) for k in cls._columns )
            newinst = cls(**params)

        return 0
    
    def dump( self ):
        """
        Returns information about all the documents stored for a specific user.
        """
        allsources = []
        attrs = ('unid', 'filename', 'username',)
        for s in Source.select():
            ret = {}
            for a in attrs:
                ret[a] = getattr(s, a)
            # datetime objects cannot be marshalled
            ret['time'] = s.time.isoformat()
            ret['errors'] = bool(s.errors)
            allsources.append(ret)
        return allsources

    def geterrors( self ):
        """
        Return a list of mappings with the error texts.
        """
        errors = []
        fields = ['unid', 'filename', 'errors']
        for s in Source.select(Source.q.errors != ''):
            errors.append(dict((a, getattr(s, a)) for a in fields))
        return errors

