#!/usr/bin/env python
# image_selector.py
# Maintained by G.Winter
# 
# A jiffy application to help with the determination of the best images
# to use for cell refinement. This is to test possible assertions as
# to which images will result in the smallest errors in the cell 
# parameters from the Mosflm cell refinement process.
# 
# Requires:
#
# Crystal lattice (e.g. tP)
# Mosflm orientation matrix
# Phi start, end, delta
# First image number
# Mosaic
#
# Will write to the standard output the appropriate "postref multi"
# spell for Mosflm.
#
# 28/SEP/07

import os
import sys
import math

if not os.environ['XIA2_ROOT'] in sys.path:
    sys.path.append(os.environ['XIA2_ROOT'])
    
if not os.environ['XIA2CORE_ROOT'] in sys.path:
    sys.path.append(os.path.join(os.environ['XIA2CORE_ROOT'], 'Python'))

from Driver.DriverFactory import DriverFactory

from Experts.MatrixExpert import get_reciprocal_space_primitive_matrix

def nint(a):
    b = int(a)
    if a - b > 0.5:
        b += 1
    return b

def find_best_images(lattice, matrix, phi_start, phi_end, phi_width,
                     first_image, mosaic):
    '''Find the best images to use for cell refinement, based on the
    primitive orientation of the crystal.'''

    astar, bstar, cstar = get_reciprocal_space_primitive_matrix(
        lattice, matrix)

    num_images = nint((phi_end - phi_start) / phi_width)

    dtor = 180.0 / (4.0 * math.atan(1.0))    

    min_a = 0
    min_b = 0
    min_c = 0
    min_a_val = 1.0e6
    min_b_val = 1.0e6
    min_c_val = 1.0e6
    max_a = 0
    max_b = 0
    max_c = 0
    max_a_val = 0.0
    max_b_val = 0.0
    max_c_val = 0.0
    

    for j in range(num_images):

        phi = (j + 0.5) * phi_width + phi_start

        c = math.cos(phi / dtor)
        s = math.sin(phi / dtor)
        
        dot_a = math.fabs(-s * astar[0] + c * astar[2])
        dot_b = math.fabs(-s * bstar[0] + c * bstar[2])
        dot_c = math.fabs(-s * cstar[0] + c * cstar[2])        

        if dot_a < min_a_val:
            min_a = j
            min_a_val = dot_a

        if dot_a > max_a_val:
            max_a = k
            max_a_val = dot_a

        if dot_b < min_b_val:
            min_b = j
            min_b_val = dot_b

        if dot_b > max_b_val:
            max_b = k
            max_b_val = dot_b

        if dot_c < min_c_val:
            min_c = j
            min_c_val = dot_c

        if dot_c > max_c_val:
            max_c = k
            max_c_val = dot_c

    # next digest these - first put them in order, then define
    # wedges around them, then tidy up the resulting blocks

    best_images = [min_a, min_b, min_c, max_a, max_b, max_c]
    best_images.sort()

    half = max(2, nint(mosaic / phi_width))

    if best_images[0] < half:
        wedges = [(0, 2 * half)]
    else:
        wedges = [(best_images[0] - half, best_images[0] + half)]

    for i in best_images[1:]:
        handled = False
        
        for j in range(len(wedges)):
            if (i - half) < wedges[j][1]:
                # just stretch this wedge..
                wedges[j] = (wedges[j][0], wedges[j][i + half])
                handled = True
                break

        if not handled:
            wedges.append((i - half, i + half))

    # next print these wedges
    print 'postref multi segments %d' % len(wedges)

    for w in wedges:
        print 'process %d %d' % w
        print go

    return

def MosflmJiffy(DriverType = None):

    DriverInstance = DriverFactory.Driver(DriverType)    

    class MosflmJiffyClass(DriverInstance.__class__):
        '''A wrapper for mosflm for a specific purpose.'''

        def __init__(self):
            self.set_executable('ipmosflm')

            self._image_range = None
            self._commands = None
            self._wedge_width = None
            self._num_wedges = 1

            # this will be keyed by the wedge middle images
            # used for cell refinement and contain sigmas
            # for a b c alpha beta gamma
            
            self._results = { }

        def set_image_range(self, image_range):
            self._image_range = image_range

        def set_commands(self, command_file):
            self._commands = []
            for record in open(command_file, 'r').readlines():
                if 'process' in record:
                    continue
                if 'postref multi' in record:
                    continue
                if record.strip() == 'go':
                    continue
                self._commands.append(record)

        def set_wedge_width(self, wedge_width):
            self._wedge_width = wedge_width

        def set_num_wedges(self, num_wedges):
            self._num_wedges = num_wedges

        def run(self):

            blocks = int((image_range[0] - image_range[1] / self._wedge_width))

            self.start()

            for record in self._commands:
                self.input(record)

            blocks = []

            for i in range(blocks):
                if self._num_wedges < 1:
                    continue

                for j in range(i, blocks):
                    if self._num_wedges < 2:
                        continue

                    for k in range(j, blocks):
                        if self._num_wedges < 3:
                            continue

                        for l in range(k, blocks):
                            if self._num_wedges < 4:
                                continue

                            for m in range(l, blocks):
                                if self._num_wedges < 5:
                                    continue

                                for n in range(m, blocks):
                                    if self._num_wedges < 6:
                                        continue

                                    blocks.insert(
                                        0, (n * self._wedge_width,
                                            (n + 1) * self._wedge_width))

                                blocks.insert(
                                    0, (m * self._wedge_width,
                                        (m + 1) * self._wedge_width))

                            blocks.insert(
                                0, (l * self._wedge_width,
                                    (l + 1) * self._wedge_width))
                            
                        blocks.insert(
                            0, (k * self._wedge_width,
                                (k + 1) * self._wedge_width))
                        
                    blocks.insert(
                        0, (j * self._wedge_width,
                            (j + 1) * self._wedge_width))
                    
                blocks.insert(
                    0, (i * self._wedge_width,
                        (i + 1) * self._wedge_width))

            self.input('postref multi segments %d' % \
                       len(blocks))

            for b in blocks:
                self.input('process %d %d' % b)
                self.input('go')

            self.close_wait()

            output = self.get_all_output()

            for j in range(len(output)):
                
                
                
