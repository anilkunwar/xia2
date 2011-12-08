#!/usr/bin/env python
# test_scan.py
#   Copyright (C) 2011 Diamond Light Source, Graeme Winter
#
#   This code is distributed under the BSD license, a copy of which is 
#   included in the root directory of this package.
#
# Tests for the scan class, and it's helper classes.

import math
import os
import sys
import time

sys.path.append(os.path.join(os.environ['XIA2_ROOT']))

from dxtbx.model.scan import scan
from dxtbx.model.scan import scan_factory
from dxtbx.model.scan_helpers import scan_helper_image_files
from dxtbx.model.scan_helpers import scan_helper_image_formats

def work_helper_image_files():
    '''Test the static methods in scan_helper_image_files.'''

    helper = scan_helper_image_files()

    directory = os.path.join(os.environ['XIA2_ROOT'], 'dxtbx', 'model',
                             'tests')
    
    template = 'image_###.dat'

    assert(len(scan_helper_image_files.template_directory_to_indices(
        template, directory)) == 20)
    
    assert(scan_helper_image_files.template_directory_index_to_image(
        template, directory, 1) == os.path.join(directory, 'image_001.dat'))
    
    assert(scan_helper_image_files.template_index_to_image(
        template, 1) == 'image_001.dat')
    
    assert(scan_helper_image_files.image_to_template_directory(
        os.path.join(directory, 'image_001.dat')) == (template, directory))
    
    assert(scan_helper_image_files.image_to_index('image_001.dat') == 1)
    
    assert(scan_helper_image_files.image_to_template(
        'image_001.dat') == 'image_###.dat')
    
    return

def work_helper_image_formats():
    '''Test the static methods and properties in scan_helper_image_formats.'''
    
    assert(scan_helper_image_formats.check_format(
        scan_helper_image_formats.FORMAT_CBF))
    assert(not(scan_helper_image_formats.check_format('CBF')))
    
def work_xscan_factory():
    '''Test out the scan_factory.'''

    directory = os.path.join(os.environ['XIA2_ROOT'], 'dxtbx', 'model',
                             'tests')
    
    template = 'image_###.dat'
    
    xscans = [scan_factory.single(
        scan_helper_image_files.template_directory_index_to_image(
            template, directory, j + 1), scan_helper_image_formats.FORMAT_CBF,
        1.0, 18 + 0.5 * j, 0.5, j) for j in range(20)]

    xscans.reverse()

    try:
        print sum(xscans[1:], xscans[0])
        print 'I should not see this message'
    except AssertionError, e:
        pass

    xscans.sort()
    print sum(xscans[1:], xscans[0])

    a = scan_factory.add(xscans[:10])
    b = scan_factory.add(xscans[10:])

    print a + b

    filename = scan_helper_image_files.template_directory_index_to_image(
        template, directory, 1)
    
    assert(len(scan_factory.search(filename)) == 20)

    print (a + b)[1:5]
    print (a + b)[:10]

    cbf = os.path.join(directory, 'phi_scan_001.cbf')

    print scan_factory.imgCIF(cbf)
    
if __name__ == '__main__':

    work_helper_image_files()
    work_helper_image_formats()
    work_xscan_factory()

    

    
