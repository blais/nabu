#!/usr/bin/env python
#
# $Source$
# $Id$
#

"""
Find files that contain a publish id and compare their contents to a repository.

This file contains algorithms and an interface to find files which contain an
special marker that indicates that they should be processed and published.
"""

# stdlib imports
import md5
import re
from pprint import pprint, pformat ## FIXME remove

# nabu imports
from nabu import history, utils, process


    
def find_and_publish( fnordns, recurse=True, verbose=False ):
    """
    Discover files, figure out which ones need to be processed, and process them
    if necessary.
    """
    # process files.
    candidates = []
    for fn in utils.process_dirs_or_files(fnordns, recurse):
        if verbose:
            print 'reading...', fn

        # read the beginnings of the file
        f = open(fn)
        header = f.read(2048)

        # find if it should be published
        unid = has_publish_marker(header)
        if not unid:
            f.close()
            continue
        
        # we publish it
        print '== Probing for Publish:', fn
        print '  ', unid
            
        # read the rest of the file and compute md5 contents
        contents = header + f.read()
        f.close()

        m = md5.new(contents)
        digest = m.digest()
        
        # Note: for now we keep all the contents in memory, but when the number
        # of files will get large we will want to do something about it.  We
        # will have to decide between making a single network query for all of
        # the unids/files and losing the contents (reading the files to be
        # processed twice), or making many network queries and processing the
        # winning candidate files immediately.
        candidates.append( File(fn, unid, digest, contents) )

    # check candidates against history
    # Note: this should be a network call.
    idhistory = history.get_md5_history(x.unid for x in candidates)

    # compare digests and figure out which files to process
    proclist = []
    for candidate in candidates:
        try:
            hist_digest = idhistory[candidate.unid]
        except KeyError:
            hist_digest = None

        if candidate.digest != hist_digest:
            proclist.append(candidate)

    # process the files that need to
    print
    for pfile in proclist:
        print '== Processing: %s [%s]' % (pfile.fn, pfile.unid)
        entries = process.process_source(contents)
##         print '  ', doctree.encode('latin1', 'ignore')

        # pickle the doctree and return it
        doctree_pickle = pickle.dumps(entries['document'])


    

        
        





pubmarkre = re.compile('^:Id:\s*(\S*)\s*$', re.M)

def has_publish_marker( text ):
    """
    Returns the unique publish marker in the file, if the given text contains
    the special publish marker within the starting lines of the document.
    """
    mo = pubmarkre.search(text)
    if mo:
        return mo.group(1)
    return None
        
class File:
    """
    Struct to hold information about a candidate.
    """
    def __init__( self, fn, unid, digest, contents ):
        self.fn = fn
        self.unid = unid
        self.digest = digest
        self.contents = contents
