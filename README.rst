==============================================
  nabu: a Publishing System using Text Files
==============================================

   "Nabu is the Babylonian god of wisdom and writing [...]  Nabu is accorded the
   office of patron of the scribes, taking over from the Sumerian goddess
   Nisaba. His consort is Tashmetum. His symbols are the clay writing tablet
   with the writing stylus. [...]  His power over human existence is immense,
   because Nabu engraves the destiny of each person, as the Gods have decided,
   on the tablets of sacred record."

   ---(From `Wikipedia <http://en.wikipedia.org/wiki/Nabu>`_)


.. contents::
..
    1   Description
      1.1  Example: Extracting Contact Info
      1.2  Example: Blogging System
      1.3  Example: Automatic Bookmarks List
      1.4  Example: Shared Events Calendar
      1.5  Customizability: Writing Extractors
      1.6  Target Audience
    2   Features
      2.1  Nabu is not ...
    3   Documentation
      3.1  For Content Writers
      3.2  Technical
      3.3  Design
      3.4  Talks
      3.5  Test Drive Nabu
    4   Download
    5   Reporting Bugs
    6   Links
    7   Installation and Dependencies
    8   Copyright and License
    9   Acknowledgements
    10  Author



Description
===========

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


.. figure:: doc/nabu2.png

   Dataflow diagram of Nabu framework.


It is probably best illustrated by some examples...



Example: Extracting Contact Info
--------------------------------

For example, imagine that you write several files about your travels, say, one
for each destination.  Most likely they contain various contact information.
You could insert them like this in any of your text files and they would
automatically be extracted to a global list of contact info::

  :Contact:
  :n: Martin Blais
  :e: blais@furius.ca
  :a: 1 rue de la Montagne, Mongueuil, France

You could use this to feed into an online address book system, or create a
birthday notification system for yourself by adding your birth date.


Example: Blogging System
------------------------

Another example: you could easily build a blogging system by detecting documents
with certain bibliographic fields and a date at the top of document, for
example::

   Cookies and Cream Today
   =======================

   :Blog: general
   :Date: 2005-06-25

   Ahh, I like to talk about cookies and cream...

All you would have to do is present the documents in an orderly way, e.g. by
category, by date, just the most recent, whatever you like.


.. figure:: doc/nabusit.png

   Nabu does not really fit into any single category... it is a simple
   implementation of a simple idea that "sits" between all these things and that
   can be used to feed data into databases for presentations similar as the ones
   mentioned above.


Example: Automatic Bookmarks List
---------------------------------

Another idea: you could automatically extract all the URLs from the documents
pushed to the server (across *all* the files) and automatically build an online
RSS bookmarks feeder, where your bookmarks would be organized by keywords, maybe
even fetching the keywords in the respective documents from which they were
extracted.


Example: Shared Events Calendar
-------------------------------

How about this one: I maintain a todo file in a text file, simply.  With a
simple convention, like::

  :Event: 2005-06-28

    - dinner with Hannah @ funky restaurant

  :Event: 2005-07-10 13h30

    - presentation on quaternions (room C-117)

These entries could be fed automatically in a shared Nabu, for a group of
friends or perhaps co-workers, and presented as a shared online calendar,
perhaps password-protected for access by certain people only, or filtered
somehow.


There are many possibilities... I'm convinced I will find more serious uses for
this system as well, which is why I built it in a generic manner.


.. important::

   If you have a commercial use need for a system similar to this one, the
   author is generally available for consulting to implement customizations or
   build a system on top of Nabu.  See `contact information for consulting
   </home/consulting.html>`_.  I'm very interested in new ways to publish and
   organize information online.


Customizability: Writing Extractors
-----------------------------------

Various simple extractors will come with the Nabu package itself, but we suspect
you will very soon want to write your own.  Writing extractors is very easy.

All of this is built using the very powerful docutils_ tools, which includes the
reStructuredText_ parser and provides the data structures that represent your
source documents.  Extractors are simply docutils transforms that visit the
document structure (which is provided and saved by the Nabu system).  To add a
new type of entry, all you need to do is write code that visits the tree, finds
what you want, and write a simple object to store it in the way you prefer.  You
can use any system you like to store the data in a database or in text files
(SQL DBAPI, an ORM, files, ...).

.. note::

   At the moment I have not had time to write complex extractors yet, due to
   work/time constraints, but I will soon write a system to selectively publish
   lots of disparate documents using Nabu and the extractors I will write for
   this will come with the Nabu distribution. I'll be happy to include external
   contributions of extractor codes in the distribution if anyone cares to
   provide them.


Target Audience
---------------

This system is made to be a simple as possible to use.  However, it is not
designed for your mother.  In order to be able to use this efficiently, you must

1. understand the conventions and simple no-markup syntax of reStructuredText_;
2. be able to edit simple text files.

I suspect that this will cater to people who are already familiar with
computers.


For more details, see the design document and project proposal under the
``doc`` subdirectory.


Features
========

Nabu is cool, because:

- it is flexible: you can use

  * any text editor you like to edit the files;
  * any source code control system you like to store and maintain them (or
    none);
  * any database for storage;
  * and any web application framework for presentation.  Nabu does not
    dictate how the information is presented/served to the clients;

- you edit files *locally*, not in a bleeping web browser window (programmers
  will appreciate the value of this), in your favourite editor environment;

- the organization of the source files in subdirectories has *nothing* to do
  with how the content is presented.  We use a unique ID system (similar to
  arch) where your document to be published must contain a unique string to mark
  it with that id.  You can put that string in a reStructuredText_ comment or a
  bibliographic field.  Unlike Wikis, this allows you to change the title of
  your documents while keeping the possibility of a permanent link to them.

  It effectively offers you a sandbox for creating content, and then how you
  organize and present the content is dictated by ways that *you* decide, most
  likely independent of the source file organization structure;

- the input data can be scattered over many files, it does not have to be stored
  in files per-category (for example, you don't have to store all your
  "contacts" in a single "address book" file, they can be found within/across
  all your body of published file and a server might present as a single list if
  desired).  I conjecture that this may be closer to how humans think of this
  data.  This body of files can be used to create a mind-mapping system;

- we recognize that the value of the information lies in the source itself, the
  text files.  This valuable source remains *with you*, and you are free to
  manage them in any way you prefer, with any version control system you like
  (if you want to do that).  You can completely dump the data stored in the
  database and rebuild it from the text files;

- various semantic chunks of content are automatically extracted from your
  document.  These semantic things are easily written with little code and are
  configurable.  Nabu comes with example content extractors;

- a light-weight program with minimal dependencies is used to upload the files
  to the server.  The server processes the files for content.  This maximizes
  the potential that you will be able to use Nabu anywhere, on any platform.
  The client only requires Python to work;


Nabu is not ...
---------------

Not a Wiki
  Although we upload documents (like Wiki pages) to a server, it may
  be that the presentation layer never serves the pages/documents themselves.
  Maybe it just serves bits of information extracted from the files.  Also,
  documents are identified by a unique string, and not by Wiki names.  This
  allows one to use whatever title for single documents and to create permanent
  links to specific documents (as long as the file ID is maintained);

Not just a Blogging system
  It can be used to add any document set to a database.
  Organization by date and category is simply implemented, but not a
  requirement.  You present the data set (which can be anything) in your
  preferred manner.

  You could, however, very easily implement a flexible and very complete
  blogging system using Nabu.

Not a Word Processing system
  It is not meant to just serve documents.  You
  can use it to publish just the information that is found within documents,
  used to contain that information.

  Also, you write your documents locally, but they have the limitations of
  reStructuredText_, so it is not really like a Word processing system.  You
  must use a simple text editor.

Not a generic data entry format
  Although you could potentially use it to
  enter larges lists of similarly structured data, the overhead of document
  processing does not make it the most efficient way to do this.  If you have
  *lots* of similarly structured bits of human-editable data, it would probably
  be better to write custom code to parse a known format rather than leverage
  Nabu for this.  The docutils_ processing on the server is not extremely fast,
  and if you need speed for lots of data (say, thousands of files), you will
  probably find this too slow.

  However, for smaller sets of files, Nabu could be used this way.  Or if you
  have to input various kinds of structures within different contexts which can
  be grouped in files.

Nabu sits between all these things.  I do not know what to call it, so I just
call it "Nabu".


Documentation
=============

For Content Writers
-------------------

- `Usage <doc/nabu-usage.html>`_: usage instructions for content pushers;

Technical
---------

- `Server Setup <doc/nabu-server.html>`_: instructions for installing and
  configuring a Nabu server;

- `Writing an Extractor <doc/nabu-extractor.html>`_: an example extractor source
  code, with details and commentary.  Since you are expected to provide or at
  least configure your own extractors for your application, this will be useful
  if you intend to put Nabu to good use.  This could also help you understand
  more precisely the nature of what Nabu actually provides and what it does not
  provide;

- `TODO list <TODO>`_: list of future changes, broken things, etc.;

- `Change Log <CHANGES>`_: recent changes, history;


Design
------

- `Goals <doc/nabu-goals.html>`_: motivation behind this project, history of
  what led me to implement this;

- `Design <doc/nabu-design.html>`_: conceptual design and software architecture;

- `Future <doc/nabu-ideas.html>`_: future, postponed or rejected ideas. Stuff
  that I would like to do that is not on the immediate list;


Talks
-----

- PyCon 2006 Presentation `(PDF) <doc/talks/pycon2006.pdf>`_


Test Drive Nabu
---------------

- `Test Drive`_: test drive Nabu on our server;


Download
========

You can download the `Nabu Publisher Client`__ and save it under the name
``nabu``.  Usage instructions can be found `here <doc/nabu-usage.html>`_.

__ /nabu/bin/nabu


A Mercurial repository can be found at:

  http://github.com/blais/nabu


It consists mostly of server code, but it also contains the publisher
client. When I get some feedback I will decide on the version number.

.. important:: You will need a recent snapshot of the docutils svn development
   	       tree (after stamp 3624) to be able to install and run a server.
   	       This does not affect clients.

Stability is a relative matter.  Personally, I consider these snapshots to
correspond to a beta stability for a 1.0 release.  I'm already using the system
on personal projects (works for me), and I'm committed to fix bugs reported by
others.  When I get some feedback I will select version number (probably 1.0).


Reporting Bugs
==============

Send email to the author: Martin Blais <blais@furius.ca>.


Links
=====

Some links to projects with similar goals, or that have some kind of conceptual
relation:

- `DEVONthink <http://www.devon-technologies.com/products/devonthink/>`_
- `PI Corporation <http://www.picorp.com/>`_



Installation and Dependencies
=============================

Nabu Publisher Client
  A single file written in Python.

  The publisher finds files on the local client filesystem and figures out which
  ones are meant for publication by detecting the ids within the top of the
  files, connects to the Nabu Server and asks for comparison of the files and
  incrementally uploads the files that have changed to update the content on the
  server.  The client code may also contain a easy-to-use editor for source
  files.

  Requires Python-2.3 or greater (and perhaps some kind of shell environment to
  invoke the Python script with some arguments (cmd.exe that comes with Windows
  can do the job)).  That's it.


Nabu Server / Publisher Handler
  Receives updates of the source files from the publisher client, helps the
  client figure out which files have changed since the last update by serving
  MD5 sums of the files it has processed, and makes the necessary updates.  The
  content is stored in a database after having been parsed.

  We provide generic handler code for the publisher server, which you can bind
  to a CGI script with XML-RPC (very simple) or within your own server system
  (if you can write a little bit of Python code, still very simple).  On the
  server, you must have:

  - `Python-2.4 <http://python.org>`_ or greater;
  - docutils_;

  - if you use a database backend, whatever SQL DBAPI connector.
    Right now the application works using pyscopg2, but it could be ported very
    easily to another DBAPI-2.0 connector object, or to write to files.


Presentation Layer
  This is up to you.  Nabu does not provide nor dictate the way in which you
  present your content, it only deals with the upload and processing of the
  source documents and the storage of extracted information.  You can use any
  computer language or framework you prefer to build a front-end for data fed
  into a database by Nabu.

  However, we provide a simple CGI script that allows you to browse the uploaded
  contents for debugging and visualizing what has been stored in the Nabu
  database.


Copyright and License
=====================

Copyright (C) 2005  Martin Blais.
This code is distributed under the `GNU General Public License <COPYING>`_.


Acknowledgements
================

This project uses two important libraries to do its thing:

- the `Docutils <http://docutils.sourceforge.net>`_ project (written mostly by
  Dave Goodger), which provides the reStructuredText parser, the internal
  document structure, and the HTML writer (and more).  Docutils is a major
  facilitator for this system--without it this idea probably would not have seen
  the light of day;

It is also built in the Python language.


Author
======

Martin Blais <blais@furius.ca>

..  "Text files are forever"
..  --Martin

.. _docutils: http://docutils.sourceforge.net
.. _reStructuredText: http://docutils.sourceforge.net/rst.html
.. _Test Drive: doc/nabu-beta.html
