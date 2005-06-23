#!/usr/bin/env python
# -*- coding: iso-8859-1 -*-
#
# $Id$
#

"""
Nabu test content list and server.

This script simply attempts to get the pickled document stored in the database
and runs the writer on it to produce the HTML document and returns that.
"""

# stdlib imports
import sys, os, urlparse
from os.path import dirname, join
import cgi, cgitb; cgitb.enable()
import cPickle as pickle
from xml.sax.saxutils import escape

# add the nabu libraries to load path
root = dirname(dirname(sys.argv[0]))
sys.path.append(join(root, 'lib', 'python'))

# FIXME: this is needed until my docutils branch goes in.
# sys.path.insert(0, '/home/blais/src/docutils.blais_interrupt_render')

# nabu and other imports
from sqlobject.postgres.pgconnection import PostgresConnection
from nabu.server import init_connection, Document, Source

# docutils imports
import docutils.core

#-------------------------------------------------------------------------------
#
def main():
    """
    CGI handler. 
    """
    uri = os.environ['SCRIPT_URI']
    scheme, netloc, path, parameters, query, fragid = urlparse.urlparse(uri)
    ashtml = urlparse.urlunparse(
        [scheme, netloc, path, '', 'ashtml=1&id=%s', ''])

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
        print 'table { font-size: x-small; }'
        print 'p#desc { font-size: x-small; font-style: italic; }'
        print '</style></head>'

        print '<body>'
        print '<h1>Nabu Database Contents</h1>'
        print ('<p id="desc">'
               'This is meant to be used for debugging only. You should'
               'build a suitable presentation interface from the extracted data.'
               '</p>')

        print '<h2>Uploads</h2>'
        print '<table width="100%" class="dump">'
        sr = Source.select()
        for s in sr:
            print '<tr>'
            print '<td><a href="%s">%s</a></td>' % (linkfmt % s.unid, s.unid)
            print '<td> <a href="%s">[html]</a></td>' % (ashtml % s.unid)
            print '<td>%s</td>' % s.filename
            print '<td>%s</td>' % s.username
            print '<td>%s</td>' % s.time
            print '<td>%s</td>' % (s.errors and 'ERRORS' or '     ')
            print '</tr>'
        print '</table>'

        print '<h2>Extracted Info</h2>'


## FIXME this should be something generic to display contents from all special tables
        print '<h3>Documents</h3>'
        print '<table width="100%">'
        sr = Document.select()
        for s in sr:
            print '<tr>'
            print '<td><a href="%s">%s</a></td>' % (linkfmt % s.unid, s.unid)
            print '<td>%s</td>' % s.title
            print '<td>%s</td>' % s.date
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
    assert sr.count() == 1
    src = sr[0]

    # read document tree and unpickle it
    doctree = pickle.loads(src.doctree)

    # render document in HTML and leave
    if form.getvalue("ashtml"):
        settings = {'stylesheet': '%s://%s/docutils-style.css' % (scheme, netloc),
                    'output_encoding': 'UTF-8'}

        doctree_html = docutils.core.publish_from_doctree(
            doctree, writer_name='html', settings_overrides=settings)

        print 'Content-type:', 'text/html'
        print
        print doctree_html


    # Render the full debug page that displays the contents of an uploaded
    # source and parsed results.
    doctree_str = docutils.core.publish_from_doctree(
        doctree, writer_name='pseudoxml',
        settings_overrides={'output_encoding': 'UTF-8'})

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
    print '<a href="%s">[As Html]</a> ' % (ashtml % src.unid)
    print '<a href="%s">[Back to Index]</a>' % uri
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
