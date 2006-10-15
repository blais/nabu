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

  ***IMPORTANT*** This is an EXAMPLE ONLY.  You should setup your own customized
     version of this script, or something similar.  You basically need to setup
     a publisher URL within your favourite web app framework and call the Nabu
     server handler method as done below, with the set of extractors that
     ***YOU** want to run.

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
from nabu.extractors import document, doctree
from nabu.extractors import link, contact, event, reference, book

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
    src_pp = sources.DBSourceStorage(module, conn)
    src = sources.PerUserSourceStorageProxy(src_pp)

    transforms = (
        (document.Extractor, document.Storage(module, conn)),
        (doctree.Extractor, doctree.Storage(module, conn)),
        (event.Extractor, event.Storage(module, conn)),
        (contact.Extractor, contact.Storage(module, conn)),
        (reference.Extractor, reference.Storage(module, conn)),
        (link.Extractor, link.Storage(module, conn)),
        (book.Extractor, book.Storage(module, conn)),
        )

    server_handler = server.create_server(src, transforms, username, allow_reset=1)
    server.xmlrpc_handle_cgi(server_handler)

if __name__ == '__main__':
    main()

