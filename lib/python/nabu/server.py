#!/usr/bin/env python
#
# $Id$
#

"""
Server-side handlers for requests.
"""

# stdlib imports
import sys
import xmlrpclib
import md5
import datetime
import threading
import StringIO
import cPickle as pickle
from pprint import pprint, pformat

# docutils imports
import docutils.core
import docutils.utils
import docutils.frontend
from docutils.transforms import Transformer

# other imports
from sqlobject import *  ## FIXME remove

# nabu imports
import nabu.entryforms
from nabu.entryforms import *



## FIXME move this into being simply the result of one of the transforms
class Document(SQLObject):
    """
    Stored document.
    """
## FIXME _fromDatabase, what does it do?
    unid = StringCol(alternateID=1, length=36, notNull=1)
    title = UnicodeCol()
    date = DateCol()


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
    
    def __init__( self, sources, connection, username=None ):
        self.sources = sources
        self.connection = connection
        if username:
            self.username = username
        
        init_connection(connection)

    def ping( self ):
        return 0

    def getallids( self ):
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
                try:
                    rr = Source.byUnid(unid)
                    ret[rr.unid] = rr.digest
                except SQLObjectNotFound:
                    pass

        return ret

    def clearall( self ):
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



        
        # apply extractor transforms
        doctree.transformer = Transformer(doctree)

## FIXME set settings manually
        settings = docutils.frontend.OptionParser().get_default_values()
        doctree.reporter = docutils.utils.new_reporter('<doctree>', settings)

        doctree.transformer.add_transforms(
            tuple(nabu.entryforms.registry.values()))
        doctree.transformer.apply_transforms()

        # create a map of the applied transforms
        entries = {}
        for transform, priority, transform_class, pending in \
                doctree.transformer.applied:
            ## FIXME FIXME find a per-xform generic way to return stuff
            entries[transform_class.table] = transform.extracted

## FIXME this should be in the "whole document" transform

## FIXME entries should be the result of running all the transforms

## FIXME create tables dynamically depending on what entries are returned


        # For each available schema
        for cls in sqlobject_classes:
            try:
                entry = entries[cls.__name__]
            except KeyError:
                continue

            entry['unid'] = unid

## FIXME check that the entry indeed has a value for the column
## or perhaps create a column
            params = dict( (k._name, entry[k._name]) for k in cls._columns )
            newinst = cls(**params)

        return 0
    
    def dumpall( self ):
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
            
    def dumpone( self, unid ):
        """
        Returns information about a single uploaded source.
        """
        # Note: we need to return some Unicode strings using a UTF-8 encoded as
        # a binary, because we don't know if those long strings will contain
        # line-feed characters, which do not go through the XML-RPC layer.

        r = {}
        try:
            s = Source.byUnid(unid)
        except SQLObjectNotFound:
            return r

        # FIXME: figure out policy for users. Now: all shared, all writable.
        # if s.username != self.username:
        #     return r

        attrs = ('unid', 'filename', 'username', 'digest',)
        for a in attrs:
            r[a] = getattr(s, a)
        r['time'] = s.time.isoformat()
        r['errors'] = xmlrpclib.Binary(s.errors.encode('UTF-8'))
        r['source'] = xmlrpclib.Binary(s.source.encode('UTF-8'))

        doctree = pickle.loads(s.doctree)
        doctree_utf8 = docutils.core.publish_from_doctree(
            doctree, writer_name='pseudoxml',
            settings_overrides={'output_encoding': 'UTF-8'})
        r['doctree'] = xmlrpclib.Binary(doctree_utf8)
        return r

    def geterrors( self ):
        """
        Return a list of mappings with the error texts.
        """
        errors = []
        fields = ['unid', 'filename', 'errors']
        for s in Source.select(Source.q.errors != ''):
            errors.append(dict((a, getattr(s, a)) for a in fields))
        return errors

