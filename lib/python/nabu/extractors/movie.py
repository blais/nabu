#!/usr/bin/env python
#
# Copyright (C) 2005  Martin Blais <blais@furius.ca>
# This file is distributed under the terms of the GNU GPL license.
# For more information: http://furius.ca/nabu.
#
# $Id$
#

"""
Extractor for movies.

Movies are to be references with a custom role, e.g.::

   :movie:`Black Dahlia`

Optionally, the role may contain the movie's catalog number, like this::

   :movie:`Black Dahlia <tt0387877>`

Note: this is rather incomplete.  We still need to

- store the movies in the database
- extract and render the link using the catalog number if the catalog is present

  I think maybe we want to render the actual movie catalog link at render time
  only (maybe that becomes customizable too)

- convert all my source files to use the interpreted roles
- allow for a 'star' marker to indicate movies that I really liked


"""

# stdlib imports
import re
from urllib import quote_plus

# docutils imports
from docutils import utils, nodes
from docutils.parsers.rst import roles

# nabu imports
from nabu import extract


movie_catalog_template = 'http://imdb.com/title/%s/'
movie_search_template = 'http://imdb.com/find?q=%s;s=all'


#-------------------------------------------------------------------------------
#
def mtext_quote(s):
    return quote_plus(s.encode('latin-1'))
## FIXME: we need to solve nicely the problem of generating URLs with search
## text embedded in their GET parameters.

def movie_role(role, rawtext, text, lineno, inliner,
               options={}, content=[]):
    roles.set_classes(options)
    options.setdefault('classes', []).append('movie')
    text = utils.unescape(text)
    mo = re.match('(.*)\s*<(.*)>\s*', text)
    if mo:
        text = mo.group(1)
        uri = movie_catalog_template % mo.group(2)
    else:
        uri = movie_search_template % mtext_quote(text)
    options['refuri'] = uri
        
    return [nodes.reference(rawtext, text, **options)], []

roles.register_local_role('movie', movie_role)


#-------------------------------------------------------------------------------
#
class Extractor(extract.Extractor):
    """
    Extractor for movies.
    """

    default_priority = 900

    def apply(self, **kwargs):
        unid, storage = kwargs['unid'], kwargs['storage']

        v = self.Visitor(self.document, unid, storage)
        self.document.walkabout(v)

        if v.extracted:
            self.document.reporter.info(
                'Movie extractor: %s' % pformat(v.extracted))

    class Visitor(nodes.SparseNodeVisitor):

        def __init__(self, document, unid, storage):
            nodes.SparseNodeVisitor.__init__(self, document)
            self.unid = unid
            self.storage = storage
            self.extracted = {}

            self.desc = None

        def visit_reference(self, node):
## FIXME: todo
            pass

##     def store(self, flist):
##         emap = {}
##         for k, v in flist.iteritems():
##             if isinstance(v, (list, tuple)):
##                 s = '\n'.join(map(lambda x: x.astext(), v))
##             else:
##                 s = v.astext()
##             emap[k] = s

##         self.storage.store(self.unid, emap)


class Storage(extract.SQLExtractorStorage):
    """
    Movie storage.
    """
    sql_relations_unid = [
        ('movie', 'TABLE',
         """

          CREATE TABLE movie
          (
             unid TEXT NOT NULL,
             title TEXT,
             catalog VARCHAR(128)
          );

        """),
        ]

    def store(self, unid, *args):
        pass
        ## FIXME: todo
