#!/usr/bin/env python
# -*- coding: iso-8859-1 -*-
#
# $Id$
#

"""
Nabu test content dumper.

This is a CGI script that is meant to be invoked from a browser to debug/dump
the contents of the uploaded sources.
"""

# stdlib imports
import sys, os, urlparse
from os.path import dirname, join
import cgi, cgitb; cgitb.enable()

# add the nabu libraries to load path
root = dirname(dirname(sys.argv[0]))
sys.path.append(join(root, 'lib', 'python'))

# sqlobject imports
from sqlobject.postgres.pgconnection import PostgresConnection

# nabu imports
from nabu import sources, contents, extract

def main():
    """
    CGI handler for debugging/dumping the contents of the source upload.
    """
    user = os.environ.get('REMOTE_USER', None)

    uri = os.environ['SCRIPT_URI']
    scheme, netloc, path, parameters, query, fragid = urlparse.urlparse(uri)

    # connect to the database
    params = {
        'db': 'nabu',
        'user': 'blais',
        'passwd': '$blais',
        'host': 'localhost',
    }
    connection = PostgresConnection(**params)
    src_pp = sources.DBSourceStorage(connection, restrict_user=1)
    src = sources.PerUserSourceStorageProxy(src_pp)

    form = cgi.FieldStorage()
    unid = form.getvalue("id")
    if not unid:
        unid = None
    ashtml = form.getvalue("ashtml")
    if not form.getvalue("extracted"):
        contents.contents_handler(src, uri, user, unid, ashtml)
    else:
        print 'Content-Type:', 'text/html'
        print 
        print '<html><body>'
        print '<h1>Extracted Information</h1>'

        tables = ('document', 'link',)
        for tablename in tables:
            print_extracted(connection, tablename, unid)


def print_extracted( connection, tablename, unid=None ):
    """
    Print extracted information (again, for fun, this is not necessary).
    Try to print the extracted info in a generic way.
    """

    print '<h2>Table: %s</h2>' % tablename
    values, colnames = extract.get_generic_table_values(
        connection, tablename, unid)
    colnames.remove('unid')
    for s in values:
        print '<h3>%s</h3>'% s['unid']
        print '<table>'
        for name in colnames:
            print '<tr><td style="color: #AAA">%s</td><td>' % name
            print s.get(name, '')
            print '</td></tr>'
        print '</table>'
    
    print '</body></html>'

if __name__ == '__main__':
    main()

