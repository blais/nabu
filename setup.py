#!/usr/bin/env python

"""
Install script for the Nabu server.
"""

__author__ = "Martin Blais <blais@furius.ca>"

import sys
from distutils.core import setup

def read_version():
    try:
        return open('VERSION', 'r').readline().strip()
    except IOError, e:
        raise SystemExit(
            "Error: you must run setup from the root directory (%s)" % str(e))


# Include all files without having to create MANIFEST.in
def add_all_files(fun):
    import os, os.path
    from os.path import abspath, dirname, join
    def f(self):
        for root, dirs, files in os.walk('.'):
            if '.hg' in dirs: dirs.remove('.hg')
            self.filelist.extend(join(root[2:], fn) for fn in files
                                 if not fn.endswith('.pyc'))
        return fun(self)
    return f
from distutils.command.sdist import sdist
sdist.add_defaults = add_all_files(sdist.add_defaults)


print >> sys.stderr,  """

  Warning: this installation is needed only if you're installing a Nabu server.
  If you want to publish files, all you need is the Nabu client publisher script
  (a single file).

"""
setup(name="nabu",
      version=read_version(),
      description=\
      "A simple framework to publish and extract info from rst documents to a server database.",
      long_description="""
Assuming that a user can easily create text documents --this is the case for
most programmers and techies, we do this all day, and we all have our favourite
text editors-- this system allows you to store various kinds of data *across*
multiple documents.  You can create and maintain a body of text files from which
various elements automatically could get stored in an organized manner in a
database.

Nabu is a simple framework that extracts chunks of various types of information
from documents written in simple text files (written with reStructuredText_
conventions) and that stores this information (including the document) in a
remote database for later retrieval.  The processing and extraction of the
document is handled on a server, and there is a small and simple client that is
used to push the files to the server for processing and storage (think
``rsync``).  The client requires only Python to work.  The presentation layer is
left unspecified: you can use whichever web application framework you like to
present the extracted data in the way that you prefer.
""",
      license="GPL",
      author="Martin Blais",
      author_email="blais@furius.ca",
      url="http://furius.ca/nabu",
      download_url="http://github.com/blais/nabu",
      package_dir = {'': 'lib/python'},
      packages = ['nabu', 'nabu.extractors'],
     )

      ## scripts = ['bin/nabu'],
      # FIXME: distutils follows the symlink and installs both bin/nabu and
      # lib/python/nabu/client.py in /usr/bin.  I want to it install just
      # 'bin/nabu'. How do I do that?
