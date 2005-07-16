#!/usr/bin/env python
#
# Copyright (C) 2005  Martin Blais <blais@furius.ca>
# This file is distributed under the terms of the GNU GPL license.
# For more information: http://furius.ca/nabu.
#
# $Id$
#

"""
Extract book entries.
"""

# other imports
from sqlobject import *

# nabu imports
from nabu import extract
from nabu.extractors.flvis import FieldListVisitor


class BookExtractor(extract.Extractor):
    """
    Transform that looks at field lists and that heuristically attempts
    to find references to books.  For example,

      :title: National Geographic Photography Field Guide 2nd Edition:
              Secrets to Making Great Pictures
      :author: Peter Burian, Bob Caputo
      :url: http://www.amazon.com/o/ASIN/079225676X/
      :review:
      
        Excellent diversified advice from top photographers.  The book
        manages to pack lots of relevant content in a small format.  It
        contains a nice section on composition, which is what originally
        attracted me to it.  As per usual, I found the digital
        photography section useless, but for the most part, the
        information available in this book is of great value.  This is
        the best general book about photography that I've read.

    The heuristic looks at an empty :book: field, an :ISBN: field, or
    some list that has an author and a title. See the Book class below to
    find out which fields are stored.
    """

    default_priority = 900

    def apply( self, **kwargs ):
        self.unid, self.storage = kwargs['unid'], kwargs['storage']

        # Note: we use a special FieldListVisitor class that we've built
        # to simplify visiting generic field lists.  You could use any of
        # the docutils visitors here instead.
        v = FieldListVisitor(self.document)
        v.initialize()
        self.document.walk(v)
        v.finalize()

        for flist in v.getfieldlists():
            book = 0
            # if there is an empty book field, this is explicitly a book.
            if 'book' in flist and not flist['book'].strip():
                book = 1
            # if there is an ISBN number, then it is *definitely* a book.
            elif 'isbn' in flist:
                book = 1
            elif 'author' in flist and 'title' in flist:
                book = 1

            if book:
                self.store(flist)

    def store( self, flist ):
        emap = {}
        for k, v in flist.iteritems():
            emap[k] = v.astext()

        self.storage.store(self.unid, emap)

            
class Book(SQLObject):
    """
    Storage for book information.
    """
    unid = StringCol(notNull=1)

    title = UnicodeCol()
    author = UnicodeCol()
    year = UnicodeCol()
    url = UnicodeCol()
    review = UnicodeCol()


class BookStorage(extract.SQLObjectExtractorStorage):
    """
    Book storage.
    """

    sqlobject_classes = [Book]

    def store( self, unid, *args ):
        data, = args
        Book( unid=unid,
              title=data.get('title', ''),
              author=data.get('author'),
              year=data.get('year', ''),
              url=data.get('url', ''),
              review=data.get('review', '') )
 
