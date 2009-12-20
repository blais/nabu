# -*- coding: utf-8 -*-
#
# Copyright (C) 2005  Martin Blais <blais@furius.ca>
# This file is distributed under the terms of the GNU GPL license.
# For more information: http://furius.ca/nabu.
#

"""
Extract book entries.
"""

# stdlib imports
import sys, re
from urllib import quote_plus
from xml.sax.saxutils import escape

# nabu imports
from nabu import extract
from nabu.extractors.flvis import FieldListVisitor
import nabu.external.isbn import toI10

# docutils imports
from docutils.nodes import                                      \
  paragraph, Text, container, block_quote, reference, Text



book_isbn_template = 'http://amazon.com/o/ASIN/%s/'
book_search_template = ('http://books.google.com/books?q=%s'
                        '&btnG=Search+Books&as_brr=0')


def astext(el):
    """
    Convert a docutils node or a list of nodes to text.  Deals with a list as
    well as a single node.
    """
    if isinstance(el, (tuple, list)):
        return '\n'.join(x.astext() for x in el)
    elif isinstance(el, unicode):
        return el
    elif isinstance(el, str):
        return el.decode('utf-8')
    else:
        return el.astext()


class Extractor(extract.Extractor):
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

    def apply(self, **kwargs):
        self.unid, self.storage = kwargs['unid'], kwargs['storage']

        # Note: we use a special FieldListVisitor class that we've built
        # to simplify visiting generic field lists.  You could use any of
        # the docutils visitors here instead.
        v = FieldListVisitor(self.document)
        v.apply()

        for fnode, flist in v.getfieldlists():
            book = 0
            # if there is an empty book field, this is explicitly a book.
            if 'book' in flist or 'article' in flist:
                book = 1
            # if there is an ISBN number, then it is *definitely* a book.
            elif 'isbn' in flist:
                book = 1
            elif ('title' in flist and
                  ('author' in flist or
                   'authors' in flist or
                   'publication' in flist)):
                book = 1

            if book:
                self.store(flist)

                # FIXME: we should remove all the formatting and rendering that
                # is being done here and move it to the rendering phase instead.

                # Remove the field list and render something nicer for a book.
                ifields = []
                for field, fieldnames in (
                    ('title', ('title',)),
                    ('author', ('author', 'authors')),
                    ):

                    for fname in fieldnames:
                        f = flist.get(fname)
                        if f:
                            break
                    if f:
                        f = astext(f)
                    else:
                        f = u'<unknown %s>' % field
                    ifields.append(f)

                isbn = flist.pop('isbn', None)
                if isbn:
                    # Note: ASINs for older books are often the same as 10-char ISBNs.
                    # For newer books, they may not be.
                    # New 13-char ISBNs cannot be linked directly; a search has to be made.
                    # http://affiliate-blog.amazon.co.uk/2006/12/13digitisbn_how.html
                    # You'll have to use the e-commerce services in order to do this (this sucks).
                    # In the meantime we use a heuristic, which will work most of the time.
                    amz_asin = re.sub('[^0-9]', '', toI10(astext(isbn)))
                    url = book_isbn_template % amz_asin
                else:
                    booktitle = flist.get('title', '')
                    url = (book_search_template %
                           quote_plus(astext(booktitle).encode('utf-8')))

                title = paragraph('', '',
                    Text(u'Book: '),
                    reference(refuri=url,
                              classes=['external'],
                              text=u'“%s”, %s' % tuple(ifields)),
                    )

                # details
                details = []

                tfields = []
                for name, value in flist.iteritems():
                    if name not in ('title', 'author', 'comments'):
                        text = astext(value)
                        if text:
                            tfields.append(text)
                if tfields:
                    p = paragraph(text=u','.join(tfields),
                                  classes=['book-fields'])
                    details.append(p)

                for name in 'comments', 'comment', 'notes':
                    comments = flist.get('comments')
                    if comments:
                        break
                if comments:
                    comments = astext(comments)
                    p = paragraph(text=comments,
                                  classes=['book-comments'])
                    details.append(p)
                
                newbook = container(
                    '',
                    title,
                    block_quote('', *details),
                    classes=['book'])

                fnode.parent.replace(fnode, newbook)


    def store(self, flist):
        emap = {}
        for k, v in flist.iteritems():
            emap[k] = astext(v)

        self.storage.store(self.unid, emap)


class Storage(extract.SQLExtractorStorage):
    """
    Book storage.
    """
    sql_relations_unid = [
        ('book', 'TABLE',
         """

          CREATE TABLE book
          (
             unid TEXT NOT NULL,
             isbn CHAR(16),
             title TEXT,
             author TEXT,
             year TEXT,
             url TEXT,
             review TEXT
          );

        """),
        ]

    sql_relations = [
        ('book_isbn_idx', 'INDEX', """

          CREATE INDEX book_isbn_idx ON book (isbn);

         """)
        ]

    def store(self, unid, *args):
        data, = args
        
        # Validate ISBN
        isbn = data.get('isbn', '')
        if len(isbn) > 16:
            print >> sys.stderr, ("Warning: ISBN '%s' seems invalid." % isbn)
            data['isbn'] = isbn[:16]

        cols = ('unid', 'isbn', 'title', 'author', 'year', 'url', 'review')
        values = [unid]
        for n in cols[1:]:
            values.append( data.get(n, '') )

        cursor = self.connection.cursor()
        cursor.execute("""
          INSERT INTO book (%s) VALUES (%%s, %%s, %%s, %%s, %%s, %%s, %%s)
          """ % ', '.join(cols), values)

        self.connection.commit()
        
