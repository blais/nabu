#!/usr/bin/env python
#
# Copyright (C) 2005  Martin Blais <blais@furius.ca>
# This file is distributed under the terms of the GNU GPL license.
# For more information: http://furius.ca/nabu.
#
# $Id$
#

"""
Source storage.
"""

# stdlib imports
import sys, re, datetime
import cPickle as pickle
from pprint import pprint, pformat ## FIXME remove


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

    def map_unid( self, unid, user ):
        """
        Map the unique id to the final storage id, if a transformation on the id
        needs to happen.  This final unique-id is used during the extraction
        process, by the transforms.
        """
        return unid # Default needs to do no transform.


class PerUserSourceStorageProxy(SourceStorage):
    """
    Proxy source storage that manipulates the ids to provide per-user source
    sets.

    Note that it does not make sense to configure the server with this if you're
    going to share the same body of source documents between users.

      connection = PostgresConnection(**params)
      src_pp = sources.DBSourceStorage(connection)
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

    def map_unid( self, unid, user ):
        return self.__add_user(unid, user)

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
    Concrete source storage using a DBAPI-2.0 connection.  This one shares the
    uploaded sources, there is no per-user document store.  For example, one
    user could completely remove everyone else's documents.

    Note that the uploaded sources table may not contain the document tree nor
    the source document.  This is a matter of policy and if you desire to store
    the document tree, you should use the extractor appropriate for that
    purpose.
    """

    # Definition of table storage for uploaded source documents.
    __table_name = '__sources__'

    # Note: this code is specific to PostgreSQL.  Adjust to your preference.
    __table_schema = '''

CREATE TABLE %s
(
    unid TEXT PRIMARY KEY,
    filename TEXT,
    digest VARCHAR(32) NOT NULL,
    username VARCHAR(32),
    "time" TIMESTAMP,
    source TEXT,
    doctree BYTEA,
    errors TEXT
);

''' % __table_name

## FIXME: remove
## ALTER TABLE %s OWNER TO nabu;

    def __init__( self, module, connection, 
                  store_source=True, store_doctree=True ):
        "Initialize with an open DBAPI-2.0 connection."
        self.module, self.connection = module, connection

        assert module.paramstyle in ['format', 'pyformat']

        self.store_source = store_source
        self.store_doctree = store_doctree

        # Checks that the database tables exist and if they don't, creates them.
        cursor = self.connection.cursor()
        cursor.execute("""
           SELECT table_name FROM information_schema.tables WHERE table_name = %s
           """, (DBSourceStorage.__table_name,))
        if cursor.rowcount == 0:
            self.reset_schema(False)

    def __select( self, user ):
        query = "SELECT %%s FROM %s" % DBSourceStorage.__table_name
        if user:
            query += " WHERE username = '%s'" % user
        return query

    def getallids( self, user ):
        cursor = self.connection.cursor()

        query = self.__select(user) % 'unid'
        cursor.execute(query)
        return [x[0] for x in cursor.fetchall()]

    def getdigests( self, user, idlist=None ):
        cursor = self.connection.cursor()

        query = self.__select(user) % 'unid, digest'

        ret = {}
        if idlist is None:
            cursor.execute(query)
            for unid, digest in cursor.fetchone():
                ret[unid] = digest
        else:
            for unid in idlist:
                cursor.execute(query + " AND unid = %s", (unid,))
                if cursor.rowcount > 0:
                    unid, digest = cursor.fetchone()
                    ret[unid] = digest

        return ret

    def clear( self, user, idlist=None ):
        cursor = self.connection.cursor()
        try:
            query = "DELETE FROM %s" % DBSourceStorage.__table_name
            if user:
                query += " WHERE username = '%s'" % user

            if idlist is None:
                cursor.execute(query)
            else:
                for unid in idlist:
                    cursor.execute(query + " AND unid = %s", (unid,))
        finally:
            self.connection.commit()

    def add( self, user, unid, filename, digest, time,
             source, doctree, errors, docpickled=None ):

        if not self.store_source:
            source = u''

        if not self.store_doctree:
            docpickled = ''
        elif docpickled is None:
            # remove reporter before pickling.
            doctree.reporter = None
            docpickled = pickle.dumps(doctree)

        bindoc = self.module.Binary(docpickled)

        cursor = self.connection.cursor()
        cursor.execute("""
           INSERT INTO %s
             (unid, filename, digest, username, time, source, errors, doctree)
           VALUES
             (%%s, %%s, %%s, %%s, %%s, %%s, %%s, %%s)
             """ % DBSourceStorage.__table_name,
           (unid, filename, digest, user, time, source, errors, bindoc))
        self.connection.commit()


    def get( self, user, idlist=None, attributes=[] ):
        cursor = self.connection.cursor()

        attribstr = ', '.join(attributes)
        query = self.__select(user) % attribstr
        if idlist is not None:
            query += user and ' AND ' or ' WHERE '
            query += 'unid IN (%s)' % ', '.join(['%s'] * len(idlist))
            cursor.execute(query, idlist)
        else:
            cursor.execute(query)

        return self.__get(cursor, attributes)

    def get_errors( self, user, attributes=[] ):
        attribstr = ', '.join(attributes)
        query = self.__select(user) % attribstr
        query += ' WHERE errors IS NOT NULL'

        cursor = self.connection.cursor()
        cursor.execute(query)
        return self.__get(user, sr, attributes)

    def __get( self, cursor, attributes ):
        """
        Converts search results to expected values.
        """
        results = []
        for i in xrange(cursor.rowcount):
            row = cursor.fetchone()
            m = {}
            for value, attr in zip(row, attributes):
                if attr == 'doctree':
                    if value:
                        value = pickle.loads(str(value))
                    else:
                        value = None

                elif attr in ['filename', 'source', 'errors']:
                    # Note: we're assuming that the database is in UTF-8
                    # encoding.
                    value = value.decode('utf-8')

                m[attr] = value
            results.append(m)
        return results

    def reset_schema( self, drop=True ):
        cursor = self.connection.cursor()
        if drop:
            cursor.execute("DROP TABLE %s" % DBSourceStorage.__table_name)
        cursor.execute(DBSourceStorage.__table_schema)
        self.connection.commit()
        
