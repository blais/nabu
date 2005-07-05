#!/usr/bin/env python
#
# Copyright (C) 2005  Martin Blais <blais@furius.ca>
# This file is distributed under the terms of the GNU GPL license.
# For more information: http://furius.ca/nabu.
#
# $Id$
#

"""
Render the contents as a CGI handler, for debugging purposes.

This module contains code that is used to render basic pages for debug purposes,
to see what sources have been uploaded, etc.

Note that this is all very basic on purpose, I did not want to introduce
dependencies.
"""

# stdlib imports
import sys, os, urlparse
from os.path import dirname, join
import cPickle as pickle
from xml.sax.saxutils import escape

# add the nabu libraries to load path
root = dirname(dirname(sys.argv[0]))
sys.path.append(join(root, 'lib', 'python'))

# nabu and other imports
from nabu.extractors.document import Document
from nabu import sources

# docutils imports
import docutils.core


transitional = ('<!DOCTYPE html PUBLIC '
                '"-//W3C//DTD XHTML 1.0 Transitional//EN" '
                '"http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">')


def render_notfound():
    """
    Return a resource-not-found error to the client.
    """
    print 'Content-type:', 'text/plain'
    print 'Status: 404 Document Not Found.'
    print
    print 'Document Not Found.'

def render_index( srcstore, uri, username ):
    """
    Generate an index of documents.
    """
    ashtml = '%s?%s' % (uri, 'ashtml=1&id=%s')

    linkfmt = '%s?id=%%s' % uri
    print 'Content-type:', 'text/html'
    print
    print transitional
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

    print '<table width="100%" class="dump">'
    sr = srcstore.get(username, None,
                      ('unid', 'filename', 'username', 'time', 'errors-p',))
    for s in sr:
        print '<tr>'
        print '<td><a href="%s">%s</a></td>' % (linkfmt % s['unid'],
                                                s['unid'])
        print '<td> <a href="%s">[html]</a></td>' % (ashtml % s['unid'])
        print '<td>%s</td>' % s['filename']
        print '<td>%s</td>' % s['username']
        print '<td>%s</td>' % s['time']
        print '<td>%s</td>' % (s['errors-p'] and 'ERRORS' or '     ')
        print '</tr>'
    print '</table>'
    print '</body></html>'

def render_source_info( src, uri ):
    """
    Render a basic page that dumps all the information available for a source
    upload.
    """
    doctree = src['doctree']
    if doctree is not None:
        # Render the full debug page that displays the contents of an uploaded
        # source and parsed results.
        doctree_str, parts = docutils.core.publish_from_doctree(
            doctree, writer_name='pseudoxml',
            settings_overrides={'output_encoding': 'UTF-8'})
    else:
        doctree_str = ''

    print 'Content-Type:', 'text/html; charset=UTF-8'
    print
    print transitional
    print '<html><head></head><body>'
    print '<div id="header"><a href="%s">Back to Nabu Index</a></div>' % uri
    print '<h1>Source: %s</h1>' % escape(src['unid'])
    print '<dl>'
    print '<dt>Source Filename</dt><dd>%s</dd>' % escape(src['filename'])
    print '<dt>User</dt><dd>%s</dd>' % escape(src['username'])
    print '<dt>Time Uploaded</dt><dd>%s</dd>' % escape(str(src['time']))
    print '<dt>Digest</dt><dd>%s</dd>' % escape(src['digest'])
    print '</dl>'
    if src['errors']:
        print '<a href="#errors">Errors</a> '
    print '<a href="#doctree">Document Tree</a> '
    print '<a href="#source">Source</a> '
    print '<hr/>'
    if src['errors']:
        print '<a name="errors"/><h2>Errors</h2>'
        print '<pre>'
        print escape(src['errors'].encode('utf-8'))
        print '</pre>'
    print '<a name="doctree"/><h2>Document Tree</h2>'
    print '<pre>'
    print escape(doctree_str)
    print '</pre>'
    print '<hr/>'
    print '<a name="source"/><h2>Source</h2>'
    print '<pre>'
    print escape(src['source'].encode('utf-8'))
    print '</pre>'
    print '<hr width="5"/>'
    print '</body></html>'


def render_html( doctree, uri ):
    """
    Render the document tree naively, as HTML.

    Note: this is just for fun.  You should develop your own rendering
    interface, possibly modifying the document tree before rendering it.
    """    
    scheme, netloc, path, parameters, query, fragid = urlparse.urlparse(uri)

    settings = {'stylesheet': '%s://%s/docutils-style.css' % (scheme, netloc),
    		'embed_stylesheet': False,
                'output_encoding': 'UTF-8'}

    doctree_html, parts = docutils.core.publish_from_doctree(
        doctree, writer_name='html', settings_overrides=settings)

    print 'Content-type:', 'text/html'
    print
    sys.stdout.write(parts['html_prolog'].encode('UTF-8'))
    sys.stdout.write(parts['html_head'].encode('UTF-8'))
    print '<link rel="stylesheet" '
    print 'href="http://furius.local.biz/docutils-style.css" '
    print 'type="text/css" />'
    print '<div id="header"><a href="%s">Back to Nabu Index</a></div>' % uri
    sys.stdout.write(parts['html_body'].encode('UTF-8'))
    print '</body></html>'
    return

def contents_handler( srcstore, uri, username, unid, ashtml ):
    """
    Basic handler for the dump/debug contents page.
    Call this from the CGI script after configuration to handle the debug pages.
    """

    if unid is None:
        return render_index(srcstore, uri, username)

    # select the document from the database
    srclist = srcstore.get(
        username, idlist=[unid],
        attributes=('unid', 'filename', 'username', 'time', 'digest',
                    'errors', 'doctree', 'source'))
    if not srclist:
        return render_notfound()

    assert len(srclist) == 1
    src = srclist[0]

    # render document in HTML and leave
    if ashtml:
        doctree = src['doctree']
        if doctree is None:
            print 'Content-type:', 'text/plain'
            print
            print '(No document tree in sources upload.)'
            return
        else:
            return render_html(doctree, uri)

    return render_source_info(src, uri)

