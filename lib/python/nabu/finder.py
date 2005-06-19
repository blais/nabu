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

# nabu imports
from nabu import history, utils

__all__ = ['find_to_publish']


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
    for fn in utils.process_dirs_or_files(fnordns, recurse):
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
        
