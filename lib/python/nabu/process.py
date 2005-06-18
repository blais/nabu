#!/usr/bin/env python
#
# $Source$
# $Id$
#

"""
Process the restructuredtext files.
"""

from docutils.core import publish_parts
from docutils.readers.standalone import Reader
from docutils.transforms import Transform
from docutils import nodes

#===============================================================================
# PUBLIC DECLARATIONS
#===============================================================================

#===============================================================================
# LOCAL DECLARATIONS
#===============================================================================

## #
## # New node types.
## #
## class bookmark(node.line_block): pass



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

    entries = {
        'document': parts['whole'],
        }
    
    return entries


if __name__ == '__main__':
    main()

