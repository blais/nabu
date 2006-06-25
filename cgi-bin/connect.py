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
import sys

# dbapi imports
import psycopg2 as dbapi


def connect_dbapi():
    """
    Connects to the database using a DBAPI-2.0 compliant connection and returns
    a (module, connection) pair.
    """
    # connect to the database
    params = {
        'database': 'nabudemo',
        'user': 'nabudemo',
        'password': '$nabudemo',
        'host': 'localhost',
    }
    try:
        conn = dbapi.connect(**params)
    except dbapi.Error, e:
        print 'Content-type:', 'text/plain'
        print 'Status: 500 Could not connect to server.'
        print
        sys.exit(1)
        
    return dbapi, conn

