#!/usr/bin/env python
#
# $Id$
#

"""
Server-side handlers for requests.
"""

# stdlib imports
import xmlrpclib
import md5
import datetime
import StringIO
import cPickle as pickle

# docutils imports
import docutils.core

# nabu imports
from nabu import process
from nabu.utils import ExceptionXMLRPCRequestHandler

class PublishServerHandler:
    """
    Protocol server handler.
    """
    username = 'guest'

    def __init__( self, srcstore, transforms, allow_reset=False ):
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

    def reload( self, username ):
        """
        Use this it the server is reused between different requests.
        """
        self.username = username

    def ping( self ):
        return 0

    def getallids( self ):
        return self.sources.getallids(self.username)

    def gethistory( self, idlist=None ):
        """
        Returns the digests for the list of requested ids.
        """
        return self.sources.getdigests(self.username, idlist)

    def clearall( self ):
        """
        Clear the entire database.
        This is requested from the client interface.
        """
        # clear the extracted chunks of data that are associated with all
        # documents.
        for extractor, extractstore in self.transforms:
            extractstore.clear()

        # clear the source documents
        self.sources.clear(self.username)
        return 0

    def clearids( self, idlist ):
        """
        Clear all entries for a set of ids.
        """
        assert len(idlist) > 0

        # clear the extracted chunks of data that are associated with these
        # documents.
        for unid in idlist:
            for extractor, extractstore in self.transforms:
                extractstore.clear(unid)

        # clear the source documents
        self.sources.clear(self.username, idlist)
        return 0

    def reset_schema( self ):
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

    def dumpall( self ):
        """
        Returns information about all the documents stored for a specific user.
        """
        return map(self.__xform_xmlrpc,
                   self.sources.get(self.username,
            attributes=('unid', 'filename', 'time', 'username', 'errors-p',)))

    def dumpone( self, unid ):
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

    def geterrors( self ):
        """
        Return a list of mappings with the error texts.
        """
        return map(self.__xform_xmlrpc,
                   self.sources.get(self.username,
                                    attributes=('unid', 'filename', 'errors',)))

    def __xform_xmlrpc( self, odic ):
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
                doctree_utf8, parts = docutils.core.publish_from_doctree(
                    v, writer_name='pseudoxml',
                    settings_overrides={'output_encoding': 'UTF-8'})
                dic['%s_str' % k] = xmlrpclib.Binary(doctree_utf8)
                del dic[k]
        return dic

    def process_source( self, unid, filename, contents_bin ):
        """
        Process a single file.
        We assume that the file comes wrapped in a Binary, encoded in UTF-8.
        """
        # convert XML-RPC Binary into string
        contents_utf8 = contents_bin.data

        # compute digest of contents
        m = md5.new(contents_utf8)
        digest = m.hexdigest()

        # process and store contents as a Unicode string
        errstream = StringIO.StringIO()
        doctree = docutils.core.publish_doctree(
            source=contents_utf8, source_path=filename,
            settings_overrides={
            'input_encoding': 'UTF-8',
            'error_encoding': 'UTF-8',
            'warning_stream': errstream,
            'halt_level': 100, # never halt
            },
            )

        errortext = errstream.getvalue().decode('UTF-8')
        messages = self.__process(unid, filename, digest,
                                  contents_utf8, doctree, None, errortext)
        return errortext, messages

    def process_doctree( self, unid, filename, digest,
                         contents_bin, doctree_bin, errortext ):
        """
        Process a single file.  We assume that the file and document tree comes
        wrapped in a Binary, encoded in UTF-8.
        """
        contents_utf8 = contents_bin.data

        # Note: errors unpickling are caught gracefully and reported to the
        # client (but they should not occur anyway).
        docpickled = doctree_bin.data
        doctree = pickle.loads(docpickled)

        messages = self.__process(unid, filename, digest,
                                  contents_utf8, doctree, docpickled,
                                  errortext.decode('UTF-8'))
        return '', messages

    def __process( self, unid, filename, digest, contents_utf8,
                   doctree, docpickled, errortext ):
        """
        Process the given tree, extracting the information entries from it and
        replacing the existing entries with the newly extracted ones.

        :Parameters:
          ...
          - `docpickled`: an optimization because we might already have a
            pickled version of the tree.  If left to None we create our own.
        """
        assert isinstance(errortext, unicode)

        # remove all previous objects that were previously extracted from this
        # document, including this document, if it exists
        self.clearids([unid])

        # transform the document tree
        # Note: we apply the transforms before storing the document tree.
        messages = process.transform_doctree(unid, doctree, self.transforms)
        
        # add the transformed tree as a new uploaded source
        self.sources.add(self.username, unid, filename.replace('\\', '/'),
                         digest, datetime.datetime.now(),
                         contents_utf8.decode('utf-8'),
                         doctree, errortext,
                         docpickled)
        
        return messages or u''

    def get_transforms_config( self ):
        """
        Return a textual description of the supported transforms that this
        server is configured with. We simply concatenate the docstrings of the
        transform classes to provide this.
        """
        helps = []
        for x in self.transforms:
            cls = x[0]
            h = cls.__name__ + ':\n' + cls.__doc__
            if not isinstance(h, unicode):
                # most of our source code in latin-1 or ascii
                h = h.decode('latin-1')
            helps.append(h)
            
        sep = unicode('\n' + '=' * 79 + '\n')
        return sep.join(helps)


def xmlrpc_handler( srcstore, transforms, username, allow_reset=0 ):
    """
    Given a source storage instance and a list of (transform class, transform
    storage) pairs, implement a basic XMLRPC handler loop.

    Note: this is an example, you might want to handle the XMLRPC loop
    differently, whatever you like.  This is being used by the example CGI
    handler.
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
    
    # create an XMLRPC server handler and bind interface
    handler = ExceptionXMLRPCRequestHandler()
    handler.register_instance(server_handler)
    handler.handle_request()
