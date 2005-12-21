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
Nabu Publisher Client.

Usage::
   nabu [<options>] [<file-or-dir> ...]

Find files with a specific marker, and publish the files that have changed
against the database using XML-RPC calls over an HTTP connection.  Takes a list
of files and/or directories to publish.  If none is specified, the current
directory is assumed.

This program's publish functionality reads some input text files, identifies and
extracts meaningful information chunks from them, such as addresses and contact
info, bookmarks and links, quotes, and much more.  The goal is for the automatic
extraction and classification of this information in order to publish it in a
database, on top of which various specialized views can be made available.

We want this extraction and publication system to work incrementally, to speed
up the process.  Also, the organization of the source files should be
independent of the organization of the data in the database.

To remove files, see the clear options.  To get the processing errors stored on
the server, or to get a contents dump, see the other actions options.  For more
details, see the design document that comes with Nabu, or use the `--help`
switch.

Configuration
-------------

All the command-line options offered by this program can be set in a
configuration file, which is to be written in Python code.  Use the first long
option name, with dashes replaced by underscores to set the options.

Parent directories for the files and directories specified on the command-line
are searched (in order) to find a file named ``nabu.conf`` to contain this
configuration.  If none are found, the file ``~/.naburc`` in the user's home
directory is looked for.  To supersede this searching mechanism, you can set the
environment variable NABURC and this will be used no matter what).

Minimal configuration: you must at least specify the server URL, user and
password.

"""

__version__ = '$Revision$'
__author__ = 'Martin Blais <blais@furius.ca>'

## Design Note About Dependencies
## ------------------------------
##
## We really want to make it so that all to code to publish fits inside this one
## file, so that we can distribute a single script file with no libraries to
## setup or install, at least for those who will not process locally.  The
## reason is that it's really just much simpler to setup or demo for other
## people, in any place.  However, it the user wants to process locally, we
## require an install of the nabu system; this is where we draw the line.
## Otherwise running this only requires Python-2.4.

# stdlib imports
import sys, os, re, md5, xmlrpclib, fnmatch, urlparse
import optparse
from os.path import *

if sys.version_info[:2] < (2, 3):
    raise SystemExit("Error: you need Python >=2.3 to run this program.")

if sys.version_info[:2] < (2, 4):
    from sets import Set as set

#-------------------------------------------------------------------------------
# Publish
#-------------------------------------------------------------------------------

_server = None
def get_server( opts ):
    """
    Create server lazily, because we might not have any candidates.
    """
    global _server
    if _server is None:
        if opts.process_locally != 3:
            # if opts.verbose:
            #     print '======= connecting to %s' % opts.server_url
            try:
                _server = xmlrpclib.ServerProxy(opts.server_url,
                                                allow_none=1, verbose=0)
                _server.ping()
            except xmlrpclib.Error, e:
                if e.errcode == 401:
                    raise SystemExit(
                        "Error: Cannot authenticate user '%s'." % opts.user)
                else:
                    raise
        else:
            try:
                # You need to provide this module if you want to work locally.
                import nabuserv
                _server = nabuserv.get_server()
            except ImportError, e:
                raise SystemExit(
                    "Cannot import local Nabu server for local processing: " +
                    "'%s'" % e)

    return _server

def opts_publish( parser ):
    # processing options
    group = optparse.OptionGroup(parser,
        "Processing options",
        "These options specify where/how to upload or"
        "process the files on the server.")

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

    group.add_option('-m', '--print-messages', action='store_true',
                     help="Print informative messages indicating what "
                     "the transforms have parsed.")

    group.add_option('--dont-upload-source', action='store_true',
                     help="When processing locally, do not upload the source "
                     "document to the server.  Upload an empty string instead. "
                     "This option only takes effect when you are processing "
                     "the document locally (the server does not need the "
                     "source.")

    parser.add_option_group(group)

def opts_clear( parser ):
    group = optparse.OptionGroup(parser,
        "Clear/remove options",
        "These options specify which files to remove (if any)")

    group.add_option('-c', '--clear-not-found', '--clear-others', '--complete',
                     action='store_true',
                     help="Clear documents that were not found.")

    group.add_option('-C', '--clear-found', '--clear-found-only',
                     action='store_true',
                     help="Clear documents are found, instead of publish.")

    parser.add_option_group(group)

def publish( candidates, opts, args ):
    """
    Publish files.
    """
    server = get_server(opts)

    # remove documents that were found (if requested)
    if opts.clear_found:
        idlist = [x.unid for x in candidates]
        for iid in idlist:
            print '======= clearing {%s}' % iid
        server.clearids(idlist)
        return # nothing more to do

    # check candidates against history (if not suppressed)
    if opts.force:
        proclist = candidates
    elif not candidates:
        proclist = []
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
            else:
                if opts.verbose:
                    print '======= unchanged {%s}' % candidate.unid


    # process selected files
    for pfile in proclist:
        if opts.process_locally == 0:
            print '======= sending source for processing:  %s  {%s}' % \
                  (pfile.fn, pfile.unid)

            errors, messages = server.process_source(
                pfile.unid, pfile.fn, xmlrpclib.Binary(pfile.contents))
            if errors:
                print errors
            if opts.print_messages and messages:
                print messages
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
                docutils.core.publish_doctree

            except ImportError:
                raise SystemExit(
                    "Error: you must have installed docutils in order to "
                    "process files locally.")

            except AttributeError:
                raise SystemExit(
                    "Error: for local processing "
                    "you need a more recent checkout of docutils \n"
                    "or the author's special branch (will be merged soon, "
                    "for now you can fetch it from:\n"
                    "svn://svn.berlios.de/docutils/branches/"
                    "blais_interrupt_render/docutils\n")

            import StringIO
            errstream = StringIO.StringIO()
            doctree = docutils.core.publish_doctree(
                source=pfile.contents, source_path=pfile.fn,
                settings_overrides={
                'input_encoding': 'UTF-8',
                'warning_stream': errstream,
                'halt_level': 100, # never halt
                },
                )
            errors = errstream.getvalue()
            if errors:
                print >> sys.stderr, errors

            if opts.process_locally == 1:
                print '======= sending parsed document to server: {%s}' % \
                      pfile.unid
                import cPickle as pickle
                doctree.reporter = None
                docpickled = pickle.dumps(doctree)

                if opts.dont_upload_source:
                    pfile.contents = '' #utf8

                errors, messages = server.process_doctree(
                    pfile.unid, pfile.fn, pfile.digest,
                    xmlrpclib.Binary(pfile.contents),
                    xmlrpclib.Binary(docpickled),
                    errors)
                if errors:
                    print errors
                if opts.print_messages and messages:
                    print messages

            elif opts.process_locally == 2:
                # do nothing, all we were asked to do is validate and don't
                # send.
                print '======= (file validated)'

            elif opts.process_locally == 3:
                # this case is already taken care of in get_server().
                pass

    # remove documents that were not found (if requested)
    if opts.clear_not_found:
        allids = server.getallids()
        foundids = [x.unid for x in candidates]
        idlist = [x for x in allids if x not in foundids]
        for iid in idlist:
            print '======= clearing {%s}' % iid
        server.clearids(idlist)

#-------------------------------------------------------------------------------
# Other Actions
#-------------------------------------------------------------------------------

def opts_others( parser ):
    group = optparse.OptionGroup(parser,
        "Other actions",
        "Alternative actions, other than publish. "
        "These don't find nor publish.")

    group.add_option('-e', '--errors', '--dump-errors', action='store_true',
                      help="Don't publish, fetch error status from the server.")

    group.add_option('-d', '--dump', '--dump-all', '--debug',
                     action='store_true',
                      help="Don't publish, print server contents for debugging. "
                     "If you specify some unique ids, server information about "
                     "that document is printed.")

    group.add_option('-X', '--clear-all', action='count', default=0,
                     help="Clear the entire database for this user.  If "
                     "you invoke this twice, it resets the schema as well "
                     "(this only works if the server allows that option.)")

    group.add_option('--help-transforms', action='store_true',
                     help="Don't publish, fetch the help for the transforms "
                     "that are supported by the server.  This is a simple "
                     "server-dependent documentation mechanism.")

    parser.add_option_group(group)

def errors( opts ):
    """
    Print last errors in the server.
    """
    errors_info = get_server(opts).geterrors()
    for e in errors_info:
        print '=== From %s {%s}' % (e['filename'], e['unid'])
        print e['errors']

def dump( opts, args ):
    """
    Dump/debug server contents.
    """
    server = get_server(opts)
    if not args:
        attrs = ['unid', 'filename', 'time', 'username', 'errors']
        headers = [dict( [(x, x.capitalize()) for x in attrs] )]
        headers[0]['errors'] = 'Errors'
        sources_info = server.dumpall()

        countcols = dict( [(x, 0) for x in attrs] )
        for s in headers + sources_info:
            for a in attrs:
                countcols[a] = max(countcols[a], len(str(s[a])))

        headers.append( dict( [(x, '-' * countcols[x]) for x in attrs] ) )

        sfmt = '%%(%(name)s)-%(count)ds'
        fmt = '  '.join(
            map(lambda a: sfmt % {'name': a, 'count': countcols[a]}, attrs))

        for s in headers + sources_info:
            print fmt % s
    else:
        attrs = ('unid', 'filename', 'username', 'time', 'digest',)
        attrs_bin = ('errors', 'doctree_str', 'source',)
        for unid in args:
            sources_info = server.dumpone(unid)
            if not sources_info:
                print >> sys.stderr, "Error: document '%s' not found" % unid
                continue

            print '\f'
            for a in attrs:
                print '%s: %s' % (a.capitalize(), sources_info[a])
            for a in attrs_bin:
                print '\f'
                print a.capitalize()
                print '=' * 80
                utf8_text = sources_info[a].data.decode('UTF-8')
                # most consoles take latin-1
                print utf8_text.encode('latin-1', 'replace')
                print

def clear( opts ):
    """
    Issues a clear request to the server.
    """
    print "======= clearing entire database for user '%s'." % opts.user
    if opts.clear_all == 1:
        get_server(opts).clearall()
    elif opts.clear_all == 2:
        if get_server(opts).reset_schema():
            # This only succeeds when the server allows it, i.e. for debugging
            # and configuration.
            print "Schema reset on server and all data dropped."
        else:
            raise SystemExit("Server does not allow to reset the schema.")

def help_transforms( opts ):
    """
    Fetches the help about the server configuration and the transforms it
    supports.
    """
    print
    print 'Supported Transforms on the Server'
    print '=================================='
    print
    print get_server(opts).get_transforms_config().encode('UTF-8')


#-------------------------------------------------------------------------------
# Finder
#-------------------------------------------------------------------------------

def opts_finder( parser ):
    # finder options
    group = optparse.OptionGroup(parser,
                                  "Finder options",
                                  """These options affect how the publisher
                                  finds and recognizes files.""")

    group.add_option('-r', '--recurse', '--recurse',
                      action='store_true', dest='recursive', default=True,
                      help="Disable recursion for directories.")

    group.add_option('-R', '--no-recurse', '--dont-recurse',
                      action='store_false', dest='recursive',
                      help="Disable recursion for directories.")

    group.add_option('-E', '--exclude', action='append', metavar='PATTERN',
                      default=['CVS', '.svn', '*~', '*.bak'],
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

class File:
    """
    Struct to hold information about a candidate.
    """
    def __init__( self, fn, unid, digest, contents ):
        self.fn = fn
        self.unid = unid
        self.digest = digest
        self.contents = contents # always a UTF-8 encoded string

def find_candidates( opts, args ):
    """
    Finds the list of candidate files.
    """
    # validate options
    try:
        opts.marker_regexp = re.compile(opts.marker_regexp, re.M)
    except re.error, e:
        raise SystemExit("Error: Compiling marker regexp: %s" % str(e))

    # find candidate files to consider
    try:
        if not hasattr(opts, 'dont_remove_marker'):
            opts.dont_remove_marker = True
        candidates = find_to_publish(args, opts)
    except IOError, e:
        raise SystemExit('Error: %s' % e)

    if not candidates:
        if opts.verbose:
            print >> sys.stderr, '(no local files to visit.)'
    return candidates

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
        fn = abspath(fn).replace('\\', '/') # platform independent.
        if fn in files:
            print >> sys.stderr, \
                  "Warning: Skipping file '%s' that was seen twice." % fn
            continue
        files.add(fn)

        if opts.verbose:
            print '======= reading...', fn

        # read the beginnings of the file
        try:
            f = open(fn)
        except IOError, e:
            print >> sys.stderr, '======= skipping: %s' % e
            continue

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

def opts_global( parser ):
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

def create_parser():
    """
    Create a new parser with all the options we need.
    """
    parser = optparse.OptionParser(__doc__.strip(), version=__version__)
    opts_global(parser)
    opts_finder(parser)
    opts_publish(parser)
    opts_clear(parser)
    opts_others(parser)
    return parser

def parse_options():
    """
    Parse the command-line and config file options and return a pair of opts,
    args like optparse.
    """
    # first parse to find the names of files or directory arguments.
    parser = create_parser()
    opts, args = parser.parse_args()
    if not args:
        args = ['.']

    # read the config file if found
    configvars = read_config(opts, args)

    # then parse again for real, setting the values in the config file as
    # defaults (and verified by optparse).

    # this next is from optparse from 2.4, in order to be able to run on 2.3.
    if sys.version_info[:2] < (2, 4):
        def _get_all_options(self):
            options = self.option_list[:]
            for group in self.option_groups:
                options.extend(group.option_list)
            return options
        allopts = _get_all_options
    else:
        allopts = optparse.OptionParser._get_all_options

    for option in allopts(parser):
        if option.dest in configvars:
            parser.defaults[option.dest] = configvars[option.dest]

    opts, args = parser.parse_args()

    # some server url is necessary
    if opts.server_url is None and opts.process_locally != 3:
        parser.error("You must specify a server url.")

    # cook up server url with user and password, thus supporting both syntaxes
    # (separate user/pass or xml-rpc module syntax).  Final syntax is:
    # http://user:pass@host:port/path".
    purl = list(urlparse.urlparse(opts.server_url)) # note: does this ever fail?
    mo = re.match('(.+)@(.+)', purl[1])
    if mo:
        purl[1] = mo.group(2)
        userpass = mo.group(1).split(':')
        if len(userpass) == 1:
            fuser, = userpass
        elif len(userpass) == 2:
            fuser, fpass = userpass
        else:
            raise SystemExit("Error: invalid server URL.")
        if not opts.user:
            opts.user = fuser
        if not opts.password:
            opts.password = fpass

    if not opts.password:
        # Query for password if necessary.
        import getpass
        opts.password = getpass.getpass()

    purl[1] = '%s:%s@%s' % (opts.user, opts.password, purl[1])
    opts.server_url = urlparse.urlunparse(purl)

    if opts.verbose:
        print '======= server url:', opts.server_url

    return opts, args

def search_parents( fnordns, confname ):
    """
    Search the given list of files or directories and their parents, for the
    file named `confname`.  The files and directories are searched in the order
    in which they appear.  Return `None` if no file with such a name was found.
    """
    for dn in fnordns:
        if not isdir(dn):
            dn = dirname(dn)
        dn = abspath(dn)
            
        prevdn = None
        while dn != prevdn:
            tentfn = join(dn, confname)
            if exists(tentfn):
                return tentfn
            prevdn = dn
            dn = dirname(dn)

    return None

def read_config( opts, args ):
    """
    Read, parse and verify values from config file.
    Returns a dictionary of all values read in the file.
    """
    # select config file.
    try:
        # look at the environment variable
        rcfile = os.environ['NABURC']
    except KeyError:
        # search the directories and parent directories for config file
        rcfile = search_parents(args, 'nabu.conf')
        if rcfile is None:
            # look for the config file in the user's home
            if 'HOME' in os.environ:
                rcfile = join(os.environ['HOME'], '.naburc')
            else:
                rcfile = None

    if rcfile is None or not exists(rcfile) or not os.access(rcfile, os.R_OK):
        return {}
            
    # read and execute the file.
    defvars = {}
    if opts.verbose:
        print "======= reading config file '%s'" % rcfile
    try:
        execfile(rcfile, defvars)
    except Exception, e:
        import traceback
        print >> sys.stderr, \
              "Error: parsing configuration file '%s'" % rcfile
        print >> sys.stderr, "Please fix errors below before running."
        print >> sys.stderr, '----------------------------------------'
        traceback.print_exc(file=sys.stderr)
        print >> sys.stderr, '----------------------------------------'
        print >> sys.stderr, '(exiting.)'
        raise SystemExit(1)
    return defvars

#-------------------------------------------------------------------------------
# Main Program
#-------------------------------------------------------------------------------

def main():
    """
    Main program for publisher client.
    """
    try: # set the locale to the user settings.
        import locale
        locale.setlocale(locale.LC_ALL, '')
    except:
        pass

    opts, args = parse_options()

    try:
        if opts.errors:
            errors(opts)
        elif opts.dump:
            dump(opts, args)
        elif opts.clear_all:
            clear(opts)
        elif opts.help_transforms:
            help_transforms(opts)
        else:
            # if we're not requesting a complete clear of the database,
            # process files from current directory.  this is a bit of a special
            # behaviour to allow us to clear the entire database.
            if not args:
                args = ['.']
            candidates = find_candidates(opts, args)
            publish(candidates, opts, args)
    except xmlrpclib.Fault, e:
        raise SystemExit("Error: an error occurred on the server:\n %s\n" % e +
                         "Contact the server administrator for support.")

if __name__ == '__main__':
    main()
