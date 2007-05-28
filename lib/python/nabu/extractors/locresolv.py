# -*- coding: iso-8859-1 -*-
"""
Storage and resolver for partial location names + orderings.

This table and algorithm allows us to specify partial location names, and to
dynamically resolve the name into the longest possible location name.
"""

# stdlib imports
import string
from itertools import izip
import codecs 
from pprint import pprint

# misc support imports
try:
    import latscii
except ImportError:
    import hume.util.latscii

# antiorm imports
from antiorm import *
from antipool import dbpool, ConnOp

## FIXME: this module is placed "on hold" because of the dependency it
## introduces on antiorm.  It also needs to be completed (see FIXME notes
## below).




schemas = (

    #-----------------------------------------
    ('location_ordering', 'TABLE',
     """

      -- Note that both 'name' and 'parent' are keynames.
      CREATE TABLE location_ordering
      (
         -- Unique id for the location the name came from
         locid INTEGER NOT NULL,

         -- The short name to match against
         name TEXT NOT NULL,

         -- The parent node
         parent TEXT,

         -- Each location can only contain a name once (this is a
         -- constraint we impose due to our resolution algorithm)
         PRIMARY KEY (locid, name)
      )

      """),

    #-----------------------------------------
    ('locid_idx', 'INDEX',
     "CREATE INDEX locid_idx ON location_ordering(locid)"),

    #-----------------------------------------
    ('name_idx', 'INDEX',
     "CREATE INDEX name_idx ON location_ordering(name)"),

    #-----------------------------------------
    ('locid_seq', 'SEQUENCE',
     "CREATE SEQUENCE locid_seq START WITH 1"),

    #-----------------------------------------
    ('location_pretty', 'TABLE',
     """

      CREATE TABLE location_pretty
      (
         -- The key name
         keyname TEXT PRIMARY KEY,

         -- The beautiful name
         srcname TEXT NOT NULL
      )

      """),

    #-----------------------------------------
    ('location_cache', 'TABLE',
     """

      CREATE TABLE location_cache
      (
         -- Unique id for the location the name came from
         locid SERIAL PRIMARY KEY,

         -- The fully rendered name
         rendered TEXT NOT NULL
      )

      """),
    )



class Locations(MormTable):
    table = 'location_ordering'
    converters = {}

    @classmethod
    def add(cls, location_field):
        """
        Given a string that represents a place in the world, split it and add
        its contents to the table of orderings.  Return a new location id for
        the given location field.  If you pass in strings, they will be assumed
        to be encoded in UTF-8 encoding (the better way is to do the decoding on
        your side and pass in unicode objects).
        """
        if not isinstance(location_field, unicode):
            location_field = location_field.decode('utf-8')

        keysrc_pairs = field2both(location_field)
        words = [x[0] for x in keysrc_pairs]

        conn, cursor = dbpool().connection(1)
        try:
            # FIXME: Eventually we want to be able to recycle the location
            # ids, because we're going to overflow.
            cursor.execute("""
               SELECT nextval('locid_seq');
             """)
            locid = cursor.fetchone()[0]

            it = izip([None] + words, words + [None])
            it.next()
            for w1, w2 in it:
                cursor.execute('''
                   INSERT INTO location_ordering
                      (locid, name, parent)
                      VALUES (%s,  %s, %s)
                ''', (locid, w1, w2))

            for key, src in keysrc_pairs:
                PrettyLocations.update(key, src)

            conn.commit()
            return locid
        finally:
            conn.release()

    @classmethod
    def get_raw_location(cls, locid):
        """
        Reconstructs the list of location names for the given location id.
        Return a list of words.
        """
        lmap = {}
        for o in ConnOp(cls).select_all(
            "WHERE locid = %s", (locid,), cols=('name', 'parent')):
            lmap[o.parent] = o.name

        curname = lmap.pop(None)
        locs = [curname]
        while lmap:
            curname = lmap.pop(curname)
            locs.append(curname)

        locs.reverse()
        return locs

    @classmethod
    def get_location(cls, locid):
        """
        Get the resolved location for the given location id, that id given the
        source document locid, find the source location words, and reconstruct
        the complete set of words from them.
        """
        rawloc = cls.get_raw_location(locid)

        resolved = cls.resolve(rawloc)
        if resolved:
            resolved = PrettyLocations.beautify(resolved)
        return PrettyLocations.beautify(resolved)

    @classmethod
    def resolve_name(cls, location_field):
        """
        Given a source location name, split the words and resolve the complete
        set of location words from them.
        """
        resolved = cls.resolve(field2keys(location_field))
        if resolved:
            resolved = PrettyLocations.beautify(resolved)
        return resolved
        
    @classmethod
    def resolve(cls, location_names):
        """
        Given a sequence of potentially incomplete location names, resolve the
        location into the full list of location names.  The full table is used
        to resolve the given name to its fullest.  If the result is ambiguous,
        return None; Otherwise return a sequence of the full list of names.
        """
        conn, cursor = dbpool().connection(1)
        try:
            # First fetch all the possible database relations starting from the
            # first name.  We do this to avoid querying the database twice for
            # nothing (we cache all the required information in a dict).
            firstname = location_names[0]

            rels = {}
            todo = [firstname]
            while todo:
                cur = todo.pop()
                if cur in rels:
                    continue

                cursor = conn.cursor()
                cursor.execute("""
                   SELECT DISTINCT parent FROM location_ordering
                     WHERE name = %s
                 """, (cur,))
                if cursor.rowcount > 0:
                    parents = [x.parent for x in
                               cls.decoder( ('parent',) ).iter(cursor)]

                    rels[cur] = parents
                    todo.extend(parents)

        finally:
            conn.release()

        # Not found.
        if not rels:
            return []

        # Compute all the possible paths that end with None.  Detect cycles.
        def rec(curnode, path, paths):
            path.append(curnode)
            for sub in rels[curnode]:
                if sub is None:
                    paths.append(list(path))
                else:
                    rec(sub, path, paths)
            path.pop(-1)

        paths = []
        rec(firstname, [], paths)

        # Filter out the paths that are not supersets of our set of words.
        nameset = frozenset(location_names)
        paths = [x for x in paths if nameset.issubset(x)]

        # Take the longest.
        paths.sort(key=len, reverse=1)
        longest = paths[0]

        # Make sure all the other ones are subsets of the longest.
        longest_set = frozenset(longest)
        for other in paths[1:]:
            if not frozenset(other).issubset(longest_set):
                raise ValueError("Ambiguous path: %s" % other)

        return longest

    @classmethod
    def astree(cls):
        """
        Produce a tree of location names, from all the information in the
        database.  Return a tree of nodes, each consisting in (name, children)
        pairs (tuples).
        """
        conn, cursor = dbpool().connection(1)
        try:
            # Note: this is a terribly inefficient algorithm, and we don't care,
            # because it is meant to be used for debugging only.
            cursor.execute("""
               SELECT name FROM location_ordering
             """)
            dec = MormDecoder(cls, cursor)
            plocs = set()
            for o in dec.iter(cursor):
                resolved = cls.resolve([o.name])
                # This reduction here could be instead done in a single step.
                plocs.add(tuple(reversed(PrettyLocations.beautify(resolved))))

            locmap = {None: ('<World>', [])}
            for loclist in sorted(plocs):
                newname = loclist[-1]
                if len(loclist) == 1:
                    parent = None
                else:
                    parent = loclist[-2]
                l = locmap[newname] = (newname, [])
                locmap[parent][1].append(l)

            tree = locmap[None]

            return tree
        finally:
            conn.release()

    @classmethod
    def search(cls, terms):
        """
        Run a search on the keynames, and then resolve all the matching ones.
        Return a list of resolved sequences.
        """
        conn, cursor = dbpool().connection_ro(1)
        try:
            cursor.execute("""
              SELECT DISTINCT name FROM location_ordering
                WHERE name LIKE %s
            """, ('%%%s%%' % '%'.join(terms),))
            it = [x[0] for x in cursor.fetchall()]
        finally:
            conn.release()

        return [Locations.resolve_name(name.decode('UTF-8')) for name in it]

## FIXME: we need to deal with removal of location ids
## FIXME: we need a cache for lookups (work is started below)



























class PrettyLocations(MormTable):
    """
    This table contains a mapping from keys to the full names
    """
    table = 'location_pretty'
    converters = {
        'srcname': MormConvUnicode(),
    }

    @classmethod
    def beautify(cls, keynames):
        """
        Given a sequence of keynames, find the prettier versions of those names
        and return a sequence of beautified words.  This essentially maps via
        the pretty words table map.
        """
        conn, cursor = dbpool().connection_ro(1)
        try:
            pnames = []
            for kname in keynames:
                o = cls.get(conn, keyname=kname)
                pnames.append(o.srcname)
            return pnames
        finally:
            conn.release()

    @classmethod
    def update(cls, key, src):
        """
        Make sure we have the most beautiful mapping for the given keyname in
        the table.
        """
        assert isinstance(key, str) and isinstance(src, unicode)
        conn, cursor = dbpool().connection(1)
        try:
            try:
                o = cls.get(conn, keyname=key)

                # We use the longest utf-8 encoded string, thinking that the
                # more accents the string has the more space it takes, and that
                # the more accents it has, the better.  This is rather
                # simplistic, but it seems to do what I need for location names.
                if len(src.encode('utf-8')) > len(o.srcname.encode('utf-8')):
                    cursor.execute('''
                       UPDATE location_pretty
                         SET srcname = %s
                         WHERE keyname = %s
                    ''', (src, key))
                    conn.commit()
            except MormError:
                cursor.execute('''
                   INSERT INTO location_pretty
                      (keyname, srcname)
                      VALUES (%s, %s)
                ''', (key, src))
                conn.commit()
        finally:
            conn.release()


def field2keys(location_field):
    """
    Convert a string that represents a comma-separated list of location names
    and return a sequence of keynames for it.
    """
    return [keyname(x.strip()) for x in location_field.split(',')]

def field2both(location_field):
    """
    Convert a string that represents a comma-separated list of pairs of
    (keyname, source name).
    """
    return [(keyname(w), w)
            for w in [x.strip() for x in location_field.split(',')]]



class LocationCache(MormTable):
    """
    This table contains a cache of location ids to rendered
    names.  Note that this cache must be completely cleared every
    time a new location is entered, because it may completely
    change the way that the output gets rendered.
    """
    table = 'location_pretty'
    converters = {
        'rendered': MormConvUnicode(),
    }

    @classmethod
    def get_location(cls, locid):
        pass
## FIXME: todo
## FIXME todo complete this caching system.











        






def keyname(srcname):
    """
    Convert a source location name to the a name that is normalized for better
    matches.  For example, we remove the diacritics, and any non-alphanumeric
    characters.
    """
    if srcname is None:
        return None
    assert isinstance(srcname, unicode)

    name = srcname.encode('latscii').replace('.', '').replace('-', '').lower()
    
    return name




if __name__ == '__main__':

    import sys, pdb, unittest, logging
    from os.path import join, dirname

    # dbapi imports
    import psycopg2 as dbapi

    # antiorm imports
    import antipool


    class TestOrderings(unittest.TestCase):
        """
        Test the partial orderings.
        """
        def setUp(self):
            antipool.initpool(
                antipool.ConnectionPool(dbapi,
                                        database='test',
                                        user='blais'))

            conn, cursor = dbpool().connection(1)
            for name, stype, entity in schemas:
                query = "DROP %s %s;" % (stype, name)
                try:
                    cursor.execute(query)
                    conn.commit()
                except dbapi.Error:
                    conn.rollback()

            for name, stype, entity in schemas:
                cursor.execute(entity)

            conn.commit()


        #-----------------------------------------------------------------------
        #
        data_simple = (
            'Montreal, Quebec, Canada',
            'Montreal, Canada',
            'Toronto, Ontario',
            'Ontario, Canada',
            'Hamilton, Ontario, Canada',
            'Ontario, Canada',
            )

        def test_simple(self):
            "Simple test."
            ids = [(x, Locations.add(x)) for x in self.data_simple]

            # Check that we can fetch these values back from the database.
            for loc, locid in ids:
                words = [x.strip() for x in loc.split(',')]
                self.assertEquals(words,
                                  Locations.get_raw_location(locid))
        
        def test_truestory(self):
            "True story: use some real data."
            ids = load_truestory()

            # Check that we can fetch these values back from the database.
            for loc, locid in ids:
                resolved = Locations.get_location(locid)
                print loc, '   ->   ', u', '.join(resolved)

            # Print a nice hierarchical rendering of the tree.
            tree = Locations.astree()

            def print_node(node, level=0):
                name, children = node
                print '    ' * level, name
                for child in children:
                    print_node(child, level+1)
            print_node(tree)
            
        #-----------------------------------------------------------------------
        #
        def test_resolve(self):
            "Test resolver."

            def prepare(*dataset):
                self.setUp()
                return dict((x, Locations.add(x)) for x in dataset)

            ids = prepare('A, B, D',
                          'A, C, D')

            self.assertRaises(ValueError, Locations.resolve_name, u'A, D')
            self.assertEquals(Locations.resolve_name(u'A, B, D'),
                              ['A', 'B', 'D'])
            self.assertEquals(Locations.resolve_name(u'A, C, D'),
                              ['A', 'C', 'D'])
            self.assertEquals(Locations.resolve_name(u'A, B'),
                              ['A', 'B', 'D'])

            self.assertEquals(Locations.resolve_name(u'D'),
                              ['D'])
            self.assertEquals(Locations.resolve_name(u'C'),
                              ['C', 'D'])


            prepare('A, B, C, D',
                    'A, E, D')

            self.assertRaises(ValueError, Locations.resolve_name, u'A, D')
            self.assertEquals(Locations.resolve_name(u'A, B, D'),
                              ['A', 'B', 'C', 'D'])
            self.assertEquals(Locations.resolve_name(u'A, C, D'),
                              ['A', 'B', 'C', 'D'])
            self.assertEquals(Locations.resolve_name(u'A, E, D'),
                              ['A', 'E', 'D'])


            prepare('A, B, D, E',
                    'A, C, D')

            self.assertRaises(ValueError, Locations.resolve_name, u'A, D')
            self.assertRaises(ValueError, Locations.resolve_name, u'A, E')


            prepare('A, B, C')

            self.assertEquals(Locations.resolve_name(u'A, C'),
                              ['A', 'B', 'C'])


            prepare('A, B, C',
                    'A, C')

            self.assertEquals(Locations.resolve_name(u'A, C'),
                              ['A', 'B', 'C'])


            prepare('A, B, C, D',
                    'A, C')

            self.assertEquals(Locations.resolve_name(u'A, D'),
                              ['A', 'B', 'C', 'D'])


            prepare('A, B, C, D',
                    'A, D')

            self.assertEquals(Locations.resolve_name(u'A, D'),
                              ['A', 'B', 'C', 'D'])


            prepare('A, B, C, D, E',
                    'A, D')

            self.assertEquals(Locations.resolve_name(u'A, D, E'),
                              ['A', 'B', 'C', 'D', 'E'])


            prepare('A, B, C',
                    'A, X, Y, C')

            self.assertEquals(Locations.resolve_name(u'A, B'),
                              ['A', 'B', 'C'])


            prepare('A, B, C, D',
                    'A, X, C',
                    'X, D')

            self.assertEquals(Locations.resolve_name(u'A, B'),
                              ['A', 'B', 'C', 'D'])
            self.assertEquals(Locations.resolve_name(u'A, B, D'),
                              ['A', 'B', 'C', 'D'])


            prepare('A, B, C, D, E',
                    'A, X, E')

            self.assertEquals(Locations.resolve_name(u'A, D, E'),
                              ['A', 'B', 'C', 'D', 'E'])


            prepare('A, B, C',
                    'A, W, X, Y, Z, C')

            self.assertEquals(Locations.resolve_name(u'A, B, C'),
                              ['A', 'B', 'C'])


    def suite():
        suite = unittest.TestSuite()
        suite.addTest(TestOrderings("test_resolve"))
        suite.addTest(TestOrderings("test_simple"))
        suite.addTest(TestOrderings("test_truestory"))
        return suite

    def truestory():
        suite = unittest.TestSuite()
        suite.addTest(TestOrderings("test_truestory"))
        return suite

    def load_truestory():
        "Load my test data into a database table."
        data = [
            x.strip() for x in
            codecs.open(
              join(dirname(__file__), 'locresolv.testdata'),
              encoding='UTF-8')]
        return [(x, Locations.add(x)) for x in data]

    unittest.main(defaultTest='suite')



