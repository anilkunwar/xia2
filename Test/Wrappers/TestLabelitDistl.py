#!/usr/bin/env python
# TestLabelitDistl.py
# Maintained by G.Winter
# 2nd June 2006
# 
# Unit tests to ensure that the LabelitDistl wrapper is behaving
# properly. Also added is the wrapper to stats_distl, since
# the results from this should be identical.
# 

import os, sys

if not os.environ.has_key('DPA_ROOT'):
    raise RuntimeError, 'DPA_ROOT not defined'

sys.path.append(os.path.join(os.environ['DPA_ROOT']))

from Wrappers.Labelit.LabelitDistl import LabelitDistl
from Wrappers.Labelit.LabelitStats_distl import LabelitStats_distl
import unittest

# this should be placed in a gwmath module or something...

def nint(a):
    b = int(a)
    if a - b > 0.5:
        b += 1
    return b

class TestLabelitDistl(unittest.TestCase):

    def setUp(self):
        pass

    def testtetragonal(self):
        '''A test to see if the screening works when it should.'''

        ld = LabelitDistl()

        directory = os.path.join(os.environ['DPA_ROOT'],
                                 'Data', 'Test', 'Images')

        ld.addImage(os.path.join(directory, '12287_1_E1_001.img'))
        
        ld.distl()

        stats = ld.getStatistics('12287_1_E1_001.img')

        # most of the spots are good
        self.assertEqual(nint(float(stats['spots_good']) /
                              float(stats['spots'])), 1)

        self.assertEqual(nint(stats['resol_one']), 2)
        self.assertEqual(nint(stats['resol_two']), 2)

        return

    def teststatsdistl(self):
        '''A test to see if the labelit.stats_distl wrapper is
        behaving as expected.'''

        ld = LabelitDistl()

        directory = os.path.join(os.environ['DPA_ROOT'],
                                 'Data', 'Test', 'Images')

        ld.addImage(os.path.join(directory, '12287_1_E1_001.img'))
        ld.distl()
        stats = ld.getStatistics('12287_1_E1_001.img')

        lsd = LabelitStats_distl()
        lsd.stats_distl()

        copy = lsd.getStatistics('12287_1_E1_001.img')

        self.assertEqual(stats, copy)

        return


if __name__ == '__main__':
    unittest.main()


    


