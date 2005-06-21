#!/usr/bin/env python
# -*- coding: iso-8859-1 -*-
#
# $Source$
# $Id$
#

"""
Nabu test content list and server.

This script simply attempts to get the pickled document stored in the database
and runs the writer on it to produce the HTML document and returns that.
"""

# stdlib imports
from pprint import pprint, pformat
import sys, os, urlparse
from os.path import dirname, join
import cgi, cgitb; cgitb.enable()
import cPickle as pickle

# add the nabu libraries to load path
root = dirname(dirname(sys.argv[0]))
sys.path.append(join(root, 'lib', 'python'))
sys.path.insert(0, '/home/blais/src/docutils.blais_interrupt_render')
## FIXME remove for testing only

# nabu and other imports
from sqlobject.postgres.pgconnection import PostgresConnection
from nabu.server import init_connection, Document, Source
## import nabu.process

# docutils imports
import docutils.core

#-------------------------------------------------------------------------------
#
def main():
    """
    CGI handler. 
    """
    # connect to the database
    params = {
        'db': 'nabu',
        'user': 'blais',
        'passwd': '$blais',
        'host': 'localhost',
    }
    connection = PostgresConnection(**params)

    init_connection(connection)

    form = cgi.FieldStorage()
    unid = form.getvalue("id")
    if unid is None:
        # generate an index of documents.
        linkfmt = '%s?id=%%s' % os.environ['SCRIPT_URI']
        print 'Content-type:', 'text/html'
        print
        print '<html>'
        print '<head><style>'
        print 'table.dump { font-size: x-small; }'
        print '</style></head>'

        print '<body>'
        print '<h1>(Sources)</h1>'
        print '<table width="100%" class="dump">'
        sr = Source.select()
        for s in sr:
            print '<tr>'
            print '<td>%s</td>' % s.unid
            print '<td>%s</td>' % s.filename
            print '<td>%s</td>' % s.username
            print '<td>%s</td>' % s.time
            print '<td>%s</td>' % (s.errors and True or False)
            print '</tr>'
        print '</table>'

        print '<h2>Documents</h2>'
        print '<table width="100%">'
        sr = Document.select()
        for s in sr:
            print '<tr>'
            print '<td><a href="%s">%s</a></td>' % (linkfmt % s.unid, s.unid)
            print '</tr>'
        print '</table>'
        return

    # select the document from the database
    sr = Document.select(Document.q.unid==unid)
    if sr.count() == 0:
        print 'Content-type:', 'text/plain'
        print 'Status: 404 Document Not Found.'
        print
        print 'Document not found'
        return

    # read and document and unpickle it
    doc = sr[0]
    document = pickle.loads(sr[0].contents)

    # render document in HTML
    scheme, netloc, path, parameters, query, fragid = \
            urlparse.urlparse(os.environ['SCRIPT_URI'])
    settings = {'stylesheet': '%s://%s/docutils-style.css' % (scheme, netloc),
                'output_encoding': 'UTF-8'}

    output = docutils.core.publish_from_doctree(
        document, writer_name='html4css1', settings_overrides=settings)

    print 'Content-type:', 'text/html'
    print
    print output


if __name__ == '__main__':
    main()
