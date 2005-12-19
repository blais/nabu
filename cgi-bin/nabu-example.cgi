#!/usr/bin/env python
#
# Copyright (C) 2005  Martin Blais <blais@furius.ca>
# This file is distributed under the terms of the GNU GPL license.
# For more information: http://furius.ca/nabu.
#

"""
Nabu test/prototype presentation application.

This is simple application to demonstrate presentation of some stuff extracted
from the Nabu-filled database, which present a blog-like interface, with other
stuff.  This interface is dependent on the configuration of the publisher,
specifically which of the extractors are running.
"""

# stdlib imports
import sys, os, urlparse, random, datetime
from os.path import dirname, join
import cgi, cgitb; cgitb.enable()
from xml.sax.saxutils import escape
import cPickle as pickle

# add the nabu libraries to load path
root = dirname(dirname(sys.argv[0]))
sys.path.append(join(root, 'lib', 'python'))

# docutils imports
import docutils.core, docutils.io

# local cgi directory imports.
import connect

# (Note: observe that we do not need to import any nabu modules for
# presentation.)


#-------------------------------------------------------------------------------
#
def main():
    """
    CGI handler for debugging/dumping the contents of the source upload.
    """
    user = os.environ.get('REMOTE_USER', None)

    global uri; uri = os.environ['SCRIPT_URI']
    scheme, netloc, path, parameters, query, fragid = urlparse.urlparse(uri)

    # Setup access to the database.
    module, conn = connect.connect_dbapi()

    form = cgi.FieldStorage()
    method = form.getvalue("method")

    render_header()
    
    if not method:
        render_front_page(conn)
    elif method == 'document':
        render_document(conn, form.getvalue("unid"))

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
<meta http-equiv="Content-Type" content="text/html; charset=utf-8" />
<link rel="stylesheet" href="/nabu/style-example.css" type="text/css" />
<style type="text/css">
%s
</style>
</head>
<body>

<div id="project-header">
  <a href="/nabu/cgi-bin/nabu-example.cgi">
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


#-------------------------------------------------------------------------------
#
def render_front_page( conn ):
    """
    Prints list of documents uploaded.
    """
    print __blurb__
    print '<h1>Recent Documents</h1>'
    render_categories(conn)
    print '<table id="docslist">'

    curs = conn.cursor()
    curs.execute("SELECT unid, date, title, author FROM document")
    if curs.rowcount > 0:
        rows = curs.fetchall()

        # reverse sort
        rows.sort(lambda x, y: cmp(y[1] or datetime.date.min,
                                   x[1] or datetime.date.min))

        for unid, date, title, author in rows:
            print ('<tr><td><span class="date">%s</span></td>'
                   '<td><a href="%s">%s</a></td></tr>') % \
                  (escape(str(date)),
                   uri + '?method=document&unid=%s' % unid,
                   escape(title or ''))
            print ('<tr><td></td><td class="author">%s</td></tr>' %
                   escape(author or ''))
        print '</table>'

    render_random_links(conn)
    
#-------------------------------------------------------------------------------
#
def render_categories( conn ):
    """
    Prints a div with a list of categories.
    """

    # Get the list of unique categories
    curs = conn.cursor()
    curs.execute("SELECT DISTINCT category FROM document")

    categories = set()
    if curs.rowcount > 0:
        categories.update(filter(None, [x[0] for x in curs.fetchall()]))

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
def render_random_links( conn ):
    """
    Prints a div with random links.
    """
    print '<div id="random-links">'
    print '<h3>Random 3 Links</h3>'

    curs = conn.cursor()
    curs.execute("SELECT url FROM reference")
    if curs.rowcount > 0:
        refs = [x[0] for x in curs.fetchall()]
        for i in xrange(3):
            url = random.choice(refs)
            print '<a href="%s">%s</a><br/>' % (url, escape(url))
    print '</div>'


#-------------------------------------------------------------------------------
#
def render_document( conn, unid ):
    assert unid is not None
    
    curs = conn.cursor()
    curs.execute("SELECT doctree FROM doctree WHERE unid = %s", (unid,))
    if curs.rowcount > 0:
        dbdoctree = str(curs.fetchone()[0])
        doctree = pickle.loads(dbdoctree)
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


