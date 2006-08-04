#!/usr/bin/env python
# Indexer.py
#   Copyright (C) 2006 CCLRC, Graeme Winter
#
#   This code is distributed under the terms and conditions of the
#   CCP4 Program Suite Licence Agreement as a CCP4 Library.
#   A copy of the CCP4 licence can be obtained by writing to the
#   CCP4 Secretary, Daresbury Laboratory, Warrington WA4 4AD, UK.
# 
# An interface for programs which perform indexing - this will handle
# all of the aspects of the interface which are common between indexing
# progtrams, and which must be presented in order to satisfy the contract
# for the indexer interface.
# 
# The following are considered to be critical for this class:
# 
# Images to index - optional this could be decided by the implementation
# Refined beam position
# Refined distance
# Mosaic spread
# 
# Input: ?Selected lattice?
# Input: ?Cell?
# Output: Selected lattice
# Output: Unit cell
# Output: Aux information - may include matrix files &c. This is going to
#         be in the "payload" and will be program specific.
# 
# Methods:
# 
# index() -> delegated to implementation._index()
#
# FIXME: getter methods should, if the results are NULL, initiate the index
#        process to allow pure constructor based (functional?) programming.
#
# Notes:
# 
# All properties of this class are prefixed with either indxr for protected
# things or Indexer for public things.
#
# Error Conditions:
# 

import os
import sys

if not os.environ.has_key('DPA_ROOT'):
    raise RuntimeError, 'DPA_ROOT not defined'

if not os.environ['DPA_ROOT'] in sys.path:
    sys.path.append(os.path.join(os.environ['DPA_ROOT']))

class Indexer:
    '''A class interface to present autoindexing functionality in a standard
    way for all indexing programs. Note that this interface defines the
    contract - what the implementation actually does is a matter for the
    implementation.'''

    def __init__(self):

        # (optional) input gubbinzes
        self._indxr_images = []
        self._indxr_input_lattice = None
        self._indxr_input_cell = None

        # job management parameters
        self._indxr_run = False
        
        # output items
        self._indxr_lattice = None
        self._indxr_cell = None
        self._indxr_mosaic = None
        self._indxr_refined_beam = None
        self._indxr_refined_distance = None

        # extra indexing guff - a dictionary which the implementation
        # can store things in
        self._indxr_payload = { }

        return

    def _index_select_images(self):
        '''This is something the implementation needs to implement.
        For instance, Labelit & Mosflm work well with 2 frames 90
        degrees separated, d*TREK & XDS with a couple of wedges.'''

        raise RuntimeError, 'overload me'

    def index_select_images(self):
        '''Call the local implementation...'''
        
        result = self._index_select_images()

        # reset the indexer - we need to rerun to get updated
        # results
        self._indxr_run = False

        return result

    def _index(self):
        '''This is what the implementation needs to implement.'''

        raise RuntimeError, 'overload me'

    def index(self):
        if self._indxr_images is []:
            self.index_select_images()

        result = self._index()
        self._indxr_run = True
        return result

    # setter methods for the input

    def add_indexer_image_wedge(self, image):
        '''Add some images for autoindexing (optional,) input is a 2-tuple
        or an integer.'''

        if type(image) == type(()):
            self._indxr_images.append(image)
        if type(image) == type(1):
            self._indxr_images.append((image, image))

        # reset the indexer - we need to rerun to get updated
        # results
        self._indxr_run = False
        
        return

    def set_indexer_input_lattice(self, lattice):
        '''Set the input lattice for this indexing job. Exactly how this
        is handled depends on the implementation. FIXME decide on the
        format for the lattice.'''

        self._indxr_lattice = lattice

        # reset the indexer - we need to rerun to get updated
        # results
        self._indxr_run = False

        return

    def set_indexer_input_cell(self, cell):
        '''Set the input unit cell (optional.)'''

        if not type(cell) == type(()):
            raise RuntimeError, 'cell must be a 6-tuple de floats'

        if len(cell) != 6:
            raise RuntimeError, 'cell must be a 6-tuple de floats'

        self._indxr_input_cell = tuple(map(float, cell))

        # reset the indexer - we need to rerun to get updated
        # results
        self._indxr_run = False

        return

    # getter methods for the output
    def get_indexer_cell(self):
        '''Get the selected unit cell.'''

        # if not already run, run
        if not self._indxr_run:
            self.index()

        return self._indxr_cell

    def get_indexer_lattice(self):
        '''Get the selected lattice as tP form.'''

        # if not already run, run
        if not self._indxr_run:
            self.index()

        return self._indxr_lattice

    def get_indexer_mosaic(self):
        '''Get the estimated mosaic spread in degrees.'''

        # if not already run, run
        if not self._indxr_run:
            self.index()

        return self._indxr_mosaic

    def get_indexer_distance(self):
        '''Get the refined distance.'''

        # if not already run, run
        if not self._indxr_run:
            self.index()

        return self._indxr_refined_distance

    def get_indexer_beam(self):
        '''Get the refined distance.'''

        # if not already run, run
        if not self._indxr_run:
            self.index()

        return self._indxr_refined_beam

    def get_indexer_payload(self, this):
        '''Attempt to get something from the indexer payload.'''

        # if not already run, run
        if not self._indxr_run:
            self.index()

        return self._indxr_payload.get(this, None)

    # end of interface
