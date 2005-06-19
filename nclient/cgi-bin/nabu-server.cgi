#!/usr/bin/env python
# -*- coding: iso-8859-1 -*-
#
# $Source$
# $Id$
#

"""
Nabu Server CGI handler.

This is a CGI handler that will pass on the Nabu server requests to the
appropriate server code.  Note that the handler could be implemented using any
web application framework.
"""

# stdlib imports
from pprint import pprint, pformat
import sys
from os.path import dirname, join
import cgi, cgitb
#cgitb.enable(display=0, logdir="/tmp") # for debugging
from SimpleXMLRPCServer import CGIXMLRPCRequestHandler

# add the nabu libraries to load path
root = dirname(dirname(dirname(sys.argv[0])))
sys.path.append(join(root, 'lib', 'python'))

# nabu and other imports
from sqlobject.postgres.pgconnection import PostgresConnection
from nabu import server

#-------------------------------------------------------------------------------
#
def main():
    """
    CGI handler. 
    """
    # connect to the database
    params = {
        'db': 'nabu',
        'user': 'blais',
        'passwd': '$blais',
        'host': 'localhost',
    }
    connection = PostgresConnection(**params)

    # create an XMLRPC server handler and bind methods
    server_handler = server.ServerHandler(connection)
    handler = CGIXMLRPCRequestHandler()
    handler.register_instance(server_handler)
    handler.handle_request()

if __name__ == '__main__':
    main()
