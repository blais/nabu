#!/usr/bin/env python
#
# Copyright (C) 2005  Martin Blais <blais@furius.ca>
# This file is distributed under the terms of the GNU GPL license.
# For more information: http://furius.ca/nabu.
#

"""
Nabu Server CGI handler.

This is a CGI handler that will pass on the Nabu server requests to the
appropriate server code.  Note that the handler could be implemented using any
web application framework.
"""

# stdlib imports
import sys, os
from os.path import dirname, join
##import cgitb; cgitb.enable(display=0, logdir="/tmp") # for debugging

# add the nabu libraries to load path of our CGI script
root = dirname(dirname(sys.argv[0]))
sys.path.append(join(root, 'lib', 'python'))

# nabu imports
from nabu import server, sources
from nabu.extractors import document, link, contact, event, reference, book

# local cgi directory imports.
import connect


def main():
    """
    CGI handler for XML-RPC server.
    """
    # Connect to the database.
    module, conn = connect.connect_dbapi()

    # make sure we're authenticated
    username = os.environ.get('REMOTE_USER', None)
    if username is None:
        print 'Content-type:', 'text/plain'
        print 'Status: 404 Document Not Found.'
        print
        return
    
    # Get access to source storage.
    src_pp = sources.DBSourceStorage(module, conn, restrict_user=1)
    src = sources.PerUserSourceStorageProxy(src_pp)

    sconnection = connect.connect_sqlobject()
    transforms = (
        (document.DocumentExtractor, document.DocumentStorage(sconnection)),
        (document.DoctreeExtractor, document.DoctreeStorage(sconnection)),
        (link.LinkExtractor, link.LinkStorage(sconnection)),
        (event.EventExtractor, event.EventStorage(sconnection)),
        (contact.ContactExtractor, contact.ContactStorage(sconnection)),
        (reference.ReferenceExtractor, reference.ReferenceStorage(sconnection)),
        (book.BookExtractor, book.BookStorage(sconnection)),
        )

    server.xmlrpc_handler(src, transforms, username, allow_reset=1)
    
if __name__ == '__main__':
    main()

