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
from xml.sax.saxutils import escape

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
    uri = os.environ['SCRIPT_URI']
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
        linkfmt = '%s?id=%%s' % uri
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
            print '<td><a href="%s">%s</a></td>' % (linkfmt % s.unid, s.unid)
            print '<td>%s</td>' % s.filename
            print '<td>%s</td>' % s.username
            print '<td>%s</td>' % s.time
            print '<td>%s</td>' % (s.errors and 'ERRORS' or '     ')
            print '</tr>'
        print '</table>'

## FIXME this should be generic for all tables
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
    sr = Source.select(Source.q.unid==unid)
    if sr.count() == 0:
        print 'Content-type:', 'text/plain'
        print 'Status: 404 Document Not Found.'
        print
        print 'Document not found'
        return
    print >> sys.stderr, sr.count()
##     assert sr.count() == 1
    src = sr[0]

    # read document tree and unpickle it
    doctree = pickle.loads(src.doctree)

    # render document in HTML
    scheme, netloc, path, parameters, query, fragid = urlparse.urlparse(uri)
    settings = {'stylesheet': '%s://%s/docutils-style.css' % (scheme, netloc),
                'output_encoding': 'UTF-8'}

    doctree_str = docutils.core.publish_from_doctree(
        doctree, writer_name='pseudoxml', settings_overrides=settings)

    print 'Content-type:', 'text/html'
    print
    print '<html><head></head><body>'
    print '<h1>Source: %s</h1>' % escape(src.unid)
    print '<dl>'
    print '<dt>Source Filename</dt><dd>%s</dd>' % escape(src.filename)
    print '<dt>User</dt><dd>%s</dd>' % escape(src.username)
    print '<dt>Time Uploaded</dt><dd>%s</dd>' % escape(str(src.time))
    print '<dt>Digest</dt><dd>%s</dd>' % escape(src.digest)
    print '</dl>'
    print '<a href="#doctree">Document Tree</a> '
    print '<a href="#source">Source</a> '
    if src.errors:
        print '<a href="#errors">Errors</a> '
    print '<a href="%s">(Back to Index)</a>' % uri
    print '<hr/>'
    if src.errors:
        print '<a name="errors"/><h2>Errors</h2>'
        print '<pre>'
        print escape(src.errors.encode('utf-8'))
        print '</pre>'
    print '<a name="doctree"/><h2>Document Tree</h2>'
    print '<pre>'
    print escape(doctree_str)
    print '</pre>'
    print '<hr/>'
    print '<a name="source"/><h2>Source</h2>'
    print '<pre>'
    print escape(src.source.encode('utf-8'))
    print '</pre>'
    print '<hr width="5"/>'
    print '</body></html>'


if __name__ == '__main__':
    main()
