#!/usr/bin/env python
# -*- coding: iso-8859-1 -*-
#
# $Id$
#

"""
Generic utilities that could be reused in other programs.
"""

# stdlib imports
from SimpleXMLRPCServer import CGIXMLRPCRequestHandler


class ExceptionXMLRPCRequestHandler(CGIXMLRPCRequestHandler):
    """
    XMLRPC handler, with tracing for exceptions.
    This makes it much easier to fix exceptions when they occur on the server.
    """
    def _dispatch( self, method, params ):
        try:
            return CGIXMLRPCRequestHandler._dispatch(self, method, params)
        except Exception, e:
            # print server error on stderr (which should go to the apache
            # logfile so we can more easily debug the problem)
            import traceback
            traceback.print_exc()
            raise e

