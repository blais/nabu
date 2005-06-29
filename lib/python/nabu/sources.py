#!/usr/bin/env python
#
# $Id$
#

"""
Source storage.
"""

# stdlib imports
import re, datetime
import cPickle as pickle

# other imports
from sqlobject import *


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

    unid = StringCol(alternateID=1, notNull=1)
    filename = UnicodeCol(length=256)
    digest = StringCol(length=32, notNull=1)
    username = StringCol(length=32)
    time = DateTimeCol()
    source = UnicodeCol()
    doctree = BLOBCol() # pickled doctree, before custom transforms.
    errors = UnicodeCol()


class SourceStorage:
    """
    Interface for the sources storage.
    """
    def getallids( self, user ):
        """
        Return a list of all the unique ids in the sources.
        """

    def getdigests( self, user, idlist=None ):
        """
        Return a mapping of (unid, digest) for the requested unids.
        If none is requested, return digests for all.
        """

    def clear( self, user, idlist=None ):
        """
        Clear the requested ids.
        If none specified, clear all ids.
        """

    def add( self, user, unid, filename, digest, time,
             source, doctree, errors, docpickled=None ):
        """
        Add or replace a source entry for a specific unid.

        :Parameters:
          - user (string/ascii): the username
          - unid (string/ascii): unique id
          - filename (unicode): original filename
          - digest (string/ascii): source digest
          - time (datetime): date/time of upload
          - source (unicode): original source text
          - doctree (instance): document tree
          - errors (unicode): conversion errors
          - docpickled (string): a pickled version of the tree (optional)

        The optional `docpickled` parameter is meant to be used as an
        optimization, only to be given if we already have a copy of the pickled
        document handy.  The concrete implementatoin of the source storage may
        decide to store the document tree differently.
        """

    def get( self, user, idlist=None, attributes=[] ):
        """
        Get the requested attributes for the request ids.
        If `idlist` is not specified, return attributes for all sources.
        The return value is: a list of dictionaries, where the
        dictionary values have the same types as expected in `add()`.

        Note: an extra attribute can be requests: error-p, which contains a bool
        that specifies if there were errors.
        """

    def get_errors( self, user, attributes=[] ):
        """
        Get the requested attributes for the documents with errors.
        """

    def reset_schema( self ):
        """
        Reset the database schema.
        This only happens if the server allows it.
        """


class PerUserSourceStorageProxy(SourceStorage):
    """
    Proxy source storage that manipulates the ids to provide per-user source
    sets.

    Note that it does not make sense to configure the server with this if you're
    going to share the same body of source documents between users.


    Make sure that the proxied storage restricts users for this to work.
    For example, this could be done like this using the DBSourceStorage::

      connection = PostgresConnection(**params)
      src_pp = sources.DBSourceStorage(connection, restrict_user=1)
      src = sources.PerUserSourceStorageProxy(src_pp)


    """
    # Note: to be completely on the side of angels, we should make sure that the
    # usernames do not contain ':'.

    ure = re.compile('([^:]+):(.*)')

    def __init__( self, proxied ):
        self.prox = proxied

    def __add_user( self, unid, user ):
        return '%s:%s' % (user, unid)

    def __remove_user( self, unid, user ):
        mo = PerUserSourceStorageProxy.ure.match(unid)
        assert mo
        assert mo.group(1) == user # double dooper sanity check
        return mo.group(2)

    def getallids( self, user ):
        return [self.__remove_user(x, user) for x in self.prox.getallids(user)]

    def getdigests( self, user, idlist=None ):
        digests = self.prox.getdigests(
            user, [self.__add_user(x, user) for x in idlist])
        return dict([(self.__remove_user(x, user), d) \
                     for x, d in digests.iteritems()])

    def clear( self, user, idlist=None ):
        if idlist is not None:
            idlist = [self.__add_user(x, user) for x in idlist]
        return self.prox.clear(user, idlist)

    def add( self, user, unid, filename, digest, time,
             source, doctree, errors, docpickled=None ):
        unid = self.__add_user(unid, user)
        return self.prox.add(user, unid, filename, digest, time,
                             source, doctree, errors, docpickled)

    def __remove_user_dicts( self, dictlist, user ):
        "Fixes unids in lists of dictionaries."
        for dic in dictlist:
            if 'unid' in dic:
                dic['unid'] = self.__remove_user(dic['unid'], user)
        return dictlist

    def get( self, user, idlist=None, attributes=[] ):
        if idlist is not None:
            idlist = [self.__add_user(x, user) for x in idlist]
        dl = self.prox.get(user, idlist, attributes)
        if 'unid' in attributes:
            self.__remove_user_dicts(dl, user)
        return dl

    def get_errors( self, user, attributes=[] ):
        dl = self.prox.get_errors(user, attributes)
        if 'unid' in attributes:
            self.__remove_user_dicts(dl, user)
        return dl

    def reset_schema( self ):
        return self.prox.reset_schema()


class DBSourceStorage(SourceStorage):
    """
    Concrete source storage using an SQLObject connection.
    This one shares the documents, there is no per-user document store.
    For example, one user could completely remove everyone else's documents.
    """
    def __init__( self, connection, restrict_user=False ):
        "Initialize with an open SQLObject connection."
        self.connection = connection
        Source._connection = connection

        self.restrict_user = restrict_user

    def __select( self, user, op=None ):
        if self.restrict_user:
            if op:
                sr = Source.select(AND(Source.q.username == user, op))
            else:
                sr = Source.select(Source.q.username == user)
        else:
            if op:
                sr = Source.select(op)
            else:
                sr = Source.select()
        return sr
    
    def getallids( self, user ):
        return [r.unid for r in self.__select(user)]

    def getdigests( self, user, idlist=None ):
        ret = {}

        if idlist is None:
            for r in self.__select(user):
                ret[r.unid] = r.digest
        else:
            for unid in idlist:
                try:
                    rr = Source.byUnid(unid)
                    ret[rr.unid] = rr.digest
                except SQLObjectNotFound:
                    pass

        return ret

    def clear( self, user, idlist=None ):
        if idlist is None:
            Source.clearTable()
        else:
            for unid in idlist:
                for s in self.__select(user, Source.q.unid == unid):
                    s.destroySelf()

    def add( self, user, unid, filename, digest, time,
             source, doctree, errors, docpickled=None ):

        if docpickled is None:
            docpickled = pickle.dumps(doctree)

        Source(unid=unid,
               filename=filename,
               digest=digest,
               username=user,
               time=time,
               source=source,
               doctree=docpickled,
               errors=errors)

    def get( self, user, idlist=None, attributes=[] ):
        if idlist is None:
            sr = self.__select(user)
        else:
            sr = self.__select(user, IN(Source.q.unid, idlist))
        return self.__get(user, sr, attributes)

    def get_errors( self, user, attributes=[] ):
        sr = self.__select(user, Source.q.errors != '')
        return self.__get(user, sr, attributes)

    def __get( self, user, sr, attributes ):
        "Converts search results to expected values."

        for s in sr:
            s.sdict = {}

        for a in attributes:
            if a == 'doctree':
                for x in sr:
                    x.sdict['doctree'] = pickle.loads(s.doctree)
            elif a == 'errors-p':
                for x in sr:
                    x.sdict[a] = bool(x.errors)
            else:
                for x in sr:
                    x.sdict[a] = getattr(x, a)

        return [x.sdict for x in sr]

    def reset_schema( self ):
        Source.dropTable()
        Source.createTable()

    
