#!/usr/bin/env python
# -*- coding: iso-8859-1 -*-
#
# $Source$
# $Id$
#

"""
Nabu test HTML conversion from pickled document.

This script simply attempts to get the pickled document stored in the database
and runs the writer on it to produce the HTML document and returns that.

"""

# stdlib imports
from pprint import pprint, pformat
import sys
from os.path import dirname, join
import cgi, cgitb; cgitb.enable()
import cPickle as pickle

# add the nabu libraries to load path
root = dirname(dirname(dirname(sys.argv[0])))
sys.path.append(join(root, 'lib', 'python'))

# nabu and other imports
from sqlobject.postgres.pgconnection import PostgresConnection
from nabu.server import init_connection, Document

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

    init_connection(connection)

    form = cgi.FieldStorage()
    unid = form.getvalue("id")
    sr = Document.select(Document.q.unid==unid)
    if sr.count() == 0:
        print 'Status: 404 Document Not Found.'
        print
        return

    doc = sr[0]
    doctree = pickle.loads(sr[0].contents)
    print 'Content-type:', 'text/plain'
    print
    print doctree
    


if __name__ == '__main__':
    main()
