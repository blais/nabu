#!/usr/bin/env python
#
# Copyright (C) 2005  Martin Blais <blais@furius.ca>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.
#

"""
Nabu Extractor Tester.

Usage::
   nabu [<options>] <extractor-py-file> <source-document> [<source-document> ...]

Simple program that can be used to test an extractor.  The idea is that we
simply process the document into its document tree and run the first extractor
class that is found in the given file on it, using a storage object that only
prints out the results.  This allows us to quickly find out if our extractors
are working without a server setup (not that that's hard to check with a server
install, but I'm just a sucker for quick testing, and this is one more step
towards it, and other people might enjoy this as well, without having to tweak
their server for debug output generation).
"""

__version__ = '$Revision$'
__author__ = 'Martin Blais <blais@furius.ca>'

# stdlib imports
import sys, os, re, md5, xmlrpclib, fnmatch, urlparse, imp
import optparse
from os.path import *

if sys.version_info[:2] < (2, 3):
    raise SystemExit("Error: you need Python >=2.3 to run this program.")

if sys.version_info[:2] < (2, 4):
    from sets import Set as set


def load_extractor( fn ):
    """
    Imports the extractor module and returns an extractor class found in it.
    """

    try:
        __import__

    fp, pathname, description = imp.find_module(name)
    
    try:
        fp = file(extractorfn)
        print imp.load_module('extractor', fp, extractorfn, '')
    finally:
        # Since we may exit via an exception, close fp explicitly.
        if fp:
            fp.close()        



#-------------------------------------------------------------------------------
# Main Program
#-------------------------------------------------------------------------------

def main():
    """
    Main program for extractor tester.
    """
    try: # set the locale to the user settings.
        import locale
        locale.setlocale(locale.LC_ALL, '')
    except:
        pass

    # parse/validate arguments
    import optparse
    parser = optparse.OptionParser(__doc__.strip())
    opts, args = parser.parse_args()

    opts, args = parse_options()
    if len(args) < 2:
        parser.error("You must specify the extractor source file and a list "
                     "of source rest documents to test it with.")
    extractorfn, docfns = args[0], args[1:]

    # load the extractor code.
    


    








if __name__ == '__main__':
    main()


