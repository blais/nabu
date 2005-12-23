#!/usr/bin/env python
#
# Copyright (C) 2005  Martin Blais <blais@furius.ca>
# This file is distributed under the terms of the GNU GPL license.
# For more information: http://furius.ca/nabu.
#

"""
Nabu content dumper.

This is a CGI script that is meant to be invoked from a browser to debug/dump
the contents of the uploaded sources.  This is NOT meant as a presentation
layer, this is really just for debugging stuff.
"""

# stdlib imports
import sys, os, urlparse
from os.path import dirname, join
import cgi, cgitb; cgitb.enable()
from pprint import pformat

# add the nabu libraries to load path
root = dirname(dirname(sys.argv[0]))
sys.path.append(join(root, 'lib', 'python'))

# nabu imports
from nabu import sources, contents, extract

# local cgi directory imports.
import connect


ctype = 'Content-Type: text/html; charset=UTF-8\n\n'
admins = ['admin'] # Administrator see all datasets.

def main():
    """
    CGI handler for debugging/dumping the contents of the source upload.
    """
    user = os.environ.get('REMOTE_USER', None)

    uri = os.environ['SCRIPT_URI']
    scheme, netloc, path, parameters, query, fragid = urlparse.urlparse(uri)

    # Connect to the database.
    module, conn = connect.connect_dbapi()

    # Get access to source storage.
    src = sources.DBSourceStorage(module, conn)

    # Restrict by user, unless we're the administrator.
    if user not in admins:
        src = sources.PerUserSourceStorageProxy(src)

    tablenames = ('document', 'link', 'event', 'contact', 'reference', 'book')

    form = cgi.FieldStorage()
    view = form.getvalue("view")
    unid = form.getvalue("id")

    if not unid:
        print ctype
        if view == 'extracted':
            print contents.render_extracted(None, None, uri, user, conn, tablenames)
        else:
            print contents.render_index(uri, user, src)
        return

    # Check if the source exists.
    ulist = src.get(user, [unid], ('unid',))
    if len(ulist) != 1:
        # Return error message if not.
        return contents.render_notfound()
        

    # Render an appropriate view.
    if not view:
        view = 'source' # default.

    if view == 'source':
        print ctype
        print contents.render_source(unid, uri, user, src)

    elif view == 'html':
        print ctype
        print contents.render_html(unid, uri, user, src)

    elif view == 'extracted':
        stored_unid = src.map_unid(unid, user)
        print ctype
        print contents.render_extracted(unid, stored_unid,
                                        uri, user, conn, tablenames)

    else:
        print contents.render_notfound()

if __name__ == '__main__':
    main()

