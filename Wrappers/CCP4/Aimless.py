#!/usr/bin/env python
# Aimless.py
#   Copyright (C) 2011 Diamond Light Source, Graeme Winter
#
#   This code is distributed under the BSD license, a copy of which is
#   included in the root directory of this package.
#
# 31st August 2011
#
# A wrapper for the CCP4 program Aimless, for scaling & merging reflections.
# This is a replacement for the more venerable program Scala, and shares the
# same interface as the Scala wrapper. Mostly.

import os
import sys
import math

if not os.environ.has_key('XIA2CORE_ROOT'):
  raise RuntimeError, 'XIA2CORE_ROOT not defined'

if not os.path.join(os.environ['XIA2CORE_ROOT'], 'Python') in sys.path:
  sys.path.append(os.path.join(os.environ['XIA2CORE_ROOT'],
                               'Python'))

if not os.environ['XIA2_ROOT'] in sys.path:
  sys.path.append(os.environ['XIA2_ROOT'])

from Driver.DriverFactory import DriverFactory
from Decorators.DecoratorFactory import DecoratorFactory
from Handlers.Streams import Debug
from Handlers.Flags import Flags
from Experts.ResolutionExperts import linear

def Aimless(DriverType = None,
            partiality_correction = None,
            absorption_correction = None,
            decay_correction = None):
  '''A factory for AimlessWrapper classes.'''

  DriverInstance = DriverFactory.Driver(DriverType)
  CCP4DriverInstance = DecoratorFactory.Decorate(DriverInstance, 'ccp4')

  class AimlessWrapper(CCP4DriverInstance.__class__):
    '''A wrapper for Aimless, using the CCP4-ified Driver.'''

    def __init__(self):
      # generic things
      CCP4DriverInstance.__class__.__init__(self)

      self.set_executable(os.path.join(
          os.environ.get('CBIN', ''), 'aimless'))

      if not os.path.exists(self.get_executable()):
        raise RuntimeError, 'aimless binary not found'

      self.start()
      self.close_wait()

      version = None

      for record in self.get_all_output():
        if '##' in record and 'AIMLESS' in record:
          version = record.split()[5]

      if not version:
        raise RuntimeError, 'version not found'

      Debug.write('Using version: %s' % version)

      # FIXME (i) check program exists and (ii) version is known -
      # if not then default back in the calling code to using scala.

      # clear all the header junk
      self.reset()

      # input and output files
      self._scalepack = False
      self._chef_unmerged = False
      self._unmerged_reflections = None
      self._xmlout = None

      # scaling parameters
      self._resolution = None

      self._resolution_by_run = { }

      # scales file for recycling
      self._scales_file = None

      # this defaults to SCALES - and is useful for when we
      # want to refine the SD parameters because we can
      # recycle the scale factors through the above interface
      self._new_scales_file = None

      # this flag indicates that the input reflections are already
      # scaled and just need merging e.g. from XDS/XSCALE.
      self._onlymerge = False

      # by default, switch this on
      if decay_correction is None:
        self._bfactor = True
      else:
        self._bfactor = decay_correction

      # this will often be wanted
      self._anomalous = False

      # by default switch this on too...
      if partiality_correction is None:
        self._tails = True
      else:
        self._tails = partiality_correction

      # alternative for this is 'batch' err.. no rotation
      if Flags.get_batch_scale():
        self._mode = 'batch'
      else:
        self._mode = 'rotation'

      # these are only relevant for 'rotation' mode scaling
      self._spacing = 5

      if absorption_correction == None:
        self._secondary = Flags.get_aimless_secondary()
      elif absorption_correction == True:
        self._secondary = Flags.get_aimless_secondary()
      else:
        self._secondary = 0

      self._cycles = 100
      self._brotation = None
      self._bfactor_tie = None
      self._surface_tie = None
      self._surface_link = True

      self._intensities = 'combine'

      self._project_crystal_dataset = { }
      self._runs = []

      # for adding data on merge - one dname
      self._pname = None
      self._xname = None
      self._dname = None

      return

    # getter and setter methods

    def set_project_info(self, pname, xname, dname):
      '''Only use this for the merge() method.'''
      self._pname = pname
      self._xname = xname
      self._dname = dname
      return

    def add_run(self, start, end,
                pname = None, xname = None, dname = None,
                exclude = False, resolution = 0.0,
                name = None):
      '''Add another run to the run table, optionally not including
      it in the scaling - for solution to bug 2229.'''

      self._runs.append((start, end, pname, xname, dname,
                         exclude, resolution, name))
      return

    def set_scalepack(self, scalepack = True):
      self._scalepack = scalepack
      return

    def set_chef_unmerged(self, chef_unmerged = True):
      '''Output the measurements in the form suitable for
      input to chef, that is with SDCORRECTION 1 0 0 and
      in unmerged MTZ format.'''

      self._chef_unmerged = chef_unmerged
      return

    def set_resolution(self, resolution):
      '''Set the resolution limit for the scaling -
      default is to include all reflections.'''

      self._resolution = resolution
      return

    def get_xmlout(self):
      return self._xmlout

    def set_resolution_by_run(self, run, resolution):
      '''Set the resolution for a particular run.'''

      self._resolution_by_run = { }
      return

    def set_scales_file(self, scales_file):
      '''Set the file containing all of the scales required for
      this run. Used when fiddling the error parameters or
      obtaining stats to different resolutions. See also
      set_new_scales_file(). This will switch on ONLYMERGE RESTORE.'''

      self._scales_file = scales_file
      return

    def set_new_scales_file(self, new_scales_file):
      '''Set the file to which the scales will be written. This
      will allow reusing through the above interface.'''

      self._new_scales_file = new_scales_file
      return

    def set_onlymerge(self, onlymerge = True):
      '''Switch on merging only - this will presume that the
      input reflections are scaled already.'''

      self._onlymerge = onlymerge
      return

    def set_bfactor(self, bfactor = True, brotation = None):
      '''Switch on/off bfactor refinement, optionally with the
      spacing for the bfactor refinement (in degrees.)'''

      self._bfactor = bfactor

      if brotation:
        self._brotation = brotation

      return

    def set_surface_tie(self, surface_tie):
      self._surface_tie = surface_tie
      return

    def set_surface_link(self, surface_link):
      self._surface_link = surface_link
      return

    def set_anomalous(self, anomalous = True):
      '''Switch on/off separating of anomalous pairs.'''

      self._anomalous = anomalous
      return

    def set_tails(self, tails = True):
      '''Switch on/off tails correction.'''

      self._tails = tails
      return

    def set_scaling_parameters(self, mode,
                               spacing = None, secondary = None):
      '''Set up the scaling: mode is either rotation or batch.
      Spacing indicates the width of smoothing for scales with
      rotation mode scaling, secondary defines the number
      of spherical harmonics which can be used for the secondary
      beam correction. Defaults (5, 6) provided for these seem
      to work most of the time.'''

      if not mode in ['rotation', 'batch']:
        raise RuntimeError, 'unknown scaling mode "%s"' % mode

      if mode == 'batch':
        self._mode = 'batch'
        return

      self._mode = 'rotation'

      if spacing:
        self._spacing = spacing

      if not secondary is None:
        self._secondary = secondary

      return

    def set_cycles(self, cycles):
      '''Set the maximum number of cycles allowed for the scaling -
      this assumes the default convergence parameters.'''

      self._cycles = cycles

      return

    def set_intensities(self, intensities):
      intensities = intensities.lower()
      assert intensities in ("summation", "profile", "combine")
      self._intensities = intensities

    def identify_negative_scale_run(self):
      '''Given the presence of a negative scale factor, try to
      identify it - this is going to be called after a negative scales
      error has been raised.'''

      bad_run = 0

      runs_to_batches = { }
      run = 0

      for record in self.get_all_output():

        if 'Run number' and 'consists of batches' in record:
          run = int(record.split()[2])
          runs_to_batches[run] = []
          continue

        if run and not record.strip():
          run = 0
          continue

        if run:
          runs_to_batches[run].extend(map(int, record.split()))

        if 'shifted scale factor' in record and 'negative' in record:
          tokens = record.split()
          scale = tokens[tokens.index('factor') + 1]
          bad_run = int(scale.split('.')[0][1:])

      return bad_run, (min(runs_to_batches[bad_run]),
                       max(runs_to_batches[bad_run]))

    def identify_no_observations_run(self):
      '''Identify the run which was causing problems with "no
      observations" reported.'''

      bad_run = 0

      runs_to_batches = { }
      run = 0

      for record in self.get_all_output():

        if 'Run number' and 'consists of batches' in record:
          run = int(record.split()[2])
          runs_to_batches[run] = []
          continue

        if run and not record.strip():
          run = 0
          continue

        if run:
          runs_to_batches[run].extend(map(int, record.split()))

        if 'No observations for parameter' in record:
          bad_run = int(record.split()[-1])

      return bad_run, (min(runs_to_batches[bad_run]),
                       max(runs_to_batches[bad_run]))

    def check_aimless_error_negative_scale_run(self):
      '''Check for a bad run giving a negative scale in Aimless - this
      is particularly for the multi-crystal analysis.'''

      for record in self.get_all_output():
        if ' **** Negative scale factor' in record:
          raise RuntimeError, 'bad batch %d' % \
                int(record.split()[-3])

      return

    def check_aimless_errors(self):
      '''Check for Aimless specific errors. Raise RuntimeError if
      error is found.'''

      # FIXME in here I need to add a test for convergence

      output = self.get_all_output()

      for line in output:
        if 'File must be sorted' in line:
          raise RuntimeError, 'hklin not sorted'
        if 'Negative scales' in line:
          run, batches = self.identify_negative_scale_run()
          raise RuntimeError, 'negative scales run %d: %d to %d' % \
                (run, batches[0], batches[1])
        if 'Scaling has failed to converge' in line:
          raise RuntimeError, 'scaling not converged'
        if '*** No observations ***' in line:
          run, batches = self.identify_no_observations_run()
          raise RuntimeError, 'no observations run %d: %d to %d' % \
                (run, batches[0], batches[1])

      return

    def sum(self):
      '''Sum a set of reflections in a sorted mtz file - this will
      just sum partials to make whole reflections, initially for
      resolution analysis.'''

      self.check_hklin()
      self.check_hklout()

      self.start()

      self.input('run 1 all')
      self.input('scales constant')
      self.input('output unmerged')
      self.input('sdcorrection noadjust 1.0 0.0 0.0')

      self.close_wait()

      # check for errors

      if True:
        # try:
        self.check_for_errors()
        self.check_ccp4_errors()
        self.check_aimless_error_negative_scale_run()
        self.check_aimless_errors()

        status = 'OK'

        if 'Error' in status:
          raise RuntimeError, '[AIMLESS] %s' % status

      else:
        # except RuntimeError, e:
        try:
          os.remove(self.get_hklout())
        except:
          pass

        raise e

      return self.get_ccp4_status()

    def merge(self):
      '''Actually merge the already scaled reflections.'''

      self.check_hklin()
      self.check_hklout()

      if not self._onlymerge:
        raise RuntimeError, 'for scaling use scale()'

      if not self._scalepack:
        self.set_task('Merging scaled reflections from %s => %s' % \
                     (os.path.split(self.get_hklin())[-1],
                      os.path.split(self.get_hklout())[-1]))
      else:
        self.set_task('Merging reflections from %s => scalepack %s' % \
                     (os.path.split(self.get_hklin())[-1],
                      os.path.split(self.get_hklout())[-1]))

      self._xmlout = os.path.join(self.get_working_directory(),
                                  '%d_aimless.xml' % self.get_xpid())

      self.start()
      self.input('xmlout %d_aimless.xml' % self.get_xpid())
      self.input('bins 20')
      self.input('run 1 all')
      self.input('scales constant')
      self.input('initial unity')
      self.input('sdcorrection both noadjust 1.0 0.0 0.0')

      if self._anomalous:
        self.input('anomalous on')
      else:
        self.input('anomalous off')

      if self._scalepack:
        self.input('output polish unmerged')
      self.input('output unmerged')

      self.close_wait()

      # check for errors

      try:
        self.check_for_errors()
        self.check_ccp4_errors()
        self.check_aimless_errors()

        status = self.get_ccp4_status()

        if 'Error' in status:
          raise RuntimeError, '[AIMLESS] %s' % status

      except RuntimeError, e:
        try:
          os.remove(self.get_hklout())
        except:
          pass

        raise e

      return self.get_ccp4_status()

    def scale(self):
      '''Actually perform the scaling.'''

      self.check_hklin()
      self.check_hklout()

      if self._chef_unmerged and self._scalepack:
        raise RuntimeError, 'CHEF and scalepack incompatible'

      if self._onlymerge:
        raise RuntimeError, 'use merge() method'

      if not self._scalepack:
        self.set_task('Scaling reflections from %s => %s' % \
                     (os.path.split(self.get_hklin())[-1],
                      os.path.split(self.get_hklout())[-1]))
      else:
        self.set_task('Scaling reflections from %s => scalepack %s' % \
                     (os.path.split(self.get_hklin())[-1],
                      os.path.split(self.get_hklout())[-1]))

      self._xmlout = os.path.join(self.get_working_directory(),
                                  '%d_aimless.xml' % self.get_xpid())

      self.start()

      nproc = Flags.get_parallel()
      if nproc > 1:
        self.set_working_environment('OMP_NUM_THREADS', '%d' %nproc)
        self.input('refine parallel')
      self.input('xmlout %d_aimless.xml' % self.get_xpid())
      self.input('bins 20')
      self.input('intensities %s' %self._intensities)

      if self._new_scales_file:
        self.input('dump %s' % self._new_scales_file)

      run_number = 0
      for run in self._runs:
        run_number += 1

        if not run[5]:
          self.input('run %d batch %d to %d' % (run_number,
                                                run[0], run[1]))

        if run[6] != 0.0 and not run[5]:
          self.input('resolution run %d high %f' % \
                     (run_number, run[6]))

      run_number = 0
      for run in self._runs:
        run_number += 1

        if run[7]:
          Debug.write('Run %d corresponds to sweep %s' % \
                      (run_number, run[7]))

        if run[5]:
          continue

      self.input('sdcorrection same')

      # FIXME this is a bit of a hack - should be better determined
      # than this...
      if Flags.get_small_molecule():
        self.input('sdcorrection tie sdfac 0.707 0.3 tie sdadd 0.1 0.2')

      if self._secondary and self._surface_tie:
        self.input('tie surface %.4f' % self._surface_tie)
        if not self._surface_link:
          self.input('unlink all')

      # assemble the scales command
      if self._mode == 'rotation':
        scale_command = 'scales rotation spacing %f' % self._spacing

        if self._secondary:
          scale_command += ' secondary %d absorption %d' % \
            (int(self._secondary), int(self._secondary))

        if self._bfactor:
          scale_command += ' bfactor on'

          if self._brotation:
            scale_command += ' brotation %f' % \
                             self._brotation

        else:
          scale_command += ' bfactor off'

        if self._tails:
          scale_command += ' tails'

        self.input(scale_command)

      else:

        scale_command = 'scales batch'

        if self._bfactor:
          scale_command += ' bfactor on'

          if self._brotation:
            scale_command += ' brotation %f' % \
                             self._brotation
          else:
            scale_command += ' brotation %f' % \
                             self._spacing

        else:
          scale_command += ' bfactor off'

        if self._tails:
          scale_command += ' tails'

        self.input(scale_command)

      # Debug.write('Scaling command: "%s"' % scale_command)

      # next any 'generic' parameters

      if self._resolution:
        self.input('resolution %f' % self._resolution)

      if self._resolution_by_run != { }:
        # FIXME 20/NOV/06 this needs implementing somehow...
        pass

      self.input('cycles %d' % self._cycles)

      if self._anomalous:
        self.input('anomalous on')
      else:
        self.input('anomalous off')

      if self._scalepack:
        self.input('output polish unmerged')
      elif self._chef_unmerged:
        self.input('output unmerged together')
      else:
        self.input('output unmerged')

      # run using previously determined scales

      if self._scales_file:
        self.input('onlymerge')
        self.input('restore %s' % self._scales_file)

      self.close_wait()

      # check for errors

      if True:
        # try:
        self.check_for_errors()
        self.check_ccp4_errors()
        self.check_aimless_error_negative_scale_run()
        self.check_aimless_errors()

        status = 'OK'

        Debug.write('Aimless status: %s' % status)

        if 'Error' in status:
          raise RuntimeError, '[AIMLESS] %s' % status

      else:
        # except RuntimeError, e:
        try:
          os.remove(self.get_hklout())
        except:
          pass

        raise e

      # here get a list of all output files...
      output = self.get_all_output()

      hklout_files = []
      hklout_dict = { }

      for i in range(len(output)):
        record = output[i]

        # this is a potential source of problems - if the
        # wavelength name has a _ in it then we are here stuffed!

        if 'Writing merged data for dataset' in record:

          if len(record.split()) == 9:
            hklout = output[i + 1].strip()
          else:
            hklout = record.split()[9]

          dname = record.split()[6].split('/')[-1]
          hklout_dict[dname] = hklout

          hklout_files.append(hklout)

        elif 'Writing unmerged data for all datasets' in record:
          if len(record.split()) == 9:
            hklout = output[i + 1].strip()
          else:
            hklout = record.split()[9]

          self._unmerged_reflections = hklout

      self._scalr_scaled_reflection_files = hklout_dict

      return 'OK'

    def multi_merge(self):
      '''Merge data from multiple runs - this is very similar to
      the scaling subroutine...'''

      self.check_hklin()
      self.check_hklout()

      if not self._scalepack:
        self.set_task('Scaling reflections from %s => %s' % \
                     (os.path.split(self.get_hklin())[-1],
                      os.path.split(self.get_hklout())[-1]))
      else:
        self.set_task('Scaling reflections from %s => scalepack %s' % \
                     (os.path.split(self.get_hklin())[-1],
                      os.path.split(self.get_hklout())[-1]))

      self.start()

      self._xmlout = os.path.join(self.get_working_directory(),
                                  '%d_aimless.xml' % self.get_xpid())

      self.input('xmlout %d_aimless.xml' % self.get_xpid())
      self.input('bins 20')

      if self._new_scales_file:
        self.input('dump %s' % self._new_scales_file)

      if self._resolution:
        self.input('resolution %f' % self._resolution)

      run_number = 0
      for run in self._runs:
        run_number += 1

        if not run[5]:
          self.input('run %d batch %d to %d' % (run_number,
                                                run[0], run[1]))

        if run[6] != 0.0 and not run[5]:
          self.input('resolution run %d high %f' % \
                     (run_number, run[6]))

      # put in the pname, xname, dname stuff
      run_number = 0
      for run in self._runs:
        run_number += 1

        if run[7]:
          Debug.write('Run %d corresponds to sweep %s' % \
                      (run_number, run[7]))

        if run[5]:
          continue

      # we are only merging here so the scales command is
      # dead simple...

      self.input('scales constant')

      if self._anomalous:
        self.input('anomalous on')
      else:
        self.input('anomalous off')

      # FIXME this is probably not ready to be used yet...
      if self._scalepack:
        self.input('output polish unmerged')
      self.input('output unmerged')

      if self._scales_file:
        self.input('onlymerge')
        self.input('restore %s' % self._scales_file)

      self.close_wait()

      # check for errors

      try:
        self.check_for_errors()
        self.check_ccp4_errors()
        self.check_aimless_errors()

        status = 'OK'

        Debug.write('Aimless status: %s' % status)

        if 'Error' in status:
          raise RuntimeError, '[AIMLESS] %s' % status

      except RuntimeError, e:
        try:
          os.remove(self.get_hklout())
        except:
          pass

        raise e

      # here get a list of all output files...
      output = self.get_all_output()

      # want to put these into a dictionary at some stage, keyed
      # by the data set id. how this is implemented will depend
      # on the number of datasets...

      # FIXME file names on windows separate out path from
      # drive with ":"... fixed! split on "Filename:"

      # get a list of dataset names...

      datasets = []
      for run in self._runs:
        # cope with case where two runs make one dataset...
        if not run[4] in datasets:
          if run[5]:
            pass
          else:
            datasets.append(run[4])

      hklout_files = []
      hklout_dict = { }

      for i in range(len(output)):
        record = output[i]

        # this is a potential source of problems - if the
        # wavelength name has a _ in it then we are here stuffed!

        if 'Writing merged data for dataset' in record:

          if len(record.split()) == 9:
            hklout = output[i + 1].strip()
          else:
            hklout = record.split()[9]

          dname = record.split()[6].split('/')[-1]
          hklout_dict[dname] = hklout

          hklout_files.append(hklout)

        elif 'Writing unmerged data for all datasets' in record:
          if len(record.split()) == 9:
            hklout = output[i + 1].strip()
          else:
            hklout = record.split()[9]

          self._unmerged_reflections = hklout

      self._scalr_scaled_reflection_files = hklout_dict

      return 'OK'

    def get_scaled_reflection_files(self):
      '''Get the names of the actual scaled reflection files - note
      that this is not the same as HKLOUT because Aimless splits them
      up...'''
      return self._scalr_scaled_reflection_files

    def get_unmerged_reflection_file(self):
      return self._unmerged_reflections

    def get_summary(self):
      '''Get a summary of the data.'''

      xml_file = self.get_xmlout()
      assert os.path.isfile(xml_file)

      from AimlessHelpers import parse_aimless_xml
      return parse_aimless_xml(xml_file)

  return AimlessWrapper()

if __name__ == '__output_main__':
  # test parsing the output

  logfile = os.path.join(os.environ['XIA2_ROOT'],
                         'Doc', 'Logfiles', 'aimless.log')

  s = Aimless()
  s.load_all_output(logfile)

  results = s.parse_ccp4_loggraph()

  print 'The following loggraphs were found'
  for k in results.keys():
    print k


  summary = s.get_summary()

  for k in summary.keys():
    dataset = summary[k]
    for property in dataset.keys():
      print k, property, dataset[property]

if __name__ == '__main_2_':

  # run a couple of tests - this will depend on the unit tests for
  # XIACore having been run...

  s = Aimless()

  hklin = os.path.join(os.environ['XIA2CORE_ROOT'],
                       'Python', 'UnitTest', '12287_1_E1_sorted.mtz')

  hklout = '12287_1_E1_scaled.mtz'

  s.set_hklin(hklin)
  s.set_hklout(hklout)

  s.set_resolution(1.65)

  # switch on all of the options I want
  s.set_anomalous()
  s.set_tails()
  s.set_bfactor()

  s.set_scaling_parameters('rotation')

  # this is in the order fac, add, B
  s.add_sd_correction('full', 1.0, 0.02, 15.0)
  s.add_sd_correction('partial', 1.0, 0.00, 15.0)

  print s.scale()

  s.write_log_file('aimless.log')

  results = s.parse_ccp4_loggraph()

  print 'The following loggraphs were found'
  for k in results.keys():
    print k

  summary = s.get_summary()

  for k in summary.keys():
    print k, summary[k]


if __name__ == '__main__':

  s = Aimless()

  hklin = 'TS00_13185_sorted_INFL.mtz'
  hklout = 'TS00_13185_merged_INFL.mtz'

  s.set_hklin(hklin)
  s.set_hklout(hklout)

  s.set_anomalous()
  s.set_onlymerge()
  s.merge()

  s.write_log_file('merge.log')

  results = s.parse_ccp4_loggraph()

  print 'The following loggraphs were found'
  for k in results.keys():
    print k

  summary = s.get_summary()

  for k in summary.keys():
    print k, summary[k]
