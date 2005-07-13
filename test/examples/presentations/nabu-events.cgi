#!/usr/bin/env python
# -*- coding: iso-8859-1 -*-
#
# $Id$
#

"""
Test dumper for list of events.
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
from nabu.extractors.event import Event

def main():
    user = os.environ.get('REMOTE_USER', None)

    uri = os.environ['SCRIPT_URI']
    scheme, netloc, path, parameters, query, fragid = urlparse.urlparse(uri)

    # connect to the database
    params = {
        'db': 'nabu',
        'user': 'nabu',
        'passwd': 'pwnabu',
        'host': 'localhost',
    }
    connection = PostgresConnection(**params)
    Event._connection = connection
    
    print 'Content-Type:', 'text/html'
    print 
    print '<html><body>'
    print '<h1>Events</h1>'
    
    allevents = list(Event.select())
    allevents.sort(lambda x, y: cmp(x.date, y.date))
    allevents.reverse()
    print '<ul>'
    for ev in allevents:
        print '<li><b>%s</b>: %s</li>' % (ev.date, ev.description)
    print '</ul>'
    print '</body></html>'


if __name__ == '__main__':
    main()

