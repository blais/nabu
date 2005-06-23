#!/usr/bin/env python
# -*- coding: iso-8859-1 -*-
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

# add the nabu libraries to load path
root = dirname(dirname(sys.argv[0]))
sys.path.append(join(root, 'lib', 'python'))


# nabu and other imports
from sqlobject.postgres.pgconnection import PostgresConnection
from nabu import server
from nabu.utils import ExceptionXMLRPCRequestHandler

def main():
    """
    CGI handler for XML-RPC server.
    """
    # connect to the PostgreSQL database
    params = {
        'db': 'nabu',
        'user': 'blais',
        'passwd': '$blais',
        'host': 'localhost',
    }
    connection = PostgresConnection(**params)

    # note: make sure we're authenticated
    username = os.environ.get('REMOTE_USER', None)
    
    # create an XMLRPC server handler and bind methods
    server_handler = server.ServerHandler(connection, username)
    handler = ExceptionXMLRPCRequestHandler()
    handler.register_instance(server_handler)
    handler.handle_request()
    
if __name__ == '__main__':
    main()
