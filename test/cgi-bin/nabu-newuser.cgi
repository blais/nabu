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
import os, string, random, crypt, gdbm
from os.path import join
import cgi

#---------------------------------------------------------------------------
#
def crypt_pass( plpass ):
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
    user, passwd = map(form.getvalue, ("user", "passwd"))
    if user is None and passwd is None:
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
        print '<tr>'
        print '<td>Password:<input name="passwd"></input></td>'
        print '</tr>'
        print '<tr><td><input type="submit" value="Create"></input></td></tr>'
        print '</table>'
        print '</body></html>'
    else:
        passwd_file = join(os.environ['DOCUMENT_ROOT'],
                           'webcache', 'nabu', 'passwddbm')
        cpasswd = crypt_pass(passwd)

        # DBM auth.
        dbm = gdbm.open(passwd_file, 'c')
        dbm[user] = cpasswd
        dbm.close()

        print 'Content-type:', 'text/html'
        print
        print '<html><body>'
        print '<h1>User %s created.</h1>' % user
        print '</body></html>'

if __name__ == '__main__':
    main()

