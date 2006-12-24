#!/usr/bin/env python
#
# Copyright (C) 2005  Martin Blais <blais@furius.ca>
# This file is distributed under the terms of the GNU GPL license.
# For more information: http://furius.ca/nabu.
#
# $Id$
#

"""
Process the document tree with a set of custom transforms.
"""

# stdlib imports
import sys, StringIO, traceback

# docutils imports
import docutils.utils
import docutils.frontend
from docutils.transforms import Transformer

from docutils.transforms.universal import FilterMessages

# nabu imports
from nabu.extract import Extractor


def transform_doctree(unid, doctree, transforms, pickle_receiver=None,
                      report_level=1):
    """
    Run the transforms on the document tree.  This may modify the tree,
    which will have an effect later on if using that stored document tree as
    a source for rendering.
    """
    # Create transformer.
    doctree.transformer = Transformer(doctree)

    # Add a transform to remove system messages.
    doctree.transformer.add_transform(FilterMessages, priority=1)
    
    # Populate with transforms.
    for tclass, storage in transforms:
        assert issubclass(tclass, Extractor)
        doctree.transformer.add_transform(
            tclass, unid=unid, storage=storage,
            pickle_receiver=pickle_receiver)

    # Create an appropriate reporter.
    fend = docutils.frontend.OptionParser()
    settings = fend.get_default_values()
    errstream = StringIO.StringIO()
    settings.update({
        'warning_stream': errstream,
        'error_encoding': 'UTF-8',
        'halt_level': 100, # never halt
        'report_level': report_level,
        }, fend)
    doctree.reporter = docutils.utils.new_reporter('', settings)

    # Apply the transforms.
    try:
        doctree.transformer.apply_transforms()
    except Exception, e:
        traceback.print_exc(sys.stderr)
    
    # Fix back the doctree to allow to be pickled.
    doctree.transformer = doctree.reporter = None

    # Return messages that were reported during the processing of the
    # transforms.
    return errstream.getvalue().decode('UTF-8')
