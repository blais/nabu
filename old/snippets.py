


class RemoveSystemMessages(docutils.transforms.Transform):
    """
    Transform that removes the system messages from the doctree.
    """
    def apply( self, **kwargs ):
        """
        Apply the transform to the document tree.
        See the documentation for docutils.transforms.Transform.
        """
