import optparse
import os
import os.path
import re
import subprocess
import sys
import time
import unittest
import anydbm
import UserDict
import tempfile

################################################################################
##
##  Database
##
################################################################################
class Database(UserDict.DictMixin):
    def __init__(self, filename):
        self.filename = filename
        self._dbm = None
        self._open()
        self._close()

    def _open(self):
        self._dbm = anydbm.open(self.filename, 'c')

    def _close(self):
        if self._dbm:
            self._dbm.close()

    def __getitem__(self, key):
        self._open()
        val = self._dbm[str(key)]
        self._close()
        return val

    def __setitem__(self, key, val):
        self._open()
        self._dbm[str(key)] = str(val)
        self._close()

    def __delitem__(self, key):
        self._open()
        del self._dbm[str(key)]
        self._close()

    def keys(self):
        self._open()
        keys = self._dbm.keys()
        self._close()
        return keys

################################################################################
##
##  TC_Database
##
################################################################################
class TC_Database(unittest.TestCase):
    filename = None

    def setUp(self):
        if not self.filename:
            (fd, self.filename) = tempfile.mkstemp()
            os.close(fd)
            try:
                os.unlink(self.filename)
            except OSError:
                pass

    def tearDown(self):
        try:
            os.unlink(self.filename)
        except OSError:
            pass

    def test_no_dir(self):
        try:
            db = Database(os.path.join(self.filename,'nofile'))
        except anydbm.error:
            pass
        else:
            self.fail("Expected exception opening database")

    def test_open(self):
        db = Database(self.filename)

    def test_write(self):
        db = Database(self.filename)
        db['abcd'] = '12345'
        self.assertEquals(db['abcd'], '12345')

    def test_update(self):
        db = Database(self.filename)
        db['abcd'] = '12345'
        db['abcd'] = '54321'
        self.assertEquals(db['abcd'], '54321')

    def test_del(self):
        db = Database(self.filename)
        db['abcd'] = '12345'
        db['efgh'] = '54321'
        db['ijkl'] = '13579'
        del db['efgh']
        self.assertRaises(KeyError, lambda: db['efgh'])

    def test_keys(self):
        db = Database(self.filename)
        db['abcd'] = '12345'
        db['efgh'] = '54321'
        self.assertEqual(len(db), 2)
        self.assertTrue('abcd' in db.keys())
        self.assertTrue('efgh' in db.keys())
        self.assertFalse('ijkl' in db.keys())

    def test_values(self):
        db = Database(self.filename)
        db['abcd'] = '12345'
        db['efgh'] = '54321'
        self.assertEqual(len(db), 2)
        self.assertTrue('12345' in db.values())
        self.assertTrue('54321' in db.values())
        self.assertFalse('88888' in db.values())

    def test_iter(self):
        db = Database(self.filename)
        db['abcd'] = '12345'
        db['efgh'] = '54321'
        db['ijkl'] = '13579'
        want = set(('abcd','efgh','ijkl'))
        got = set()
        for k in db:
            got.add(k)
        self.assertEqual(want,got)

    def test_iteritems(self):
        db = Database(self.filename)
        db['abcd'] = '12345'
        db['efgh'] = '54321'
        db['ijkl'] = '13579'
        want_k = set(('abcd','efgh','ijkl'))
        want_v = set(('12345','54321','13579'))
        got_k = set()
        got_v = set()
        for (k,v) in db.iteritems():
            got_k.add(k)
            got_v.add(v)
        self.assertEqual(want_k,got_k)
        self.assertEqual(want_v,got_v)

##############################################################################
##
##  main
##
##############################################################################
if __name__ == '__main__':
    unittest.main()
