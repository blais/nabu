#!/usr/bin/env python
#
# Copyright (C) 2005  Martin Blais <blais@furius.ca>
# This file is distributed under the terms of the GNU GPL license.
# For more information: http://furius.ca/nabu.
#
# $Id$
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

# sql imports
from sqlobject.postgres.pgconnection import PostgresConnection

# nabu imports
from nabu import server, sources
from nabu.extractors import document, link, contact, event

def main():
    """
    CGI handler for XML-RPC server.
    """
    # connect to the PostgreSQL database
    params = {
        'db': 'nabu',
        'user': 'nabu',
        'passwd': 'pwnabu',
        'host': 'localhost',
    }
    connection = PostgresConnection(**params)

    # make sure we're authenticated
    username = os.environ.get('REMOTE_USER', None)
    if username is None:
        print 'Content-type:', 'text/plain'
        print 'Status: 404 Document Not Found.'
        print
        return
    
    # create a storage space for the uploaded source data
    src_pp = sources.DBSourceStorage(connection, restrict_user=1)
    src = sources.PerUserSourceStorageProxy(src_pp)

    transforms = (
        (document.DocumentExtractor, document.DocumentStorage(connection)),
        (document.DoctreeExtractor, document.DoctreeStorage(connection)),
        (link.LinkExtractor, link.LinkStorage(connection)),
        (event.EventExtractor, event.EventStorage(connection)),
        (contact.ContactExtractor, contact.ContactStorage(connection)),
        )

    server.xmlrpc_handler(src, transforms, username, allow_reset=1)
    
if __name__ == '__main__':
    main()

