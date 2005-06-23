#!/usr/bin/env python
#
# $Id$
#

"""
Source storage.
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

    unid = StringCol(alternateID=1, length=36, notNull=1)
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
    def getallids( self ):
        """
        Return a list of all the unique ids in the sources.
        """

    def getdigests( self, idlist=None ):
        """
        Return a mapping of (unid, digest) for the requested unids.
        If none is requested, return digests for all.
        """

    def clear( self, idlist=None ):
        """
        Clear the requested ids.
        If none specified, clear all ids.
        """

    def add( self, unid, filename, digest, username, time,
             source, doctree, errors ):
        """
        Add or replace a source entry for a specific unid.

        :Parameters:
          - unid (string/ascii): unique id
          - filename (unicode): original filename 
          - digest (string/ascii): source digest
          - username (string/ascii): the username
          - time (datetime): date/time of upload
          - source (unicode): original source text
          - doctree (instance): document tree
          - errors (unicode): conversion errors
        """

    def get( self, idlist=None, attributes=[] ):
        """
        Get the requested attributes for the request ids.
        If `idlist` is not specified, return attributes for all sources.
        The return value is: a list of dictionaries, where the
        dictionary values have the same types as expected in `add()`.
        """

    def get_errors( self, attributes=[] ):
        """
        Get the requested attributes for the documents with errors.
        """





class SQLObjectSourceStorage(SourceStorage):
    """
    Concrete source storage using an SQLObject connection.
    """
    def __init__( self, connection ):
        "Initialize with an open SQLObject connection."
        self.connection = connection

    def getallids( self ):
        ''

    def getdigests( self, idlist=None ):
        ''

    def clear( self, idlist=None ):
        ''

    def add( self, unid, filename, digest, username, time,
             source, doctree, errors ):
        ''

    def get( self, idlist=None, attributes=[] ):
        ''

    def get_errors( self, attributes=[] ):
        ''

