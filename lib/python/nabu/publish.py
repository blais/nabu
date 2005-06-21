#!/usr/bin/env python
#
# $Source$
# $Id$
#

"""
Nabu reStructuredText Reader Extractor.

Usage::
   nabu [<global-opts>] <cmd> [<cmd-opts>]

Available commands:

   `publish`: Find and publish files that have changed against the database.
              Takes a list of files and/or directories to publish;

   `clean`:   Removes data from the database (by default all data);

   `errors`:  Fetches error messages from previous processing on the server.

This program's publish functionality reads some input text files, identifies and
extracts meaningful information chunks from them, such as addresses and contact
info, bookmarks and links, quotes, and much more.  The goal is for the automatic
extraction and classification of this information in order to publish it in a
database, on top of which various specialized views can be made available.

We want this extraction and publication system to work incrementally, to speed
up the process.  Also, the organization of the source files should be
independent of the organization of the data in the database.

For more details, see the design document that comes with Nabu, or use the
`--help` switch.

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
import optparse
from os.path import *
from pprint import pprint, pformat ## FIXME remove

#-------------------------------------------------------------------------------
# Main
#-------------------------------------------------------------------------------

class CmdServerUser:
    """
    Base class for commands that use a server.
    """
    _server = None

    def get_server( self, opts ):
        """
        Create server lazily, because we might not have any candidates.
        """
        if self._server is None:
            self._server = xmlrpclib.ServerProxy(opts.server_url, allow_none=1)
        return self._server

## FIXME add this
## Both the HTTP and HTTPS transports support the URL syntax extension for HTTP
## Basic Authentication: http://user:pass@host:port/path


class CmdFinder:
    """
    Base class for commands that find files.
    """
    def addopts( self, lparser ):
        # finder options
        group2 = optparse.OptionGroup(lparser,
                                      "Publish command finder options",
                                      """These options affect how the publisher
                                      finds and recognizes files.""")

        group2.add_option('-r', '--recurse', '--recurse',
                          action='store_true', dest='recursive', default=True,
                          help="Disable recursion for directories.")

        group2.add_option('-R', '--no-recurse', '--dont-recurse',
                          action='store_false', dest='recursive',
                          help="Disable recursion for directories.")

        group2.add_option('-e', '--exclude', action='append', metavar='PATTERN',
                          default=[],
                          help="Ignore files and subdirectories whose basenames "
                          "match the given globbing pattern.  You can append "
                          "many of these options.  Typically you would ignore "
                          "something like ['.svn', 'CVS'].  You do not need to "
                          "bother setting up patterns to ignore binary files, we "
                          "process those very efficiently.")

        group2.add_option('--marker-regexp', action='store', metavar='REGEXP',
                          default=':Id:\s+(\S*)',
                          help="Regular expression to search for marker. "
                          "It must contain a single group. Note that the entire "
                          "matched contents may be removed from source.")

        group2.add_option('--header-length', action='store', type='int',
                          metavar='LENGTH', default=1024,
                          help="Length of the header (in characters) to look "
                          "for the marker at the top of each file "
                          "(the default is roughly 20 lines).")

        lparser.add_option_group(group2)

    def execute( self, opts, args ):
        # validate options
        try:
            opts.marker_regexp = re.compile(opts.marker_regexp, re.M)
        except re.error, e:
            raise SystemExit("Error: Compiling marker regexp: %s" % str(e))

        # find candidate files to consider
        try:
            if not hasattr(opts, 'dont_remove_marker'):
                opts.dont_remove_marker = True
            self.candidates = find_to_publish(args, opts)
        except IOError, e:
            raise SystemExit('Error: %s' % e)

        if not self.candidates:
            if opts.verbose:
                print >> sys.stderr, '(no local files to visit.)'

class CmdPublish(CmdServerUser, CmdFinder):
    """
    Publish files.
    """
    names = ['publish']

    def addopts( self, lparser ):
        CmdFinder.addopts(self, lparser)

        # processing options
        group3 = optparse.OptionGroup(lparser,
            "Publish command processing options",
            "These options specify where/how to upload or"
            "process the files on the server.")

        group3.add_option('-f', '--force', action='store_true',
                          help="Force sending/processing all files regardless "
                          "of history.")

        group3.add_option('-l', '--process-locally', '--local',
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

        group3.add_option('--dont-remove-marker', '--leave-marker',
            action='store_true',
            help="Leave the markers in the source files when uploading. "
            "You would use this if it makes sense for the markers "
            "appear in your published documents somehow.")

        lparser.add_option_group(group3)

    def execute( self, opts, args ):
        CmdFinder.execute(self, opts, args)
        if not self.candidates:
            return

        # check candidates against history (if not suppressed)
        server = self.get_server(opts)
        if opts.force:
            proclist = self.candidates
        else:
            idhistory = server.gethistory([x.unid for x in self.candidates])

            # compare digests and figure out which files to process
            proclist = []
            for candidate in self.candidates:
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

                errors = server.process_source(pfile.unid, pfile.fn, opts.user,
                                               xmlrpclib.Binary(pfile.contents))
                if errors:
                    print errors
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

                import StringIO
                errstream = StringIO.StringIO()
                doctree, parts = docutils.core.publish_doctree(
                    source=pfile.contents, source_path=pfile.fn,
                    settings_overrides={'input_encoding': 'UTF-8',
                                        'warning_stream': errstream},
                    )
                errors = errstream.getvalue()
                if errors:
                    print >> sys.stderr, errors

                if opts.process_locally == 1:
                    print '======= sending parsed document to server: {%s}' % \
                          pfile.unid
                    import cPickle as pickle
                    docpickled = pickle.dumps(doctree)

                    server.process_doctree(pfile.unid, pfile.fn, pfile.digest,
                                           opts.user,
                                           xmlrpclib.Binary(docpickled))

                elif opts.process_locally == 2:
                    # do nothing, all we were asked to do is validate and don't
                    # send.
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

class CmdClear(CmdServerUser, CmdFinder):
    """
    Clear/remove stuff in the database.
    """
    names = ['clear', 'dump', 'clean']

    def addopts( self, lparser ):
        CmdFinder.addopts(self, lparser)
        lparser.add_option('--found-only', action='store_true',
                           help="Only remove documents that were found.")

    def execute( self, opts, args ):
        server = self.get_server(opts)

        if opts.found_only:
            CmdFinder.execute(self, opts, args)
            if not self.candidates:
                return

            idlist = [x.unid for x in self.candidates]
            for iid in idlist:
                print "== clearing {%s}" % iid
            server.clearids(opts.user, idlist)
        else:
            print "== clearing entire database for user '%s'." % opts.user
            server.clearuser(opts.user)


class CmdErrors(CmdServerUser):
    """
    Report parsing errors.
    """
    names = ['errors']

    def execute( self, opts, args ):
        pass

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

        if encoding.lower() in ('utf-8', 'utf8'):
            contents = contents_enc
        else:
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

#-------------------------------------------------------------------------------
# Config / Global Options
#-------------------------------------------------------------------------------

def parse_subcommands( gparser, subcmds, configvars, defcmd=None ):
    """
    Parse given global arguments, find subcommand from given list of subcommand
    objects, parse local arguments and return a tuple of global options,
    selected command object, command options, and command arguments.  Call
    execute() on the command object to run.
    """
    # build map of name -> command
    subcmds_map = {}
    for sc in subcmds:
        for n in sc.names:
            assert n not in subcmds_map
            subcmds_map[n] = sc

    # parse global options.
    for option in gparser._get_all_options():
        if option.dest in configvars:
            gparser.defaults[option.dest] = configvars[option.dest]

    gparser.disable_interspersed_args()
    opts, args = gparser.parse_args()
    if not args:
        if defcmd is None:
            gparser.print_help()
            raise SystemExit("Error: you must specify a command to use.")
        else:
            args.insert(0, None) # later will be caught
    subcmdname, subargs = args[0], args[1:]

    # parse command-local arguments and invoke command.
    try:
        sc = subcmds_map[subcmdname]
    except KeyError:
        if defcmd is None:
            raise SystemExit("Error: invalid command '%s'" % subcmdname)
        else:
            subargs.insert(0, subcmdname)
            sc = subcmds_map[defcmd]

    lparser = optparse.OptionParser(sc.__doc__.strip())
    if hasattr(sc, 'addopts'):
        sc.addopts(lparser)

    for option in lparser._get_all_options():
        if option.dest in configvars:
            lparser.defaults[option.dest] = configvars[option.dest]

    lopts, subsubargs = lparser.parse_args(subargs)
    opts.__dict__.update(lopts.__dict__.iteritems())

    return sc, opts, subsubargs

def parse_options( configvars ):
    """
    Parse the command-line and config file options and return a pair of opts,
    args like optparse.
    """
    # global parser
    parser = optparse.OptionParser(__doc__.strip())

    parser.add_option('-v', '--verbose', action='store_true',
                      help="Increase verbosity")

    # server options
    group1 = optparse.OptionGroup(parser, "Global / Server options",
                                  """These options specify where to upload
                                  the files on the server.""")


    group1.add_option('-s', '--server-url', action='store', metavar='URL',
                      help="URL to server handler.")

    group1.add_option('-u', '--user', action='store',
                      help="Username to use to publish.")

    group1.add_option('-p', '--password', action='store', metavar='PASSWD',
                      help="Password to use to publish (will query if not set).")

    parser.add_option_group(group1)

    subcmds = (CmdPublish(), CmdClear(), CmdErrors(),)
    sc, opts, args = parse_subcommands(parser, subcmds, configvars, 'publish')

    # some server url is necessary
    if opts.server_url is None:
        parser.error("You must specify a server url.")

    return sc, opts, args

def read_config():
    """
    Read, parse and verify values from config file.
    Returns a dictionary of all values read in the file.
    """
    defvars = {}
    try:
        rcfile = os.environ['NABURC']
    except KeyError:
        rcfile = join(os.environ['HOME'], '.naburc')
    if exists(rcfile):
        execfile(rcfile, defvars)
        # FIXME: maybe catch exceptions here.
    return defvars

#-------------------------------------------------------------------------------
# Main Program
#-------------------------------------------------------------------------------

def main():
    """
    Main program of publisher client.
    """
    try: # set the locale to the user settings.
        import locale
        locale.setlocale(locale.LC_ALL, '')
    except:
        pass

    configvars = read_config()
    sc, opts, args = parse_options(configvars)
    return sc.execute(opts, args)


if __name__ == '__main__':
    main()
