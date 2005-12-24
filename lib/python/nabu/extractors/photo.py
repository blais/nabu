#!/usr/bin/env python
#
# Copyright (C) 2005  Martin Blais <blais@furius.ca>
# This file is distributed under the terms of the GNU GPL license.
# For more information: http://furius.ca/nabu.
#
# $Id$
#

"""
Process photos inside of documents.
"""

# stdlib imports
import re, datetime

# docutils imports
from docutils import nodes
from docutils.parsers.rst import directives

# nabu imports
from nabu import extract


#-------------------------------------------------------------------------------
#
align_values = ('left', 'center', 'right')

def align(argument):
    return directives.choice(argument, align_values)

def photo_directive( name, arguments, options, content, lineno,
                     content_offset, block_text, state, state_machine ):
    """
    Special photo directive, which will display a thumbnail of the image with a
    link to a photo page.
    """
    reference = ''.join(arguments[0].split('\n'))
    if reference.find(' ') != -1:
        error = state_machine.reporter.error(
              'Photo URI contains whitespace.', '',
              nodes.literal_block(block_text, block_text),
              line=lineno)
        return [error]
    options['uri'] = reference
    options['photo'] = '1'
    image_node = nodes.image(block_text, **options)

    if options['align'] == 'center':
        div_node = nodes.section(CLASS='photodiv')
        div_node.append(image_node)
        results = [div_node]
    else:
        results = [image_node]
    return results

photo_directive.arguments = (1, 0, 0)
photo_directive.options = {'alt': directives.unchanged,
                           'align': align}

#-------------------------------------------------------------------------------
#
def photogroup_directive( name, arguments, options, content, lineno,
                          content_offset, block_text, state, state_machine ):

    # figure out what this is doing.
    references = map(lambda x: x.strip(), content)
    if not references:
        return []

    sopts = {
        'class': 'photogroup',
        }
    pnode = nodes.bullet_list(**sopts)
    for reference in references:
        if reference.find(' ') != -1:
            error = state_machine.reporter.error(
                  'Photogroup URI contains whitespace.', '',
                  nodes.literal_block(block_text, block_text),
                  line=lineno)
            return [error]
        options['uri'] = reference
        options['photo'] = '1'
        image_node = nodes.image(block_text, **options)

        pnode.append(image_node)

    return [pnode]

photogroup_directive.arguments = (0, 0, 0)
photogroup_directive.options = {'alt': directives.unchanged}
photogroup_directive.content = True


#-------------------------------------------------------------------------------
#
class Extractor(extract.Extractor):
    
    default_priority = 900

    @classmethod
    def init_parser( cls ):
        directives.register_directive('photo', photo_directive)
        directives.register_directive('photogroup', photogroup_directive)

    def apply( self, **kwargs ):
        # Note: For now, this changes the document tree via the directives but
        # does not store anything.
        return


#-------------------------------------------------------------------------------
#
class Storage(extract.SQLExtractorStorage):
    """
    Photo storage.
    """
    # Note: For now, this changes the document but does not store anything.

