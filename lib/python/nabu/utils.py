#!/usr/bin/env python
#
# $Source$
# $Id$
#

"""
Misc generic utility functions.
"""

import os
from os.path import isdir, isfile, islink, join

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
