#!/usr/bin/env python
# DiscoverBetterExperimentalModel.py
#
#   Copyright (C) 2015 Diamond Light Source, Richard Gildea
#
#   This code is distributed under the BSD license, a copy of which is
#   included in the root directory of this package.
#
# DiscoverBetterExperimentalModel using the DIALS code: assumes spots found from same.

from __future__ import division
import os
import shutil

from __init__ import _setup_xia2_environ
_setup_xia2_environ()

from Handlers.Flags import Flags

def DiscoverBetterExperimentalModel(DriverType = None):
  '''A factory for DiscoverBetterExperimentalModel classes.'''

  from Driver.DriverFactory import DriverFactory
  DriverInstance = DriverFactory.Driver(DriverType)

  class DiscoverBetterExperimentalModelWrapper(DriverInstance.__class__):

    def __init__(self):
      DriverInstance.__class__.__init__(self)
      self.set_executable('dials.discover_better_experimental_model')

      self._sweep_filename = None
      self._spot_filename = None
      self._optimized_filename = None
      self._phil_file = None
      self._scan_ranges = []

      return

    def set_sweep_filename(self, sweep_filename):
      self._sweep_filename = sweep_filename
      return

    def set_spot_filename(self, spot_filename):
      self._spot_filename = spot_filename
      return

    def set_optimized_datablock_filename(self, optimized_filename):
      self._optimized_filename = optimized_filename
      return

    def set_phil_file(self, phil_file):
      self._phil_file = phil_file
      return

    def set_scan_ranges(self, scan_ranges):
      self._scan_ranges = scan_ranges
      return

    def add_scan_range(self, scan_range):
      self._scan_ranges.append(scan_range)
      return

    def get_optimized_datablock_filename(self):
      return self._optimized_filename

    def run(self):
      from Handlers.Streams import Debug
      Debug.write('Running %s' %self.get_executable())

      self.clear_command_line()
      self.add_command_line(self._sweep_filename)
      self.add_command_line(self._spot_filename)
      nproc = Flags.get_parallel()
      self.set_cpu_threads(nproc)
      self.add_command_line('nproc=%i' % nproc)
      for scan_range in self._scan_ranges:
        self.add_command_line('scan_range=%d,%d' % scan_range)

      if self._phil_file is not None:
        self.add_command_line("%s" %self._phil_file)

      self._optimized_filename = os.path.join(
        self.get_working_directory(), '%d_optimized_datablock.json' %self.get_xpid())
      self.add_command_line("output.datablock=%s" %self._optimized_filename)

      self.start()
      self.close_wait()
      self.check_for_errors()

      records = self.get_all_output()

      assert os.path.exists(self._optimized_filename), self._optimized_filename

      return

  return DiscoverBetterExperimentalModelWrapper()
