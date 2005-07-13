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
import sys, os, urlparse, random
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
import docutils.core, docutils.io

# nabu imports
from nabu import sources, contents, extract
from nabu.extractors import document, reference


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
    reference.Reference._connection = connection

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

div#main {
  padding: 1em; }

div#categories {
  float: right;
  border: thin dashed #CCC;
  padding: 5px;
}

div#blurb {
  font-size: small; }

div#categories ul {
  list-style: none; }
  
.date {
  font-size: smaller;
  font-weight: bold;
  font-family: Georgia, 'Times New Roman', serif;
  margin-right: 1em; }

td.author {
  font-size: smaller;
  font-style: italic; }

table#docslist {
  margin-left: 2em; }


"""

def render_header():
    print 'Content-Type:', 'text/html'
    print """
<html>
<head>
<link rel="stylesheet" href="/nabu/style-example.css" type="text/css" />
<style type="text/css">
%s
</style>
</head>
<body>

<div id="project-header">
  <a href="/nabu/cgi-bin/nabu-example-presentation.cgi">
  <img src="/nabu/etc/logo-test-nabu.gif" id="logo"></a>
</div>

<div id="main">

""" % css
    
def render_footer():
    print """

</div>
</body></html>
"""

#-------------------------------------------------------------------------------
#
__blurb__ = """
<div id="blurb">
<p>
This is an example presentation for a Nabu-filled database.
It presents the documents uploaded by users,
as if they were blog entries with categories.
(You can put a :Category: bibliographic field in your restructuredtext document
to set the category.)
Just for fun, it also inserts 3 random external links from the whole set of
documents.
You could create much more complex presentations of extraction data using this
framework, but I don't have much time right now to provide a more useful
example.
</p>

<p><b>
Please note that the information uploaded here is provided by anyone currently
testing Nabu and we're not responsible for the contents.
</b></p>
</div>
"""

def render_front_page():
    """
    Prints list of documents uploaded.
    """
    print __blurb__
    print '<h1>Recent Documents</h1>'
    render_categories()
    print '<table id="docslist">'
    documents = list(document.Document.select())
    # reverse sort
    documents.sort(lambda x, y: cmp(y.date, x.date))
    for doc in documents:
        print ('<tr><td><span class="date">%s</span></td>'
               '<td><a href="%s">%s</a></td></tr>') % \
              (escape(str(doc.date)),
               uri + '?method=document&unid=%s' % doc.unid, escape(doc.title))
        print '<tr><td></td><td class="author">%s</td></tr>' % escape(doc.author)
    print '</table>'

    render_random_links()
    
#-------------------------------------------------------------------------------
#
def render_categories():
    """
    Prints a div with a list of categories.
    """

    # get the list of unique categories
    categories = set()
    for c in document.Document.select():
        categories.add(c.category)

    print '<div id="categories">'
    print '<h3>Categories</h3>'
    print '<ul>'
    for c in categories:
        curl = uri + '?category=%s'
        print '<li><a href="%s">%s</a></li>' % (curl % escape(c), escape(c))
    print '</ul>'
    print '</div>'
    


#-------------------------------------------------------------------------------
#
def render_random_links():
    """
    Prints a div with random links.
    """
    print '<div id="random-links">'
    print '<h3>Random 3 Links</h3>'

    refs = reference.Reference.select()
    for i in xrange(3):
        ref = refs[ random.randint(0, refs.count()-1) ]
        print '<a href="%s">%s</a><br/>' % (ref.url, escape(ref.url))
    print '</div>'


#-------------------------------------------------------------------------------
#
def render_document( unid ):
    tree = document.Doctree.byUnid(unid)
    if tree.doctree is not None:
        doctree = pickle.loads(tree.doctree)
        parts = docutils.core.publish_parts(
           reader_name='doctree',
           source_class=docutils.io.DocTreeInput, source=doctree,
           source_path='doctree',
           writer_name='html')
        doctree_str = parts['html_body'].encode('utf-8')
    else:
        doctree_str = ''
        
    print doctree_str
    
if __name__ == '__main__':
    main()


