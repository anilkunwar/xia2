#!/usr/bin/env python
# Sweep.py
#   Copyright (C) 2006 CCLRC, Graeme Winter
#
#   This code is distributed under the BSD license, a copy of which is
#   included in the root directory of this package.
#
# 15th June 2006
#
# A class to represent a sweep of frames collected under the same conditions.
# This pertains to the dataset object in the early phases of processing.

from __future__ import absolute_import, division, print_function

import copy
import os
import sys

from xia2.Experts.FindImages import (find_matching_images,
                                     image2template_directory,
                                     template_directory_number2image)
from xia2.Handlers.Phil import PhilIndex

def SweepFactory(template, directory, beam=None):
  '''A factory which will return a list of sweep objects which match
  the input template and directory.'''

  sweeps = []

  from xia2.Schema import load_imagesets
  imagesets = load_imagesets(
    template, directory,
    reversephi=PhilIndex.params.xia2.settings.input.reverse_phi)

  for imageset in imagesets:
    scan = imageset.get_scan()
    if scan is not None:
      sweeps.append(
        Sweep(template, directory,
              imageset=imageset,
              id_image=scan.get_image_range()[0],
              beam=beam))

  return sweeps

class Sweep(object):
  '''A class to represent a single sweep of frames.'''

  def __init__(self,
               template,
               directory,
               imageset=None,
               id_image=None,
               beam=None):

    '''Initialise the sweep by inspecting the images. id_image
    defines the first image in this sweep, and hence the identity of
    the sweep of more than one are found which match.'''

    self._identity_attributes = ['_collect_start', '_collect_end',
                                 '_template', '_id_image']

    if id_image is not None:
      self._id_image = id_image
    else:
      self._id_image = -1

    # populate the attributes of this object

    self._template = template
    self._directory = directory

    # populate the rest of the structure
    self._images = []

    if imageset is not None:
      self._imageset = imageset
      image_range = imageset.get_scan().get_image_range()
      self._images = list(range(image_range[0], image_range[1] + 1))

    # if the beam has been specified, then this will
    # override the headers
    self._beam_centre = beam

    self.update()

  def get_template(self):
    #try:
      #return self._imageset.get_template()
    #except Exception:
    return self._template

  def get_directory(self):
    return self._directory

  def get_imageset(self):
    return self._imageset

  def get_images(self):
    # check if any more images have appeared
    self.update()
    image_range = self._imageset.get_scan().get_image_range()
    return list(range(image_range[0], image_range[1] + 1))

  def get_distance(self):
    return self._imageset.get_detector()[0].get_directed_distance()

  def get_wavelength(self):
    return self._imageset.get_beam().get_wavelength()

  def set_wavelength(self, wavelength):
    return self._imageset.get_beam().set_wavelength(wavelength)

  def get_beam_centre(self):
    from xia2.Schema.Interfaces.FrameProcessor import get_beam_centre
    detector = self._imageset.get_detector()
    beam = self._imageset.get_beam()
    return get_beam_centre(detector, beam)

  def imagename(self, number):
    '''Compute an image name from an image number.'''

    return template_directory_number2image(self._template,
                                           self._directory,
                                           number)

  def update(self):
    '''Check to see if any more frames have appeared - if they
    have update myself and reset.'''

    from xia2.Applications.xia2setup import is_hd5f_name
    if is_hd5f_name(os.path.join(self._directory, self._template)):
      return

    images = find_matching_images(self._template,
                                  self._directory)

    if len(images) > len(self._images):

      self._images = images

      from xia2.Schema import load_imagesets
      imagesets = load_imagesets(
        self._template, self._directory, id_image=self._id_image,
        use_cache=False,
        reversephi=PhilIndex.params.xia2.settings.input.reverse_phi)

      max_images = 0
      best_sweep = None
      for imageset in imagesets:
        scan = imageset.get_scan()
        if scan is None: continue
        if imageset.get_scan().get_num_images() > max_images:
          best_sweep = imageset

      self._imageset = best_sweep

    return

if __name__ == '__main__':

  if len(sys.argv) < 2:
    image = os.path.join(os.environ['XIA2_ROOT'],
                         'Data', 'Test', 'Images', '12287_1_E1_001.img')
  else:
    image = sys.argv[1]

  template, directory = image2template_directory(image)

  sl = SweepFactory(template, directory)

  for s in sl:

    t = s.get_collect()
    print('Data collection took %s seconds' % (t[1] - t[0]))
    print('For a total of %s seconds of exposure' % \
          (s.get_exposure_time() * \
           len(s.get_images())))
    print('Images: %d to %d' % (min(s.get_images()), max(s.get_images())))
    print('Template: %s' % s.get_template())
    print('')
