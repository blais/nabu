#!/usr/bin/env python
#
# Copyright (C) 2005  Martin Blais <blais@furius.ca>
# This file is distributed under the terms of the GNU GPL license.
# For more information: http://furius.ca/nabu.
#
# $Id$
#

"""
Renderers for contents of CGI handler, for debugging purposes.

This module contains code that is used to render basic pages for debug purposes,
to see what sources have been uploaded, what information has been extracted from
them, etc.
"""

# stdlib imports
import sys, os, urlparse, StringIO
from os.path import dirname, join
import cPickle as pickle
from xml.sax.saxutils import escape

# nabu and other imports
from nabu import sources

# docutils imports
import docutils.core

#-------------------------------------------------------------------------------
# Stylesheet.
css = '''

table.nabu {
  font-size: x-small;
  border: thin solid black;
  }

table.nabu td {
  border: thin solid #CCC;
  }

p#desc {
  font-size: small;
  font-style: italic;
  }

#navigation-parent {
  text-align: center;
  }

#navigation {
  font-size: x-small;
  margin-left: auto;
  margin-right: auto;
  padding-bottom: 3px;
  border-bottom: thin dashed #CCC;
  }

#navigation-unid {
  color: #666;
  font-weight: bold;
  margin-left: 2em;
  margin-right: 2em;
  }

'''

stylesheet = ('http://docutils.sourceforge.net'
              '/docutils/writers/html4css1/html4css1.css')

pages_header = '''<!DOCTYPE html PUBLIC
   "-//W3C//DTD XHTML 1.0 Transitional//EN"
   "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">

<html>
  <head>
  <meta http-equiv="Content-Type" content="text/html; charset=utf-8" />
  <link rel="stylesheet" href="%s" type="text/css" />
<style>
%s
</style>
</head>
<body>

''' % (stylesheet, css)

pages_footer = '''
</body>
</html>
'''

#-------------------------------------------------------------------------------
#
def navig_index( uri ):
    """
    Render a simple navigation header div in the document pages.
    """
    return '''
    <div id="navigation-parent">
    <div id="navigation">
       <a href="%s">[index]</a>
    </div>
    </div>
    '''% uri

def navig( uri, unid ):
    """
    Render a simple navigation header div in the document pages.
    """
    return '''
    <div id="navigation-parent">
    <div id="navigation">
       <a href="%s">[index]</a>
       <span id="navigation-unid">%s</span>
       <a href="%s">[source]</a> |
       <a href="%s">[extracted]</a> |
       <a href="%s">[html]</a>
    </div>
    </div>
    '''% (uri, unid,
          '%s?id=%s&view=source' % (uri, unid),
          '%s?id=%s&view=extracted' % (uri, unid),
          '%s?id=%s&view=html' % (uri, unid))


#-------------------------------------------------------------------------------
#
def render_notfound():
    """
    Return a resource-not-found error to the client.
    """
    os = StringIO.StringIO()
    print >> os, 'Content-type:', 'text/plain'
    print >> os, 'Status: 404 Document Not Found.'
    print >> os
    print >> os, 'Document Not Found.'
    return os.getvalue()

#-------------------------------------------------------------------------------
#
def render_index( uri, username, srcstore ):
    """
    Generate an index of documents.
    """
    os = StringIO.StringIO()
    linkfmt = '%s?id=%%s&view=%%s' % uri
    print >> os, pages_header
    print >> os, '''
    <h1>Nabu Database Contents</h1>
    <a href="%s?view=extracted">[view all extracted]</a>
    <p id="desc">
    This is meant to be used for debugging only. You should
    build a suitable presentation interface from the extracted data.
    </p>
    ''' % uri

    print >> os, '<table width="100%" class="dump nabu">'
    sr = srcstore.get(username, None,
                      ('unid', 'filename', 'username', 'time', 'errors',))

    for s in sr:
        print >> os, '<tr>'
        print >> os, '<td><a href="%s">%s</a></td>' % (linkfmt % (s['unid'], 'source'),
                                                s['unid'])
        print >> os, '<td>'
        print >> os, '  <a href="%s">S</a>' % linkfmt % (s['unid'], 'source')
        print >> os, '  <a href="%s">E</a>' % linkfmt % (s['unid'], 'extracted')
        print >> os, '  <a href="%s">H</a>' % linkfmt % (s['unid'], 'html')
        print >> os, '</td>'
        print >> os, '<td>%s</td>' % s['filename']
        print >> os, '<td>%s</td>' % s['username']
        print >> os, '<td>%s</td>' % s['time']
        print >> os, '<td>%s</td>' % (s['errors'] and 'ERRORS' or '     ')
        print >> os, '</tr>'
    print >> os, '</table>'
    print >> os, pages_footer
    return os.getvalue()

#-------------------------------------------------------------------------------
#
def render_source( unid, uri, username, srcstore ):
    """
    Render a basic page that dumps all the information available for a source
    upload.
    """
    sr = srcstore.get(username, [unid],
                      ('unid', 'filename', 'username', 'time', 'digest',
                       'errors', 'doctree', 'source'))
    assert len(sr) == 1
    src = sr[0]

    doctree = src['doctree']
    if doctree is not None:
        # Render the full debug page that displays the contents of an uploaded
        # source and parsed results.
        doctree_str = docutils.core.publish_from_doctree(
            doctree, writer_name='pseudoxml',
            settings_overrides={'output_encoding': 'UTF-8'})
    else:
        doctree_str = ''

    os = StringIO.StringIO()
    print >> os, pages_header
    print >> os, navig(uri, unid)
    print >> os, '<h1>Source</h1>'
    print >> os, '<dl>'
    print >> os, '<dt>Source Filename</dt><dd>%s</dd>' % escape(src['filename'])
    print >> os, '<dt>User</dt><dd>%s</dd>' % escape(src['username'])
    print >> os, '<dt>Time Uploaded</dt><dd>%s</dd>' % escape(str(src['time']))
    print >> os, '<dt>Digest</dt><dd>%s</dd>' % escape(src['digest'])
    print >> os, '</dl>'
    if src['errors']:
        print >> os, '<a href="#errors">Errors</a> '
    print >> os, '<a href="#doctree">Document Tree</a> '
    print >> os, '<a href="#source">Source</a> '
    print >> os, '<hr/>'
    if src['errors']:
        print >> os, '<a name="errors"/><h2>Errors</h2>'
        print >> os, '<pre>'
        print >> os, escape(src['errors'].encode('utf-8'))
        print >> os, '</pre>'
    print >> os, '<a name="doctree"/><h2>Document Tree</h2>'
    print >> os, '<pre>'
    print >> os, escape(doctree_str)
    print >> os, '</pre>'
    print >> os, '<hr/>'
    print >> os, '<a name="source"/><h2>Source</h2>'
    print >> os, '<pre>'
    print >> os, escape(src['source'].encode('utf-8'))
    print >> os, '</pre>'
    print >> os, '<hr width="5"/>'
    print >> os, pages_footer
    return os.getvalue()


#-------------------------------------------------------------------------------
#
def render_html( unid, uri, username, srcstore ):
    """
    Render the document tree naively, as HTML.

    Note: this is just for fun.  You should develop your own rendering
    interface, possibly modifying the document tree before rendering it.
    """
    sr = srcstore.get(username, [unid], ('doctree',))
    assert len(sr) == 1
    src = sr[0]
    doctree = src['doctree']

    os = StringIO.StringIO()
    if doctree is None:
        print >> os, 'Content-type:', 'text/plain'
        print >> os
        print >> os, '(No document tree in sources upload.)'
        return os.getvalue()

    scheme, netloc, path, parameters, query, fragid = urlparse.urlparse(uri)

    settings = {'embed_stylesheet': False,
                'output_encoding': 'UTF-8'}

    parts = docutils.core.publish_parts(
       reader_name='doctree', source_class=docutils.io.DocTreeInput,
       source=doctree, source_path='test',
       writer_name='html', settings_overrides=settings)

    print >> os, pages_header
    print >> os, navig(uri, unid)
    os.write(parts['html_body'].encode('UTF-8'))
    print >> os, pages_footer
    return os.getvalue()

#-------------------------------------------------------------------------------
#
def render_extracted( unid, stored_unid, uri, username, conn, tables ):
    """
    Render information that was extracted from this document.

    Note: this is just for fun.  You should develop your own rendering
    interface, possibly modifying the document tree before rendering it.
    """

    os = StringIO.StringIO()
    print >> os, pages_header
    if unid is None:
        print >> os, navig_index(uri)
    else:
        print >> os, navig(uri, unid)
    print >> os, '<h1>Extracted Information</h1>'

    for tablename in tables:
        os.write(dump_table(conn, tablename, uri, unid, stored_unid))

    print >> os, pages_footer
    return os.getvalue()

#-------------------------------------------------------------------------------
#
def dump_table( conn, tablename, uri, unid=None, stored_unid=None ):
    """
    Print extracted information (again, for fun, this is not necessary).
    Try to print the extracted info in a generic way.

    If 'user' is specified, filter by that user.
    """
    os = StringIO.StringIO()
    print >> os, '<h2>Table: %s</h2>' % tablename

    curs = conn.cursor()
    query, conds = "SELECT * FROM %s" % tablename, []
    if unid is not None:
        conds.append("unid = '%s'" % stored_unid)
    if conds:
        query += ' WHERE ' + ' AND '.join(conds)
    curs.execute(query)

    if curs.rowcount > 0:
        print >> os, '<table class="nabu">'
        print >> os, '<thead><tr>'
        unidcol = None
        for i, colname in enumerate(curs.description):
            if colname[0] == 'unid':
                unidcol = i
                if unid is not None:
                    continue
            print >> os, '<th>%s</th>' % colname[0]
        print >> os, '</tr></thead>'
        print >> os, '<tbody>'

        for row in curs.fetchall():
            print >> os, '<tr>'
            for i, value in enumerate(row):
                if i == unidcol:
                    if unid is not None:
                        continue
                    else:
                        value = '<a href="%s?id=%s">%s</a>' % (uri, value, value)

                elif isinstance(value, str) and len(value) > 100:
                    value = value[:30]
                print >> os, '<td>%s</td>' % value
            print >> os, '</tr>'

        print >> os, '</tbody>'
        print >> os, '</table>'

    return os.getvalue()
