#!/usr/bin/env python
#
# Copyright (C) 2005  Martin Blais <blais@furius.ca>
# This file is distributed under the terms of the GNU GPL license.
# For more information: http://furius.ca/nabu.
#
# $Id$
#

"""
Nabu test/prototype presentation application.

This is simple application to demonstrate presentation of some stuff extracted
from the Nabu-filled database, which present a blog-like interface, with other
stuff.  This interface is dependent on the configuration of the publisher,
specifically which of the extractors are running.
"""

# stdlib imports
import sys, os, urlparse
from os.path import dirname, join
import cgi, cgitb; cgitb.enable()
from xml.sax.saxutils import escape
import cPickle as pickle

# add the nabu libraries to load path
root = dirname(dirname(sys.argv[0]))
sys.path.append(join(root, 'lib', 'python'))

# sqlobject imports
from sqlobject.postgres.pgconnection import PostgresConnection
from sqlobject import SQLObjectNotFound

# docutils imports
import docutils.core

# nabu imports
from nabu import sources, contents, extract
from nabu.extractors import document


def main():
    """
    CGI handler for debugging/dumping the contents of the source upload.
    """
    user = os.environ.get('REMOTE_USER', None)

    global uri; uri = os.environ['SCRIPT_URI']
    print >> sys.stderr, uri
    scheme, netloc, path, parameters, query, fragid = urlparse.urlparse(uri)

    # connect to the database
    params = {
        'db': 'nabu',
        'user': 'nabu',
        'passwd': 'pwnabu',
        'host': 'localhost',
    }
    connection = PostgresConnection(**params)
    src_pp = sources.DBSourceStorage(connection, restrict_user=1)
    src = sources.PerUserSourceStorageProxy(src_pp)

    document.Doctree._connection = connection
    document.Document._connection = connection

    form = cgi.FieldStorage()
    method = form.getvalue("method")

    render_header()
    
    if not method:
        render_front_page()
    elif method == 'document':
        render_document( form.getvalue("unid") )

    render_footer()

#-------------------------------------------------------------------------------
#
css = """

.date { font-size: smaller; font-style: italic; }

"""

def render_header():
    print 'Content-Type:', 'text/html'
    print """
<html>
<head>
<link rel="stylesheet" href="/docutils-style.css" type="text/css" />
<style type="text/css">
%s
</style>
</head>
<body>
""" % css
    
def render_footer():
    print '</body></html>'

#-------------------------------------------------------------------------------
#
def render_front_page():
    # get list of documents uploaded
    print '<h1>Documents</h1>'
    print '<ul>'
    for doc in document.Document.select():
        print ('<li><a href="%s">%s</a> (%s) &nbsp; '
               '<span class="date">%s</span></li>') % \
              (uri + '?method=document&unid=%s' % doc.unid,
               escape(doc.title), escape(doc.author), escape(str(doc.date)))
    print '</ul>'

#-------------------------------------------------------------------------------
#
def render_document( unid ):
    tree = document.Doctree.byUnid(unid)
    if tree.doctree is not None:
        doctree_str, parts = docutils.core.publish_from_doctree(
            pickle.loads(tree.doctree), writer_name='html',
            settings_overrides={'output_encoding': 'UTF-8'})
    else:
        doctree_str = ''
        
    print doctree_str
    
if __name__ == '__main__':
    main()

