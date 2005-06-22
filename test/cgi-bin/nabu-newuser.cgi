#!/usr/bin/env python
# -*- coding: iso-8859-1 -*-
#
# $Source$
# $Id$
#

"""
User creation script for test Nabu install.

This simplistic script allows users to create user/password pairs to test the
Nabu system. This is only meant to be used for demo purposes.
"""

# stdlib imports
from pprint import pprint, pformat
import sys, os, urlparse, string, random, crypt
from os.path import dirname, join
import cgi, cgitb; cgitb.enable()
import cPickle as pickle


#---------------------------------------------------------------------------
#
def crypt_pass( self, plpass ):
    """Crypt password for htpasswd file."""
    saltchoice = string.ascii_letters + string.digits
    salt = ''.join([random.choice(saltchoice) for x in xrange(2)])
    cpass = crypt.crypt(plpass, salt)
    return cpass

#-------------------------------------------------------------------------------
#
def main():
    """
    CGI handler. 
    """
    form = cgi.FieldStorage()
    user = map(form.getvalue, ("user", "pass"))
    if user is None and pass is None:
        # generate an index of documents.
        print 'Content-type:', 'text/html'
        print
        print '<html><body>'
        print '<h1>Create new user:</h1>'
        print '<form action="%s" method="POST" name="create">' % \
              os.environ['SCRIPT_URI']
        print '<table>'
            print '<tr>'
            print '<td>Username:<input name="user"></input></td>'
            print '</tr>'
        print '</table>'
        print '</body></html>'
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

    # render document in HTML
    scheme, netloc, path, parameters, query, fragid = \
            urlparse.urlparse(os.environ['SCRIPT_URI'])
    settings = {'stylesheet': '%s://%s/docutils-style.css' % (scheme, netloc),
                'output_encoding': 'UTF-8'}

    output = docutils.core.publish_from_doctree(
        document, writer_name='html4css1', settings_overrides=settings)

    print 'Content-type:', 'text/html'
    print
    print output


if __name__ == '__main__':
    main()
