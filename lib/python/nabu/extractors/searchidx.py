# -*- coding: utf-8 -*-
#
# Copyright (C) 2006  Martin Blais <blais@furius.ca>
# This file is distributed under the terms of the GNU GPL license.
# For more information: http://furius.ca/nabu.
#
# $Id$
#

"""
Extract search terms and creates a simple search index.

This does not use any rocket science technology, it just splits the incoming
rest file, maybe does a little bit of massaging and filtering on the extracted
terms, and stores them in a term index along that point to the document's unid.
This is extremely wasteful and stupid, and if you want something intelligent I
suggest you not enable this extractor and stop reading this right now.

However, it will do the job fine on reasonably sized personal document
collections (thousands?), and considering the insane power that sits on my
laptop in 2006 this will do the job my little personal vanity searching needs
for now (to those who say 'LAZY!' I scream back Knuth's words:  premature
optimization is the root of... well, you know, RELAX!).
"""

# stdlib imports
import sys, re, datetime

# docutils imports
from docutils import nodes

# nabu imports
from nabu import extract



bogus_kwds = frozenset("""

   all and are but can for have i'm it like more not one some that the there
   they this was what with you your when just our will from would much has very
   could been had those than don't me how them he she her

   """.split())



class Extractor(extract.Extractor):
    """
    Transform that extracts some basic information about the document as a
    whole.  For example, it extracts the title and some bibliographic fields.
    """
    default_priority = 900

    def apply(self, unid=None, storage=None, pickle_receiver=None):
        self.unid = unid
        self.storage = storage

        v = _Visitor(self.document)
        v.xform = self
        self.document.walk(v)

        self.storage.store(self.unid, v.dico)


class _Visitor(nodes.SparseNodeVisitor):

    def __init__(self, *args, **kwds):
        nodes.SparseNodeVisitor.__init__(self, *args, **kwds)

        self.dico = {}

    def visit_Text(self, node):
        parse_words(node.astext(), self.dico)


class Storage(extract.SQLExtractorStorage):
    """
    Document storage.

    Note: this is not necessarily meant to store the actual document, but rather
    stuff extracted from the document.  You may to use the document from the
    uploaded sources storage to render the entire document as HTML, this is ok.
    """

    sql_relations_unid = [
        ('search_index', 'TABLE', '''

            CREATE TABLE search_index
            (
               keyword VARCHAR(128) NOT NULL,
               unid VARCHAR(128) NOT NULL,
               count INTEGER
            );

        '''),
        ]

    sql_relations = [
        ('keyword_idx', 'INDEX',
         "CREATE INDEX keyword_idx ON search_index (keyword)"),

        ('unid_idx', 'INDEX', 
         "CREATE INDEX unid_idx ON search_index (unid)"),
        ]

    def store(self, unid, dico):
        """
        Expect a unid and a dictionary of words-to-counts.
        """
        # Expand the dictionary into a sequence of tuples.
        seqs = [(unid, word, count)
                for word, count in dico.iteritems()
                if len(word) <= 128]

        cursor = self.connection.cursor()
        cursor.executemany("""
           INSERT INTO search_index (unid, keyword, count)
             VALUES (%s, %s, %s)
           """, seqs)
        self.connection.commit()



def parse_words(terms, dico, neg_dico=None):
    """
    Transform the text into a list of words, and store them into the dict
    'dico', adding the counts for the words.
    """
    wsplit = terms.split()
    for word in [x.lower() for x in wsplit]:
        if len(word) <= 2:
            continue
        neg = word.startswith('-')
        word = word.strip(u',.[]()“"”\’\‘\'\`:;-—?!')
        if word.isdigit():
            continue
        if word.endswith(u"'s"):
            word = word[:-2]
        if word in bogus_kwds:
            continue
        if neg and neg_dico is not None:
            neg_dico[word] = neg_dico.get(word, 0) + 1
            continue
        dico[word] = dico.get(word, 0) + 1

def search(conn, search_str):
    """
    Perform a search on the given search string.  If there are multiple
    keywords, we split them and assume AND semantics.  If you insert - before a
    keyword, we reverse the meaning of the keyword.
    """
    assert isinstance(search_str, unicode)

    dico, negdico = {}, {}
    parse_words(search_str, dico, negdico)

    clause = '\n INTERSECT \n'.join(
        ['SELECT unid FROM search_index WHERE keyword = %s'
         for x in xrange(len(dico))])
    if negdico:
        neg_clause = '\n UNION \n'.join(
            ['SELECT unid FROM search_index WHERE keyword = %s'
             for x in xrange(len(negdico))])
        clause = '(%s) EXCEPT (%s)' % (clause, neg_clause)
    cursor = conn.cursor()
    
    words = dico.keys() + negdico.keys()
    cursor.execute(clause, words)
    return [x[0] for x in cursor.fetchall()]


