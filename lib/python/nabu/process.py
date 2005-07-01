#!/usr/bin/env python
#
# $Id$
#

"""
Process the document tree with a set of custom transforms.
"""

# stdlib imports
import StringIO

# docutils imports
import docutils.utils
import docutils.frontend
from docutils.transforms import Transformer

# nabu imports
from nabu.extract import Extractor


def transform_doctree( unid, doctree, transforms, pickle_receiver=None ):
    """
    Run the transforms on the document tree.  This may modify the tree,
    which will have an effect later on if using that stored document tree as
    a source for rendering.
    """
    # populate with transforms
    doctree.transformer = Transformer(doctree)
    for tclass, storage in transforms:
        assert issubclass(tclass, Extractor)
        doctree.transformer.add_transform(
            tclass, unid=unid, storage=storage,
            pickle_receiver=pickle_receiver)

    # create an appropriate reporter
    fend = docutils.frontend.OptionParser()
    settings = fend.get_default_values()
    errstream = StringIO.StringIO()
    settings.update({
        'warning_stream': errstream,
        'error_encoding': 'UTF-8',
        'halt_level': 100, # never halt
        'report_level': 0,
        }, fend)
    doctree.reporter = docutils.utils.new_reporter('', settings)

    # apply the transforms
    doctree.transformer.apply_transforms()
    
    # fix back the doctree to allow to be pickled 
    doctree.transformer = doctree.reporter = None

    return errstream.getvalue().decode('UTF-8')
