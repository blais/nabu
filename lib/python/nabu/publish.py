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
##
## We want to make it so that all to code to publish fits inside this file, so
## that we can distribute just a single script file with no libraries to setup
## or install, at least for those who will not process locally.  The reason is
## that it's really just much simpler to demo or setup for other people.
## However, it the user wants to process locally, we require an install of the
## nabu system; this is where we draw the line.

# stdlib imports
import sys, os, re, md5, xmlrpclib, fnmatch
from os.path import *
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

        # important message, always print.
        print '(clearing entire database.)'
        server.dumpdb()

    # find candidate files to consider
    try:
        candidates = find_to_publish(args, opts)
    except IOError, e:
        raise SystemExit('Error: %s' % e)

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
        if opts.process_locally == 0:
            print '======= sending source document to server:  %s  {%s}' % \
                  (pfile.fn, pfile.unid)

            server.process_source(pfile.unid, pfile.fn, opts.user,
                                  xmlrpclib.Binary(pfile.contents))
            continue
        
        elif opts.process_locally >= 1:
            #
            # Local processing with docutils.
            #
            # Note: we require at least a docutils install.
            # Note2: this assumes that the tree structure is compatible with
            #        that which is installed on the server.
            #
            print '======= processing file locally:  %s' % pfile.fn

            try:
                import docutils.core
            except ImportError:
                raise SystemExit(
                    "Error: you must have installed docutils in order to "
                    "process files locally.")

            doctree, parts = docutils.core.publish_doctree(
                source=pfile.contents,
                settings_overrides={'input_encoding': 'UTF-8'}
                )

## FIXME how do I detect errors here?

            if opts.process_locally == 1:
                print '======= sending parsed document to server: {%s}' % \
                      pfile.unid
                import cPickle as pickle
                docpickled = pickle.dumps(doctree)

                server.process_doctree(pfile.unid, pfile.fn, pfile.digest,
                                       opts.user,
                                       xmlrpclib.Binary(docpickled))

            elif opts.process_locally == 2:
                # do nothing, all we were asked to do is validate and don't send.
                pass

            elif opts.process_locally == 3:
                print ('======= validating file with docutils and "'
                       'extraction:  %s') % pfile.fn
                try:
                    import nabu.process
                    
                    raise NotImplementedError(
                        "Local Nabu validation not implemented yet.")
## FIXME finish extract method in Nabu and call it here and then
##       print out the extracted fields.
##
##                     contents_uni = pfile.contents.decode('utf-8')
##                     entries = nabu.process.process_source(contents_uni)
                except ImportError:
                    raise SystemExit(
                        "Error: you must have installed Nabu in order to "
                        "process files with locally with extraction.")


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

    # finder options
    group = optparse.OptionGroup(parser, "Finder options",
                                 """These options affect how the publisher
                                 finds and recognizes files.""")

    group.add_option('-R', '--no-recurse', '--dont-recurse',
                     action='store_false', dest='recursive', default=True,
                     help="Disable recursion for directories.")
    group.add_option('-r', '--recurse', '--recurse',
                     action='store_true', dest='recursive',
                     help="Disable recursion for directories.")

    group.add_option('-e', '--exclude', action='append', metavar='PATTERN',
                     default=[],
                     help="Ignore files and subdirectories whose basenames "
                     "match the given globbing pattern.  You can append "
                     "many of these options.  Typically you would ignore "
                     "something like ['.svn', 'CVS'].  You do not need to "
                     "bother setting up patterns to ignore binary files, we "
                     "process those very efficiently.")

    group.add_option('--marker-regexp', action='store', metavar='REGEXP',
                     default=':Id:\s+(\S*)',
                     help="Regular expression to search for marker. "
                     "It must contain a single group. Note that the entire "
                     "matched contents may be removed from source.")

    group.add_option('--header-length', action='store', type='int',
                     metavar='LENGTH', default=1024,
                     help="Length of the header (in characters) to look "
                     "for the marker at the top of each file "
                     "(the default is roughly 20 lines).")

    parser.add_option_group(group)

    # server options
    group = optparse.OptionGroup(parser, "Server options",
                                 """These options specify where to upload
                                 the files on the server.""")

    group.add_option('-s', '--server-url', action='store', metavar='URL',
                      help="URL to server handler.")

    group.add_option('-u', '--user', action='store',
                      help="Username to use to publish.")

    group.add_option('-p', '--password', action='store', metavar='PASSWD',
                      help="Password to use to publish (will query if not set).")

    parser.add_option_group(group)

    # processing options
    group = optparse.OptionGroup(parser, "Processing options",
                                 """These options specify where to upload
                                 the files on the server.""")

    group.add_option('-c', '--clear', '--clean', action='store_true',
                      help="Clear the entire contents database "
                      "before publishing the new files.")

    group.add_option('-f', '--force', action='store_true',
                     help="Force sending/processing all files regardless "
                     "of history.")

    group.add_option('-l', '--process-locally', '--local',
                     action='count', default=0,
                     help="Process documents locally.  If you omit the option, "
                     "the documents get sent to and processed on the server "
                     "(this is the default).  If you specify it once, the "
                     "documents get processed locally and the results gets sent "
                     "to the server;  twice is for validation, the "
                     "documents get processed locally but do not get sent to "
                     "the server;  three times is for debugging only: local "
                     "extraction of Nabu entries is attempted by the local "
                     "installation of Nabu.")

    group.add_option('--dont-remove-marker', '--leave-marker',
                     action='store_true',
                     help="Leave the markers in the source files when uploading. "
                     "You would use this if it makes sense for the markers "
                     "appear in your published documents somehow.")

    parser.add_option_group(group)

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
        parser.error("You must specify a server url.")

    # compile regular expression
    try:
        opts.marker_regexp = re.compile(opts.marker_regexp, re.M)
    except re.error, e:
        parser.error("Compiling marker regexp: %s" % str(e))

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

def find_to_publish( fnordns, opts ):
    """
    Discover files, figure out which ones are candidates to be processed, and
    returns a list of those objects.

    :Parameters:
       - `fnordns`: is a list of files and/directories to look into.
       - `opts`: program options.
    """
    # process files.
    candidates = []
    fileids = set()
    files = set()
    for fn in process_dirs_or_files(fnordns, opts.exclude, opts.recursive):
        afn = abspath(normpath(fn))
        if afn in files:
            print >> sys.stderr, \
                  "Warning: Skipping file '%s' that was seen twice." % fn
            continue
        files.add(afn)

        if opts.verbose:
            print '======= reading...', fn

        # read the beginnings of the file
        f = open(fn)
        header = f.read(opts.header_length)

        # find if it should be published
        mo = opts.marker_regexp.search(header)
        if mo:
            unid = mo.group(1)

            # if the marker was partially cut by the header being too short,
            # don't publish (we don't know if we have the entire marker).
            if mo.end() == opts.header_length:
                print >> sys.stderr, \
                      ("Warning: Skipping file '%s' with marker found at " \
                       "header boundary: '%s'.") % (fn, unid)
                continue
        else:
            f.close()
            continue

        # remove the marker found from the file
        if not opts.dont_remove_marker:
            header = header[:mo.start()] + header[mo.end():]

        # check if the id has been seen before in another input file
        if unid in fileids:
            print >> sys.stderr, \
                  "Warning: Skipping file '%s' with duplicate id: '%s'." % \
                  (fn, unid)
            continue
        fileids.add(unid)

        # we publish it
        if opts.verbose:
            print '======= publish id: {%s}' % unid

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

        # Note: for now we keep all the contents in memory, but when the number
        # of files will get large we will want to do something about it.  We
        # will have to decide between making a single network query for all of
        # the unids/files and losing the contents (reading the files to be
        # processed twice), or making many network queries and processing the
        # winning candidate files immediately.
        candidates.append( File(fn, unid, digest, contents) )

    return candidates


#-------------------------------------------------------------------------------
# Utils
#-------------------------------------------------------------------------------

def exclude_list( names, exclude ):
    """
    Returns a list of the names which do not match any of the given exclude
    patterns.
    """
    newnames = []
    for n in names:
        for excl in exclude:
            if fnmatch.fnmatch(n, excl):
                break
        else:
            newnames.append(n)
    return newnames

def process_dirs_or_files( args, exclude=[], recurse=True, ignore_error=False ):
    """
    From a list of directories or filenames, yield filenames.
    (This is a generic function and you can reuse it in other places.)
    """
    # first check for existence of the given files
    if not ignore_error:
        missing = filter(lambda x: not exists(x), args)
        if missing:
            raise IOError("files or directories do not exist: %s" %
                          ', '.join(missing))
                
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
                if exclude:
                    dirs[:] = exclude_list(dirs, exclude)
                    files[:] = exclude_list(files, exclude)
                for fn in files:
                    yield join(root, fn)
        elif isfile(arg) or islink(arg):
            if exclude and not exclude_list([arg], exclude):
                continue
            yield arg

if __name__ == '__main__':
    publish()
