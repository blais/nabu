#!/usr/bin/env python
#
# $Source$
# $Id$
#

"""
Process the restructuredtext files.
"""

import sys
import xmlrpclib
import pickle
from pprint import pprint, pformat

import docutils.readers.standalone
import docutils.writers.null
import docutils.transforms
import docutils.io
import docutils.core
from docutils import nodes

class LinkTransform(docutils.transforms.Transform):
    """
    Transform that finds links represented as line-blocks of less than lines,
    where if it has three lines, the first line is taken to be a description,
    the second line is a URL (reference), and the third line a comma-separated
    set of keywords.  Like this::
    
      | Description of a link
      | http://this-is-a-reference.com/target.html
      | keyword1, references, keyword3

    The following forms are also accepted.

      | Description of a link, no keywords
      | http://this-is-a-reference.com/target.html

      | http://this-is-a-reference.com/target.html
      | just, the, keywords
    
      | http://this-is-a-reference.com/target.html

    """
    default_priority = 900

    table = 'Link'

    class Visitor(nodes.SparseNodeVisitor):

        def visit_line_block( self, node ):
            # check the number of lines
            if len(node.children) not in (1, 2, 3):
                return

            # make sure that all children are lines
            hasref = None
            for line in node.children:
                if not isinstance(line, nodes.line):
                    return
                if len(line.children) == 1 and \
                   isinstance(line.children[0], nodes.reference):
                    hasref = line
                
            # make sure that one of the children has a reference has the unique
            # child
            if hasref is None:
                return
            
            node.attributes['classes'].append('bookmark')

            print node.children[0].astext()
            print node.children[1].children[0]
            print node.children[2].astext()
            

    def apply( self ):
        v = self.Visitor(self.document)
        self.document.walk(v)

import nabu.entryforms
nabu.entryforms.registry['link'] = LinkTransform
