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
import sys, os
from os.path import dirname, join
import cgi, cgitb; cgitb.enable()
import cPickle as pickle

# add the nabu libraries to load path
root = dirname(dirname(sys.argv[0]))
sys.path.append(join(root, 'lib', 'python'))

# nabu and other imports
from sqlobject.postgres.pgconnection import PostgresConnection
from nabu.server import init_connection, Document

# docutils imports
import docutils.io
import docutils.utils
import docutils.writers.html4css1
from docutils.frontend import OptionParser

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
    if unid is None:
        # generate an index of documents.
        linkfmt = '%s?id=%%s' % os.environ['SCRIPT_URI']
        print 'Content-type:', 'text/html'
        print
        print '<html><body>'

        print '<h1>Document</h1>'
        print '<ul>'
        sr = Document.select()
        for s in sr:
            print '<li><a href="%s">%s</a></li>' % (linkfmt % s.unid, s.unid)
        print '</ul>'
        return

    # select the document from the database
    sr = Document.select(Document.q.unid==unid)
    if sr.count() == 0:
        print 'Content-type:', 'text/plain'
        print 'Status: 404 Document Not Found.'
        print
        print 'Document not found'
        return

    # read and document and unpickle it
    doc = sr[0]
    document = pickle.loads(sr[0].contents)

    # create writer and destination
    writer = docutils.writers.html4css1.Writer()
    destination = docutils.io.StringOutput(encoding='UTF-8')

    # setup settings for writer
    option_parser = OptionParser( components=(writer,),
                                  defaults={}, read_config_files=0)
    document.settings = option_parser.get_default_values()

    # create a reporter
    document.reporter = docutils.utils.Reporter(
        '<string>',
        document.settings.report_level,
        document.settings.halt_level,
        stream=document.settings.warning_stream,
        debug=document.settings.debug,
        encoding=document.settings.error_encoding,
        error_handler=document.settings.error_encoding_error_handler)
    ## source <string>, report_level 2, halt_level 4, stream None
    ## debug None, encoding ascii, error_handler backslashreplace
    
    output = writer.write(document, destination)
    writer.assemble_parts()

    print 'Content-type:', 'text/html'
    print
    print output

##     output = self.writer.write(document, self.destination)
##     self.writer.assemble_parts()

if __name__ == '__main__':
    main()

