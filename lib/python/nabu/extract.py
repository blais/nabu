#!/usr/bin/env python
#
# Copyright (C) 2005  Martin Blais <blais@furius.ca>
# This file is distributed under the terms of the GNU GPL license.
# For more information: http://furius.ca/nabu.
#
# $Id$
#

"""
Interfaces that should be implemented by extractors.
"""

# docutils imports
import docutils.transforms

# sqlobject imports
from sqlobject import *

class Extractor(docutils.transforms.Transform):
    """
    Base class for extractors.
    Essentially, they're transforms which can modify the document or store
    stuff somewhere, using the storage instance given to it.

    A reference to a storage interface object and the unique id of the
    document that will be transformed by this transform will be given when
    calling apply. (This should be used to identify the extracted items in
    the database, to associate them with the source document, this is
    important in order to be able to clear the data of these items when a
    document is reprocessed later on).
    """

    @classmethod
    def init_parser( cls ):
        """
        Initialization that is bound to occur before the parser.  By default
        this method does nothing, and it's fine and dandy.

        If you want to add new directives to the processing, this is the place
        to do it.
        """
        # noop.


class ExtractorStorage:
    """
    Interface to implement by objects which will store extracted data associated
    with a document.
    """
    def store( self, unid, *args ):
        """
        Store the given data, which could be of any type, associated with the
        given unid.  Note: it it very important to store the data in a way that
        we can later associate or clear it with the given unid.
        """

    def clear( self, unid=None ):
        """
        Clear all the data for this extractor, that is associated with the given
        unid.  If no id is specified, clear all the data associated with this
        storage.
        """

    def reset_schema( self ):
        """
        Resets the schema.
        This may be used for development, debugging, and configuration.
        The server makes sure that this does not get called there is valuable
        data stored in the database.
        """


class SQLObjectExtractorStorage(ExtractorStorage):
    """
    Extractor storage base class for storage that uses the SQLObject wrappers.
    This offers the convenience of simply having to declare the SQLObject
    classes as a class variable and their connection gets initialized
    automatically.
    """

    sqlobject_classes = [] # override this in the derived class.
    
    def __init__( self, connection ):
        assert self.sqlobject_classes
        
        # Initialize the connections for all the wrappers.
        for cls in self.sqlobject_classes:
            cls._connection = connection

        # Checks that the database tables exist and if they don't, creates them.
        for cls in self.sqlobject_classes:
            cls.createTable(ifNotExists=True)

    def clear( self, unid=None ):
        """
        Default implementation that clears the entries/tables.
        """
        for cls in self.sqlobject_classes:
            if unid is None:
                cls.clearTable()
            else:
                for s in cls.select(cls.q.unid == unid):
                    s.destroySelf()

    def reset_schema( self ):
        """
        Default implementation that drops the tables.
        """
        for cls in self.sqlobject_classes:
            cls.dropTable()


def get_generic_table_values( connection, tablename, unid=None ):
    """
    Convenience method that generically gets the values from a table.  You need
    to supply a valid connection object and a tablename, and optionally, a unid
    to filter by.  This returns a list of dictionaries, one for each table row,
    and a list of column names.
    """

    from sqlobject import SQLObject
##    cls = type(tablename, (SQLObject,), {})
## this will work only once, because of the SQLObject class registry, I need to
## declare the ORM wrapper generically.

    class ExtractedObject(SQLObject):
        class sqlmeta:
            table = tablename
        _fromDatabase = True
        _connection = connection

    colnames = [col.name for col in ExtractedObject._columns]
    if unid is None:
        sr = ExtractedObject.select()
    else:
        sr = ExtractedObject.select(ExtractedObject.q.unid == unid)
        
    values = []
    for s in sr:
        dic = {}
        values.append(dic)
        for name in colnames:
            dic[name] = getattr(s, name)
        
    return values, colnames

