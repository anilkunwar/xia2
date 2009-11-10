#!/usr/bin/env python
# PyChef.py
# 
#   Copyright (C) 2009 Diamond Light Source, Graeme Winter
#
#   This code is distributed under the BSD license, a copy of which is 
#   included in the root directory of this package.
#
# Main program for PyChef, using the PyChef class. Here is some example input:
# 
# labin BASE=DOSE
# range width 5 max 605
# anomalous on
# resolution 1.9
#
# This is the same program interface as used to come from the program CHEF.
#

import os
import sys
import time

from PyChef import PyChef

def get_hklin_files():
    '''From the command-line, get the list of hklin files. Set up thus
    as it may be useful externally. Assumes that the list of reflection
    files is passed in as HKLIN1 infl.mtz etc. N.B. could well be the case
    that HKLIN infl.mtz HKLIN lrem.mtz works just as well, though thats
    just a side-effect.'''

    hklin_files = []

    for j in range(1, len(sys.argv)):
        if 'HKLIN' in sys.argv[j].upper()[:5]:
            hklin = sys.argv[j + 1]

            if not os.path.abspath(hklin):
                hklin = os.path.join(os.getcwd(), hklin)

            if not os.path.exists(hklin):
                raise RuntimeError, 'hklin %s does not exist' % hklin
            
            hklin_files.append(hklin)

    return hklin_files

def parse_standard_input():
    '''Read and parse the standard input. Return as a dictionary.'''

    range_min = 0.0
    range_max = None
    range_width = None

    anomalous = False

    resolution_low = None
    resolution_high = None

    base_column = None

    title = None

    for record in sys.stdin.readlines():

        record = record.split('!')[0].split('#')[0]

        if not record.strip():
            continue

        key = record[:4].upper()
        tokens = record.split()

        #### KEYWORD RESOLUTION ####
        
        if key == 'RESO':
            assert(len(tokens) < 4)
            assert(len(tokens) > 1)            

            if len(tokens) == 2:
                resolution_high = float(tokens[1])
                
            elif len(tokens) == 3:
                resolution_a = float(tokens[1])
                resolution_b = float(tokens[2])
                resolution_high = min(resolution_a, resolution_b)
                resolution_low = max(resolution_a, resolution_b)

        #### KEYWORD RANGE ####

        elif key == 'RANG':
            assert(len(tokens) < 8)
            assert(len(tokens) > 2)            

            for j in range(1, len(tokens)):
                subkey = tokens[j][:4].upper()
                if subkey == 'MIN':
                    range_min = float(tokens[j + 1])
                elif subkey == 'MAX':
                    range_max = float(tokens[j + 1])
                if subkey == 'WIDT':
                    range_width = float(tokens[j + 1])
                    
        #### KEYWORD ANOMALOUS ####

        elif key == 'ANOM':
            assert(len(tokens) < 3)

            anomalous = True

            if len(tokens) > 1:
                if tokens[1].upper() == 'OFF' or \
                   tokens[1].upper() == 'FALSE' or \
                   tokens[1].upper() == 'NO':
                    anomalous = False

        #### KEYWORD LABIN ####

        elif key == 'LABI':
            assert(len(tokens) == 2)
            assert('BASE=' in tokens[1])

            base_column = tokens[1].replace('BASE=', '')

        elif key == 'TITL':
            keyword = tokens[0]
            title = record[len(keyword):].strip()

    # check that these values are sound - where they are needed...
    # assert(base_column)

    # if we have BATCH we can guess the limit and range...
    # assert(range_max)
    # assert(range_width)

    # now drop this lot to a dictionary

    results = {
        'range_min':range_min,
        'range_max':range_max,
        'range_width':range_width,
        'anomalous':anomalous,
        'resolution_high':resolution_high,
        'resolution_low':resolution_low,
        'base_column':base_column
        }

    return results
        
def main():
    '''Create and run a PyChef, reading the traditional format input from
    the command-line.'''

    hklin_list = get_hklin_files()
    standard_input = parse_standard_input()

    pychef = PyChef()

    # copy the information across from the standard input dictionary to
    # the PyChef instance.

    if standard_input['base_column']:
        pychef.set_base_column(standard_input['base_column'])

    if standard_input['range_max']:
        pychef.set_range(standard_input['range_min'],
                         standard_input['range_max'],
                         standard_input['range_width'])
        
    pychef.set_resolution(standard_input['resolution_high'],
                          standard_input['resolution_low'])
    pychef.set_anomalous(standard_input['anomalous'])

    for hklin in hklin_list:
        pychef.add_hklin(hklin)

    # right, all set up - let's run some analysis - first the completeness
    # vs. dose for each input reflection file

    pychef.init()
    pychef.print_completeness_vs_dose()
    pychef.scp()    

if __name__ == '__main__':

    if False:

        import profile
        profile.run('main()')

    else:
        main()

    
