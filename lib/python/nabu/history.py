#!/usr/bin/env python
#
# $Source$
# $Id$
#

"""
Document storage history.

Implements a way for the system to provide a history of the source documents
that were used to fill information in the data storage and some information
about these documents to allow the finder to check whether a document has
changed or not.
"""

#-------------------------------------------------------------------------------
#
def get_md5_history( idlist=None ):
    """
    Given a list of document ids to check for, return a mapping of md5sums for
    these documents at the time they were last stored in the database.

    This is meant to be used by the finder algorithm to figure out which files
    to reprocess or not.

    If not id list is given, all the md5sums in the system are returned.
    """
    
    # FIXME TODO: implement something real to save and return history
    return dict( (x, None) for x in idlist )
    
