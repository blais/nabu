#
# Copyright (C) 2005  Martin Blais <blais@furius.ca>
# This file is distributed under the terms of the GNU GPL license.
# For more information: http://furius.ca/nabu.
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
    def _dispatch(self, method, params):
        try:
            return CGIXMLRPCRequestHandler._dispatch(self, method, params)
        except Exception, e:
            # print server error on stderr (which should go to the apache
            # logfile so we can more easily debug the problem)
            import traceback
            traceback.print_exc()
            raise e


