#!/usr/bin/env python
#
# Copyright (C) 2005  Martin Blais <blais@furius.ca>
# This file is distributed under the terms of the GNU GPL license.
# For more information: http://furius.ca/nabu.
#
# $Id$
#

"""
Server-side handlers for requests.
"""

# stdlib imports
import sys, xmlrpclib
import traceback
from SimpleXMLRPCServer import SimpleXMLRPCDispatcher
import md5
import datetime
import StringIO
import cPickle as pickle

# docutils imports
from docutils import core, io

# nabu imports
from nabu import process, client
from nabu.utils import ExceptionXMLRPCRequestHandler


__all__ = ('create_server', 'xmlrpc_handle_cgi', 'xmlrpc_handle_mp',)


#-------------------------------------------------------------------------------
#
def create_server(srcstore, transforms, username, allow_reset=0):
    """
    Create a server handler object and return it.
    """
    # create a publish handler
    server_handler = PublishServerHandler(
        srcstore, transforms, allow_reset=allow_reset)

    # prepare (reload) with the current user
    #
    # Note: this is designed this way to allow integration with mod_python,
    # where we would not recreate the objects on every request.  This allows the
    # handler to work with any web application framework (to tell people what
    # they should use for building web applications is a debate we *really* do
    # not want to get involved in...).
    server_handler.reload(username)

    return server_handler

def xmlrpc_handle_cgi(server_handler):
    """
    Given a source storage instance and a list of (transform class, transform
    storage) pairs, implement a basic XMLRPC handler loop.

    Note: this is an example, you might want to handle the XMLRPC loop
    differently, whatever you like.  This is being used by the example CGI
    handler.
    """
    # create an XMLRPC server handler and bind interface
    handler = ExceptionXMLRPCRequestHandler()
    handler.register_instance(server_handler)
    handler.handle_request()

def xmlrpc_handle_mp(server_handler, request_text):
    """
    Same as xmlrpc_handle_cgi() but within a mod_python environment.  Return a
    pair of the response and a list of affected unids.
    """
    # create an XMLRPC server handler and bind interface
    handler = SimpleXMLRPCDispatcher()
    handler.register_instance(server_handler)
    response, error = _exc_marshaled_dispatch(handler, request_text)
    return response, error, list(server_handler.affected_unids())


#-------------------------------------------------------------------------------
#
def _exc_marshaled_dispatch(self, data, dispatch_method = None):
    """handler _marshaled_dispatch() method from xmlrpclib modified to intercept
    and return an exception if it occurs.
    """
    params, method = xmlrpclib.loads(data)

    error = None
    
    # generate response
    try:
        if dispatch_method is not None:
            response = dispatch_method(method, params)
        else:
            response = self._dispatch(method, params)
        # wrap response in a singleton tuple
        response = (response,)
        response = xmlrpclib.dumps(response, methodresponse=1)
    except xmlrpclib.Fault, fault:
        response = xmlrpclib.dumps(fault)
        error = traceback.format_exc()
    except Exception, fault:
        # report exception back to server
        error = traceback.format_exc()
        response = xmlrpclib.dumps(
            xmlrpclib.Fault(1, "%s:%s\n%s" % (sys.exc_type,
                                              sys.exc_value,
                                              error)))

    return response, error


#-------------------------------------------------------------------------------
#
class SimpleAccumulator:
    """
    Simple accumulator object that can only grow a list one item at a time.
    """
    def __init__(self, lis):
        self.acc = lis

    def append(self, new):
        self.acc.append(new)

class PublishServerHandler:
    """
    Protocol server handler.
    """
    username = 'guest'

    def __init__(self, srcstore, transforms, allow_reset=False):
        """
        Create the server handler with the given source storage backend, and a
        list of tranforms to apply when processing document trees.  The
        `transforms` parameter should be an iterable of pairs, consisting of a
        docutils.transform.Tranform class and an instance of an object that
        implements the ExtractorStorage interface.
        """
        self.sources = srcstore
        self.transforms = transforms
        self.allow_reset = allow_reset

        self.username = None

        self.affected = set()
        "Affected unids."

    def reload(self, username):
        """
        Use this it the server is reused between different requests.
        """
        self.username = username

    def ping(self):
        return 0

    def getallids(self):
        return self.sources.getallids(self.username)

    def gethistory(self, idlist=None):
        """
        Returns the digests for the list of requested ids.
        """
        return self.sources.getdigests(self.username, idlist)

    def clearall(self):
        """
        Clear the entire database.
        This is requested from the client interface.
        """
        self.affected.update(self.getallids())

        # Clear the extracted chunks of data that are associated with all
        # documents.
        for extractor, extractstore in self.transforms:
            extractstore.clear()

        # Clear the source documents.
        self.sources.clear(self.username)
        return 0

    def clearids(self, idlist):
        """
        Clear all entries for a set of ids.
        """
        self.affected.update(idlist)

        assert len(idlist) > 0

        # clear the extracted chunks of data that are associated with these
        # documents.
        for unid in idlist:
            # Find the transformed unid, if necessary.
            store_unid = self.sources.map_unid(unid, self.username)

            for extractor, extractstore in self.transforms:
                extractstore.clear(store_unid)

        # clear the source documents
        self.sources.clear(self.username, idlist)

        return 0

    def reset_schema(self):
        """
        Resets the schema for the extractors.
        This may be used for development, debugging, and configuration.
        """
        if self.allow_reset:
            self.sources.reset_schema()
            for extractor, extractstore in self.transforms:
                extractstore.reset_schema()
            return 1
        else:
            return 0 # indicate no reset performed.

    def dumpall(self):
        """
        Returns information about all the documents stored for a specific user.
        """
        return map(self.__xform_xmlrpc,
                   self.sources.get(self.username,
            attributes=('unid', 'filename', 'time', 'username', 'errors',)))

    def dumpone(self, unid):
        """
        Returns information about a single uploaded source.
        """
        # Note: we need to return some Unicode strings using a UTF-8 encoded as
        # a binary, because we don't know if those long strings will contain
        # line-feed characters, which do not go through the XML-RPC layer.

        values = self.sources.get(self.username,
            idlist=[unid],
            attributes=('unid', 'filename', 'username', 'time', 'digest',
                        'errors', 'doctree', 'source'))
        dic = values[0]
        return self.__xform_xmlrpc(dic)

    def geterrors(self):
        """
        Return a list of mappings with the error texts.
        """
        return map(self.__xform_xmlrpc,
                   self.sources.get(self.username,
                                    attributes=('unid', 'filename', 'errors',)))

    def __xform_xmlrpc(self, odic):
        """
        Transform dictionary values to be returnable thru xmlrpc.
        Returns a new dictionary.
        """
        dic = odic.copy()
        for k, v in dic.iteritems():
            if k == 'time':
                dic[k] = v.isoformat()
            elif k in ('errors', 'source',):
                dic[k] = xmlrpclib.Binary(
                    v.encode('UTF-8'))
            elif k == 'doctree':
                doctree_utf8, parts = core.publish_from_doctree(
                    v, writer_name='pseudoxml',
                    settings_overrides={'output_encoding': 'UTF-8'},
                    )
                dic['%s_str' % k] = xmlrpclib.Binary(doctree_utf8)
                del dic[k]
        return dic

    def process_source(self, unid, filename, contents_bin, report_level):
        """
        Process a single file.

        We assume that the file comes wrapped in a Binary, in its original
        encoding.  This function returns a pair of (docutils conversion errors,
        transform messages).
        """
        self.affected.add(unid)
        
        # Convert XML-RPC Binary into string.  The string is encoded in its
        # original encoding.
        contents = contents_bin.data

        # Compute digest of contents.
        m = md5.new(contents)
        digest = m.hexdigest()

        # Add directives from extractors.
        #
        # Note: if you upload the tree from your local parser, it will not
        # support special directives.  You should therefore pretty much always
        # upload source and process on the server if you have special directives
        # to be added for processing.  However, in general we will try to avoid
        # doing that, for that specific reason, but the feature is here anyhoo.
        for xcls, xstore in self.transforms:
            xcls.init_parser()

        # process and store contents as a Unicode string
        errstream = StringIO.StringIO()
        publish_doctree = client.get_publisher()
        doctree, encoding = publish_doctree(
            source=contents, source_path=filename,
            reader_name='standalone',
            parser_name='restructuredtext',
            settings_overrides={
            'error_encoding': 'UTF-8',
            # Remove the comments by default.  This could become an option.
            'strip_comments': 1,
            'warning_stream': errstream,
            'halt_level': 100, # never halt
            'report_level': 1,
            },
            )
        
        # Errors during conversion to document tree.
        errortext = errstream.getvalue().decode('UTF-8')

        messages = self.__process(unid, filename, digest,
                                  contents, encoding, doctree, None,
                                  errortext,
                                  report_level)

        return errortext, messages

    def process_doctree(self, unid, filename, digest,
                        contents_bin, encoding, doctree_bin, errortext,
                        report_level):
        """
        Process a single file.  We assume that the file and document tree comes
        wrapped in a Binary.
        """
        self.affected.add(unid)

        contents = contents_bin.data

        # Note: errors unpickling are caught gracefully and reported to the
        # client (but they should not occur anyway).
        docpickled = doctree_bin.data
        doctree = pickle.loads(docpickled)

        messages = self.__process(unid, filename, digest,
                                  contents, encoding,
                                  doctree, docpickled,
                                  errortext.decode('UTF-8'),
                                  report_level)

        return '', messages

    def __process(self, unid, filename, digest, contents, encoding,
                  doctree, docpickled, errortext, report_level):
        """
        Process the given tree, extracting the information entries from it and
        replacing the existing entries with the newly extracted ones.

        :Parameters:
          ...
          - `docpickled`: an optimization because we might already have a
            pickled version of the tree.  If left to None we create our own.
        """
        assert isinstance(errortext, unicode)


        # Remove all previous objects that were previously extracted from this
        # document, including this document, if it exists.
        self.clearids([unid])

        # Create a pickle receiver, an object whose tasks is to receive and
        # accumulate pickled versions of a document; this is a best-effort
        # mechanism to avoid pickling the document twice.  Worse case we pickle
        # anyway.
        #
        # The way it works is that the transform object has the option to append
        # a new pickled document to the end of the receiver.  Later we decide
        # which one we use, most probably the latest one produced.  This means
        # that if you have multiple transforms which pickle a document make sure
        # you order them correctly (usually there is only a single one).
        pickles = []
        pickle_receiver = SimpleAccumulator(pickles)
        if docpickled:
            pickle_receiver.append(docpickled)

        # Find the transformed unid, if necessary.
        store_unid = self.sources.map_unid(unid, self.username)

        # Transform the document tree.
        # Note: we apply the transforms before storing the document tree.
        messages = process.transform_doctree(
            store_unid, doctree, self.transforms, pickle_receiver,
            report_level)

        # Get the last of the received pickled documents (the most transformed).
        # We reuse that to store the doucment in the database.
        # If there is none, we pickled our own in the source.
        if pickles:
            docpickled = pickles[-1]

        # Add the transformed tree as a new uploaded source
        self.sources.add(self.username, unid, filename.replace('\\', '/'),
                         digest, datetime.datetime.now(),
                         contents,
                         encoding,
                         doctree, errortext,
                         docpickled)
        
        return messages or u''

    def get_transforms_config(self):
        """
        Return a textual description of the supported transforms that this
        server is configured with. We simply concatenate the docstrings of the
        transform classes to provide this.
        """
        helps = []
        for x in self.transforms:
            cls = x[0]
            if not cls.__doc__:
                continue
            
            h = cls.__name__ + ':\n' + cls.__doc__
            if not isinstance(h, unicode):
                # most of our source code in latin-1 or ascii
                h = h.decode('latin-1')
            helps.append(h)
            
        sep = unicode('\n' + '=' * 79 + '\n')
        helptext = sep.join(helps)
        return helptext

    def affected_unids(self):
        """
        Return a list of the affected document unids during the lifetime of this
        publish handler.  This is used to provide feedback to applications which
        may independently cache data assocaited with the documents, other than
        Nabu, such as a memory cached rendered data.
        """
        return self.affected


