#!/usr/bin/env python
#
# $Source$
# $Id$
#

"""
Process the restructuredtext files.
"""

# stdlib imports
import pickle

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


def process_source( contents ):
    """
    Process a source document into a document tree, extract various kinds of
    entries from the document and return a map of all those extracted entries,
    including the document itself.

    This method is expecting the contents to be a Unicode string.
    """
    document = docutils.core.publish_document(
        source=contents,
        reader=NabuReader(),
        settings_overrides={'input_encoding': 'unicode'}
        )
    
    # remove stuff for pickling
    transformer = document.transformer
    
    document.transformer = None
    document.reporter = None

    entries = {
        'Document': {'contents': pickle.dumps(document)}
        }
    
    return entries


def render_doctree( document, writer, encoding='UTF-8', settings_overrides={} ):
    """
    Renders a docutils document tree with an existing writer.
    """
## FIXME the contents of this should go in the docutils code itself.


    destination = docutils.io.StringOutput(encoding=encoding)

    # setup settings for writer
    option_parser = OptionParser( components=(writer,),
                                  defaults={}, read_config_files=0)
    document.settings = option_parser.get_default_values()

    # add our settings overrides
    document.settings.update(settings_overrides, option_parser)
##     from pprint import pprint, pformat ## FIXME remove
##     import sys
##     print >> sys.stderr, pformat(document.settings)

    
    # create a reporter
    document.reporter = docutils.utils.Reporter(
        '<string>',
        document.settings.report_level,
        document.settings.halt_level,
        stream=document.settings.warning_stream,
        debug=document.settings.debug,
        encoding=document.settings.error_encoding,
        error_handler=document.settings.error_encoding_error_handler)
    ## source <string>, report_level 2, halt_level 4, stream None
    ## debug None, encoding ascii, error_handler backslashreplace
    
    output = writer.write(document, destination)
    writer.assemble_parts()

    return output

    
