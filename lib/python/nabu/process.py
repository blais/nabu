#!/usr/bin/env python
#
# $Source$
# $Id$
#

"""
Process the restructuredtext files.
"""

import xmlrpclib
import pickle

from docutils.core import publish_parts
from docutils.readers.standalone import Reader
from docutils.transforms import Transform
from docutils import nodes

__all__ = ['process_source']

#-------------------------------------------------------------------------------
# PROCESSORS

class IProcessor:
    """
    Interface for processor classes.  Processors are classes whose role is to
    take the source file and insert it into the system, either via a network
    request, or by processing it directly and sending the extracted results over
    the network.
    """
    def process( self, fn, unid, contents=None ):
        """
        Process a single file identified by filename 'fn', unique id 'unid',
        which has a digest or 'digest' and contents 'contents'.  If 'contents'
        is None, we read the file from filename, otherwise we use the given
        contents (this is just for efficiency, to allow the client to cache the
        contents if he did that).
        """

class NetworkProcessor(IProcessor):
    """
    Processor that simply sends the file over a network connection.  The server
    is expected to perform the parsing itself (asynchronously) and to somehow
    provide a way to display errors to the client (if he wants it).
    """
    def __init__( self, server ):
        self.server = server

    def process( self, fn, unid, contents ):
        self.server.process_file(unid, fn, xmlrpclib.Binary(contents))


class ClientProcessor(IProcessor):
    """
    Processor that parses the file on the client side and then sends the parsed
    results over to the server to include (the original contents file is never
    sent).
    """
    def __init__( self, server ):
        self.server = server

    def process( self, fn, unid, contents ):
        pass
##         print '== Processing: %s [%s]' % (fn, unid)
## FIXME TODO process in the client code

##         entries = process_source(pfile.contents)

##         # pickle the doctree and return it
##         doctree_pickle = pickle.dumps(entries['document'])


    


class LinkTransform(Transform):
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


class NabuReader(Reader):
    """
    Nabu restructured text reader.
    This is used to add our transforms.
    """
    default_transforms = Reader.default_transforms + (
        LinkTransform,
        )


def process_source( contents ):
    """
    Process a source document into a document tree, extract various kinds of
    entries from the document and return a map of all those extracted entries,
    including the document itself.
    """
    reader = NabuReader()
    parts = publish_parts(source=contents, reader=reader)

    import sys
    print >> sys.stderr, parts['whole'].encode('latin-1', 'replace')

    entries = {
        'Document': {'contents': pickle.dumps(parts['whole'])}
        }
    
    return entries

