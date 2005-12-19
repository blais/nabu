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


class SQLExtractorStorage(ExtractorStorage):
    """
    Extractor storage base class for storage that uses a DBAPI-2.0 connection.

    Note: all of the declared tables should have a non-null unid column, to
    enable clearing obsolete data when reloading a source document.
    """

    # Override this in the derived class.
    # This should be a map from the table name to the table schema.
    sql_tables = {}

    def __init__( self, module, connection ):
        self.module, self.connection = module, connection

        cursor = self.connection.cursor()

        # Check that the database tables exist and if they don't, create them.
        for tname, tschema in self.sql_tables.iteritems():
            cursor.execute("""
               SELECT table_name FROM information_schema.tables WHERE table_name = %s
               """, (tname,))
            if cursor.rowcount == 0:
                cursor.execute(tschema)

        self.connection.commit()

    def clear( self, unid=None ):
        """
        Default implementation that clears the entries/tables.
        """
        cursor = self.connection.cursor()

        for tname, tschema in self.sql_tables.iteritems():
            query = "DELETE FROM %s" % tname
            if unid is not None:
                query += " WHERE unid = '%s'" % unid

        self.connection.commit()

    def reset_schema( self ):
        """
        Default implementation that drops the tables.
        """
        cursor = self.connection.cursor()

        for tname, tschema in self.sql_tables.iteritems():
            cursor.execute("DROP TABLE %s" % tname)
            cursor.execute(tschema)

        self.connection.commit()


# Note: the next class is provided as a convenience for people who want to use
# SQLObject, but Nabu itself does not depend on SQLObject in any way.
#
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
            cls.createTable()

