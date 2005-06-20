#!/usr/bin/env python
#
# $Source$
# $Id$
#

"""
Process the restructuredtext files.
"""

# docutils imports
import docutils.io
import docutils.utils
import docutils.writers.html4css1
from docutils.frontend import OptionParser
import docutils.readers.standalone
import docutils.core

__all__ = ['process_source']

# nabu imports
import nabu.entryforms
# note: this triggers registration of all the entry forms types.
from nabu.entryforms import *

class NabuReader(docutils.readers.standalone.Reader):
    """
    Nabu restructured text reader.
    This is used to add our transforms.
    """
    default_transforms = docutils.readers.standalone.Reader.default_transforms +\
                        tuple(nabu.entryforms.registry.values())


def extract( doctree ):
    """
    Runs the Nabu transforms on an existing document tree, extracting various
    kinds of entries from the document and return a map of all those extracted
    entries, including the document itself.
    """
##     document, parts = docutils.core.publish_doctree(
##         source=contents,
##         reader=NabuReader(),
##         settings_overrides={'input_encoding': 'unicode'}
##         )
    
    import cPickle as pickle
    entries = {
        'Document': {}
        }
    
    return entries
