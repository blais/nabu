#
# Copyright (C) 2005  Martin Blais <blais@furius.ca>
# This file is distributed under the terms of the GNU GPL license.
# For more information: http://furius.ca/nabu.
#
# $Id$
#

"""
Extract document tree and bibliographic fields.
"""

import re, datetime, copy
import pickle

from docutils import nodes

from nabu import extract


class InitialExtractor(extract.Extractor):
    """
    Document tree storage. This is used to store the document tree at the point
    of a transform.  Typically, we would not necessarily want the document tree
    that is stored in the sources upload table to be reused, we would rather
    store it explicitly for presentation and leave the Nabu mechanism alone.

    Note that this results in more database storage.  I suppose that we could
    forego storing the source and/or document tree in the sources upload
    storage.
    """

    default_priority = 1

    def apply( self, unid=None, storage=None, pickle_receiver=None ):
        self.unid = unid
        self.storage = storage
        # Store the document at this point.
        pickled = self.storage.store(self.unid, self.document)
        if pickled:
            pickle_receiver.append(pickled)


class DoctreeStorage(extract.SQLExtractorStorage):
    """
    Document tree storage.
    """
    sql_tables = { 'doctree': '''

        CREATE TABLE doctree
        (
           unid TEXT PRIMARY KEY,
           doctree BYTEA
        )

        '''
        }

    def store( self, unid, doctree ):

        # Temporarily remove the reporter and transformer, just for pickling.
        saved_reporter = doctree.reporter
        saved_transformer = doctree.transformer
        try:
            doctree.reporter = None
            doctree.transformer = None
            doctree_pickled = pickle.dumps(doctree)
        finally:
            doctree.reporter = saved_reporter
            doctree.transformer = saved_transformer

        bindoc = self.module.Binary(doctree_pickled)

        cursor = self.connection.cursor()
        cursor.execute("""
          INSERT INTO doctree (unid, doctree) VALUES (%s, %s)
          """, (unid, bindoc))
        self.connection.commit()

        return doctree_pickled
