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

raise NotImplementedError("FIXME this extractor is unfinished.")

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
class PhotoExtractor(extract.Extractor):
##     """
##     Transform that finds photos represented as line-blocks of less than lines,
##     where if it has three lines, the first line is taken to be a description,
##     the second line is a URL (reference), and the third line a comma-separated
##     set of keywords.  Like this::
##     
##       |   From Montreal -- Classifieds for Japanese living in Montreal
##       |   http://www.from-montreal.com/
##       |   montreal, classified, ads, japan
## 
##     The following forms are also accepted.
## 
##       | Description of a photo, no keywords
##       | http://this-is-a-reference.com/target.html
## 
##       | http://this-is-a-reference.com/target.html
##       | just, the, keywords
##     
##       | http://this-is-a-reference.com/target.html
## 
##     """
    
    default_priority = 900

    @classmethod
    def init_parser( cls ):
        directives.register_directive('photo', photo_directive)
        directives.register_directive('photogroup', photogroup_directive)

    def apply( self, **kwargs ):
        return

##         self.unid, self.storage = kwargs['unid'], kwargs['storage']

##         v = self.Visitor(self.document)
##         v.x = self
##         self.document.walk(v)

##     class Visitor(nodes.SparseNodeVisitor):
## 
##         def visit_line_block( self, node ):
##             # check the number of lines
##             if len(node.children) not in (1, 2, 3):
##                 return
##             
##             ldesc = lurl = lkeys = ''
## 
##             # check the various patterns above
##             def checkref( lineref ):
##                 if not lineref.children[0]:
##                     return False
##                 if not isinstance(lineref.children[0], nodes.reference):
##                     return False
##                 return lineref.children[0]
##             
##             if len(node.children) == 1:
##                 ref = checkref(node.children[0])
##                 if not ref:
##                     return
##                 lurl = ref.astext()
## 
##             elif len(node.children) == 2:
##                 ref = checkref(node.children[1])
##                 if ref:
##                     lurl = ref.astext()
##                     ldesc = node.children[0].astext()
##                 else:
##                     ref = checkref(node.children[0])
##                     if ref:
##                         lurl = ref.astext()
##                         lkeys = node.children[1].astext()
##                     else:
##                         return
##                     
##             elif len(node.children) == 3:
##                 ref = checkref(node.children[1])
##                 lurl = ref.astext()
##                 ldesc = node.children[0].astext()
##                 lkeys = node.children[2].astext()
##             else:
##                 return
##             
##             # add a class to the document for later rendering
##             node.attributes['classes'].append('bookmark')
## 
##             # store the bookmark
##             self.x.storage.store(self.x.unid, ldesc, lurl, lkeys)
                

## class Photo(SQLObject):
##     """
##     Storage for document information.
##     """
##     unid = StringCol(notNull=1)

##     url = StringCol()
##     description = UnicodeCol()
##     keywords = UnicodeCol()


## class PhotoStorage(extract.SQLObjectExtractorStorage):
##     """
##     Photo storage.
##     """

##     sqlobject_classes = [Photo]

##     def store( self, unid, url, description, keywords ):
##         Photo(unid=unid)
## ##              url=url,
## ##              description=description,
## ##              keywords=keywords)

