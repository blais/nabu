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
from docutils.core import publish_programmatically
from docutils import nodes

__all__ = ['process_source']


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

##             print node.children[0].astext()
##             print node.children[1].children[0]
##             print node.children[2].astext()
            

    def apply( self ):
        v = self.Visitor(self.document)
        self.document.walk(v)


class NabuReader(docutils.readers.standalone.Reader):
    """
    Nabu restructured text reader.
    This is used to add our transforms.
    """
    default_transforms = docutils.readers.standalone.Reader.default_transforms + (
        LinkTransform,
        )

class NoopWriter(docutils.writers.null.Writer):
    """
    Writer that translates the document tree into itself, i.e. does nothing at
    all.
    """
    def translate( self ):
        self.output = self.document

class CatcherDestination(docutils.io.NullOutput):
    """
    Simple destination class that catches the document tree.
    """
    def write( self, data ):
        self.destination.append(data)

def process_source( contents ):
    """
    Process a source document into a document tree, extract various kinds of
    entries from the document and return a map of all those extracted entries,
    including the document itself.

    This method is expecting the contents to be a Unicode string.
    """
    docreceiver = []

    output, pub = publish_programmatically(
        source_class=docutils.io.StringInput, source=contents, source_path=None,
        destination_class=CatcherDestination,
        destination=docreceiver, destination_path=None,
        reader=NabuReader(), reader_name='standalone',
        parser=None, parser_name='restructuredtext',
        writer=NoopWriter(), writer_name=None,
        settings=None, settings_spec=None,
        settings_overrides={'input_encoding': 'unicode'},
        config_section=None,
        enable_exit_status=None)

    document = docreceiver[0]
    
    # remove stuff for pickling
    transformer = document.transformer
    
    document.transformer = None
    document.reporter = None

##     print >> sys.stderr, pformat(document)
##     print >> sys.stderr, type(parts['whole'])
##     print >> sys.stderr, parts['whole'].encode('latin-1', 'replace')

    entries = {
        'Document': {'contents': pickle.dumps(document)}
        }
    
    return entries

