#!/usr/bin/env python
#
# $Source$
# $Id$
#

"""
Nabu reStructuredText Reader Extractor.

Usage:
   publish [<options>] <dir-or-file> [<dir-or-file> ...]

This program read some input text files, identifies and extracts meaningful
information chunks from them, such as addresses and contact info, bookmarks and
links, quotes, and much more.  The goal is for the automatic extraction and
classification of this information in order to publish it in a database, on top
of which various specialized views can be made available.

We want this extraction and publication system to work incrementally, to speed
up the process.  Also, the organization of the source files should be
independent of the organization of the data in the database.

For more details, see the design document that comes with Nabu.

Configuration
-------------

All options can be set in a ~/.naburc file (or in the file pointed by the NABURC
environment variable).  You must at least specify the server url somehow.

Note: you can use the option to clear the database on its own to clean it up
without pushing new files to the server.
"""

## Design Note About Dependencies
## ------------------------------
## We want to make it so that the find_to_publish algorithm fits inside this
## file, so that we can distribute just a single script file with no libraries
## to setup or install, at least for those who will not process locally.  The
## reason is that it's really just much simpler to demo or setup for other
## people.  However, it the user wants to process locally, we require an install
## of the nabu system; this is where we draw the line.

# stdlib imports
import sys, os, re, md5, xmlrpclib
from os.path import isdir, isfile, islink, join, exists
from pprint import pprint, pformat ## FIXME remove

#-------------------------------------------------------------------------------
# Main
#-------------------------------------------------------------------------------

def publish():
    """
    Main program of publisher client.
    """
    try: # set the locale to the user settings.
        import locale
        locale.setlocale(locale.LC_ALL, '')
    except:
        pass

    opts, args = parse_options()

    server = None

    # clear the database if requested.
    if opts.clear:
        # create server lazily, because we might not have any candidates.
        if server is None:
            server = xmlrpclib.ServerProxy(opts.server_url, allow_none=1)

        if opts.verbose:
            print '== clearing database.'
        server.dumpdb()

    # find candidate files to consider
    candidates = find_to_publish(args, opts.recursive, opts.verbose)

    if not candidates:
        if opts.verbose:
            print >> sys.stderr, '(no local files to visit.)'
        return

    # create server lazily, because we might not have any candidates.
    if server is None:
        server = xmlrpclib.ServerProxy(opts.server_url, allow_none=1)

    # check candidates against history (if not suppressed)
    if opts.force:
        proclist = candidates
    else:
        idhistory = server.gethistory([x.unid for x in candidates])

        # compare digests and figure out which files to process
        proclist = []
        for candidate in candidates:
            try:
                hist_digest = idhistory[candidate.unid]
            except KeyError:
                hist_digest = None

            if candidate.digest != hist_digest:
                proclist.append(candidate)

    # process selected files
    for pfile in proclist:
        if opts.process_locally:
            # Local processing.
            # This is used to validate the files before sending them.
            # Note: here we require a Nabu install
            try:
                import nabu.process
            except ImportError:
                raise SystemExit(
                    "Error: you must have installed Nabu in order to "
                    "process files locally.")
                    
            contents_uni = pfile.contents.decode('utf-8')
            entries = nabu.process.process_source(contents_uni)

        # FIXME eventually we will want to send the processed data to the server
        # because it is already parsed!
        print '== sending to server:', pfile.fn
        server.process_file(pfile.unid, pfile.fn,
                            xmlrpclib.Binary(pfile.contents))

#-------------------------------------------------------------------------------
# Config / Command-line
#-------------------------------------------------------------------------------

def parse_options():
    """
    Parse the command-line and config file options and return a pair of opts,
    args like optparse.
    """
    # define the list of options
    import optparse
    parser = optparse.OptionParser(__doc__.strip())

    parser.add_option('-v', '--verbose', action='store_true',
                      help="Increase verbosity")

    parser.add_option('-N', '--no-recurse', '--dont-recurse',
                      action='store_false', dest='recursive', default=True,
                      help="Disable recursion for directories.")

    parser.add_option('-s', '--server-url', action='store',
                      help="URL to server handler.")

    parser.add_option('-f', '--force', action='store_true',
                      help="Force sending/processing all files regardless "
                      "of history.")

    parser.add_option('-l', '--process-locally', action='store_true',
                      help="Process documents in the publisher.")
    
    parser.add_option('-u', '--user', action='store',
                      help="Username to use to publish.")
    parser.add_option('-p', '--password', action='store',
                      help="Password to use to publish (will query if not set).")
    
    parser.add_option('-c', '--clear', '--clean', action='store_true',
                      help="Clear the entire contents database "
                      "before publishing the new files.")

    # parse config file, if present
    try:
        rcfile = os.environ['NABURC']
    except KeyError:
        rcfile = join(os.environ['HOME'], '.naburc')

    if not exists(rcfile):
        values = None
    else:
        values = parser.get_default_values()
        values.read_file(rcfile) # this reads the config file as Python
    
    # parse command-line (takes precedence over config file)
    opts, args = parser.parse_args(values=values)

    if opts.server_url is None:
        raise SystemExit("Error: you must specify a server url.")
        
    return opts, args

#-------------------------------------------------------------------------------
# Finder
#-------------------------------------------------------------------------------

class File:
    """
    Struct to hold information about a candidate.
    """
    def __init__( self, fn, unid, digest, contents ):
        self.fn = fn
        self.unid = unid
        self.digest = digest
        self.contents = contents
   
codingre = re.compile('.*-\\*-\s*coding:\s*(\S+)\s*.*-\\*-')

def find_to_publish( fnordns, recurse=True, verbose=False ):
    """
    Discover files, figure out which ones are candidates to be processed, and
    returns a list of those objects.  'fnordns' is a list of files
    and/directories to look into.
    """
    # process files.
    candidates = []
    for fn in process_dirs_or_files(fnordns, recurse):
        if verbose:
            print '== reading...', fn

        # read the beginnings of the file
        f = open(fn)
        header = f.read(2048)

        # find if it should be published
        unid = has_publish_marker(header)
        if not unid:
            f.close()
            continue
        
        # we publish it
        if verbose:
            print '   publish id: {%s}' % unid
            
        # read the rest of the file and compute md5 contents
        contents_enc = header + f.read()
        f.close()
        
        # decode into Unicode, try to guess which format, if we cannot guess,
        # assume Latin-1
        mo = codingre.match(contents_enc)
        if mo:
            encoding = mo.group(1)
        else:
            encoding = 'latin-1'

        try:
            contents_uni = contents_enc.decode(encoding)
            contents = contents_uni.encode('UTF-8')
        except UnicodeDecodeError, e:
            raise SystemExit( ("Decoding error in file '%s' "
                               "(trying to decode with encoding '%s'): %s") %
                              (fn, encoding, e))
        except UnicodeEncodeError, e:
            raise SystemExit( ("Encoding error in file '%s' "
                               "(trying to encode with encoding '%s'): %s") %
                              (fn, 'UTF-8', e))

        m = md5.new(contents)
        digest = m.hexdigest()

## FIXME remove
##         print contents.decode('utf-8').encode('latin-1', 'replace')

        # Note: for now we keep all the contents in memory, but when the number
        # of files will get large we will want to do something about it.  We
        # will have to decide between making a single network query for all of
        # the unids/files and losing the contents (reading the files to be
        # processed twice), or making many network queries and processing the
        # winning candidate files immediately.
        candidates.append( File(fn, unid, digest, contents) )

    return candidates


pubmarkre = re.compile(':Id:\s*(\S*)', re.M)

def has_publish_marker( text ):
    """
    Returns the unique publish marker in the file, if the given text contains
    the special publish marker within the starting lines of the document.
    """
    mo = pubmarkre.search(text)
    if mo:
        return mo.group(1)
    return None


#-------------------------------------------------------------------------------
# Utils
#-------------------------------------------------------------------------------

def process_dirs_or_files( args, recurse=True ):
    """
    From a list of directories or filenames, yield filenames.
    (This is a generic function and you can reuse it in other places.)
    """
    for arg in args:
        if isdir(arg):
            if recurse:
                fgen = os.walk(arg)
            else:
                dirs, files = [], []
                for fn in os.listdir(arg):
                    if isdir(fn):
                        dirs.append(fn)
                    else:
                        files.append(fn)
                fgen = ((arg, dirs, files),)

            for root, dirs, files in fgen:
                for fn in files:
                    yield join(root, fn)
        elif isfile(arg) or islink(arg):
            yield arg


if __name__ == '__main__':
    publish()
