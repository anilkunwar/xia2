#!/usr/bin/env python
# Scala.py
#   Copyright (C) 2006 CCLRC, Graeme Winter
#
#   This code is distributed under the terms and conditions of the
#   CCP4 Program Suite Licence Agreement as a CCP4 Library.
#   A copy of the CCP4 licence can be obtained by writing to the
#   CCP4 Secretary, Daresbury Laboratory, Warrington WA4 4AD, UK.
#
# 5th June 2006
# 
# A wrapper for the CCP4 program Scala, for scaling & merging reflections.
# 
# Provides:
# 
# Scaling of reflection data from Mosflm and other programs.
# Merging of unmerged reflection data.
# Characterisazion of data from scaling statistics.
# 
# Versions:
# 
# Since this will be a complex interface, the first stage is to satisfy the
# most simple scaling requirements, which is to say taking exactly one
# dataset from Mosflm via Sortmtz and scaling this. This will produce
# the appropriate statistics. This corresponds to Simple 1 in the use case
# documentation.
# 
# FIXME 27/OCT/06 need to update the use case documentation - where is this?
#                 in Wrappers/CCP4/Doc I presume...
# 
# FIXME 06/NOV/06 need to update the interface to also allow a quick scaling
#                 option, to use in the case (well illustrated by TS02) where
#                 pointless needs to reindex data sets to a standard defined
#                 by the first reflection file...
# 
#                 Recipe is "cycles 6" "run 1 all"
#                 "scales rotation spacing 10" 

import os
import sys

if not os.environ.has_key('XIA2CORE_ROOT'):
    raise RuntimeError, 'XIA2CORE_ROOT not defined'

if not os.path.join(os.environ['XIA2CORE_ROOT'], 'Python') in sys.path:
    sys.path.append(os.path.join(os.environ['XIA2CORE_ROOT'],
                                 'Python'))

from Driver.DriverFactory import DriverFactory
from Decorators.DecoratorFactory import DecoratorFactory

def Scala(DriverType = None):
    '''A factory for ScalaWrapper classes.'''

    DriverInstance = DriverFactory.Driver(DriverType)
    CCP4DriverInstance = DecoratorFactory.Decorate(DriverInstance, 'ccp4')

    class ScalaWrapper(CCP4DriverInstance.__class__):
        '''A wrapper for Scala, using the CCP4-ified Driver.'''

        def __init__(self):
            # generic things
            CCP4DriverInstance.__class__.__init__(self)
            self.set_executable('scala')

            # input and output files
            self._scalepack = None

            # scaling parameters
            self._resolution = None

            # scales file for recycling
            self._scales_file = None

            # this defaults to SCALES - and is useful for when we
            # want to refine the SD parameters because we can
            # recycle the scale factors through the above interface
            self._new_scales_file = None

            # this flag indicates that the input reflections are already
            # scaled and just need merging e.g. from XDS/XSCALE.
            self._onlymerge = False

            # this is almost certainly wanted
            self._bfactor = True

            # this will often be wanted
            self._anomalous = False

            # this is almost certainly wanted
            self._tails = True

            # alternative for this is 'batch'
            self._mode = 'rotation'

            # these are only relevant for 'rotation' mode scaling
            self._spacing = 5
            self._secondary = 6

            # this defines how many cycles of
            # scaling we're allowing before convergence
            self._cycles = 20

            # less common parameters - see scala manual page:
            # (C line 1800)
            #
            # "Some alternatives
            #  >> Recommended usual case
            #  scales rotation spacing 5 secondary 6 bfactor off tails
            #
            #  >> If you have radiation damage, you need a Bfactor,
            #  >>  but a Bfactor at coarser intervals is more stable
            #  scales  rotation spacing 5 secondary 6  tails \
            #     bfactor on brotation spacing 20
            #  tie bfactor 0.5 - restraining the Bfactor also helps"

            self._brotation = None
            self._bfactor_tie = None
            
            # standard error parameters - now a dictionary to handle
            # multiple runs
            self._sd_parameters = { } 
            self._project_crystal_dataset = { }
            self._runs = []

            return

        # getter and setter methods

        def add_run(self, start, end,
                    pname = None, xname = None, dname = None):
            '''Add another run to the run table.'''

            self._runs.append((start, end, pname, xname, dname))
            return

        def add_sd_correction(self, set, sdfac, sdadd, sdb = 0.0):
            '''Add a set of SD correction parameters for a given
            set of reflections (initially set = full or partial.)'''

            # FIXME 01/NOV/06 need also to be able to specify the
            # run where this is needed - e.g. run 1, run 2...

            if not set in ['full', 'partial', 'both']:
                raise RuntimeError, 'set not known "%s"' % set

            self._sd_parameters[set] = (sdfac, sdadd, sdb)
            return

        def set_scalepack(self, scalepack):
            '''Set the output mode to POLISH UNMERGED to this
            file.'''

            self._scalepack = scalepack
            return

        def set_resolution(self, resolution):
            '''Set the resolution limit for the scaling -
            default is to include all reflections.'''

            self._resolution = resolution
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

            if secondary:
                self._secondary = secondary

            return

        def set_cycles(self, cycles):
            '''Set the maximum number of cycles allowed for the scaling -
            this assumes the default convergence parameters.'''

            self._cycles = cycles

            return

        def check_scala_errors(self):
            '''Check for Scala specific errors. Raise RuntimeError if
            error is found.'''

            # FIXME in here I need to add a test for convergence

            output = self.get_all_output()

            for line in output:
                if 'File must be sorted' in line:
                    raise RuntimeError, 'hklin not sorted'
                if 'Negative scales' in line:
                    raise RuntimeError, 'negative scales'


            return

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
                              os.path.split(self._scalepack)[-1]))

                self.add_command_line('scalepack')
                self.add_command_line(self._scalepack)

            self.start()
            # for the harvesting information
            self.input('usecwd')
            self.input('run 1 all')
            self.input('scales constant')
            self.input('initial unity')

            if self._anomalous:
                self.input('anomalous on')
            else:
                self.input('anomalous off')

            if self._scalepack:
                self.input('output polish unmerged')

            self.close_wait()

            # check for errors

            try:
                self.check_for_errors()
                self.check_ccp4_errors()
                self.check_scala_errors()

            except RuntimeError, e:
                try:
                    os.remove(self.get_hklout())
                except:
                    pass

                if self._scalepack:
                    try:
                        os.remove(self._scalepack)
                    except:
                        pass

                raise e

            # if we scaled to a scalepack file, delete the
            # mtz file we created

            if self._scalepack:
                try:
                    os.remove(self.get_hklout())
                except:
                    pass

            return self.get_ccp4_status()
            
        def scale(self):
            '''Actually perform the scaling.'''

            self.check_hklin()
            self.check_hklout()

            if self._new_scales_file:
                self.add_command_line('SCALES')
                self.add_command_line(self._new_scales_file)

            if self._onlymerge:
                raise RuntimeError, 'use merge() method'

            if not self._scalepack:
                self.set_task('Scaling reflections from %s => %s' % \
                             (os.path.split(self.get_hklin())[-1],
                              os.path.split(self.get_hklout())[-1]))
            else:
                self.set_task('Scaling reflections from %s => scalepack %s' % \
                             (os.path.split(self.get_hklin())[-1],
                              os.path.split(self._scalepack)[-1]))
                             
                self.add_command_line('scalepack')
                self.add_command_line(self._scalepack)

            self.start()
            # for the harvesting information
            self.input('usecwd')
                
            # fixme this works ok for UC1 but won't handle anything
            # more sophisticated FIXME FIXME 27/OCT/06 how is this
            # still in here???
            # self.input('run 1 all')

            run_number = 0
            for run in self._runs:
                run_number += 1
                self.input('run %d batch %d to %d' % (run_number,
                                                      run[0], run[1]))
            
            # put in the pname, xname, dname stuff
            run_number = 0
            for run in self._runs:
                run_number += 1
                self.input('name run %d project %s crystal %s dataset %s' % \
                           (run_number, run[2], run[3], run[4]))

            # assemble the scales command
            if self._mode == 'rotation':
                scale_command = 'scales rotation spacing %f' % self._spacing

                if self._secondary:
                    scale_command += ' secondary %f' % self._secondary

                if self._bfactor:
                    scale_command += ' bfactor on'

                    if self._brotation:
                        scale_command += ' brotation %f' % self._brotation
                    
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
                        scale_command += ' brotation %f' % self._brotation
                    
                else:
                    scale_command += ' bfactor off'

                if self._tails:
                    scale_command += ' tails'

                self.input(scale_command)

            # next any 'generic' parameters

            if self._resolution:
                self.input('resolution %f' % self._resolution)

            self.input('cycles %d' % self._cycles)

            for key in self._sd_parameters:
                # the input order for these is sdfac, sdB, sdadd...
                parameters = self._sd_parameters[key]
                self.input('sdcorrection %s %f %f %f' % \
                           (key, parameters[0], parameters[2], parameters[1]))

            if self._anomalous:
                self.input('anomalous on')
            else:
                self.input('anomalous off')

            if self._scalepack:
                self.input('output polish unmerged')

            # run using previously determined scales

            if self._scales_file:
                self.input('onlymerge')
                self.input('restore "%s"' % self._scales_file)

            self.close_wait()

            # check for errors

            try:
                self.check_for_errors()
                self.check_ccp4_errors()
                self.check_scala_errors()

            except RuntimeError, e:
                try:
                    os.remove(self.get_hklout())
                except:
                    pass

                if self._scalepack:
                    try:
                        os.remove(self._scalepack)
                    except:
                        pass

                raise e

            # if we scaled to a scalepack file, delete the
            # mtz file we created

            if self._scalepack:
                try:
                    os.remove(self.get_hklout())
                except:
                    pass

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
                    datasets.append(run[4])

            hklout_files = []
            hklout_dict = { }
            
            for i in range(len(output)):
                record = output[i]
                if 'WRITTEN OUTPUT MTZ FILE' in record:
                    hklout = output[i + 1].split('Filename:')[-1].strip()
                    if len(datasets) > 1:
                        dname = hklout.split('_')[-1].replace('.mtz', '')
                        if not dname in datasets:
                            raise RuntimeError, 'unknown dataset %s' % dname
                        hklout_dict[dname] = hklout
                    elif len(datasets) > 0:
                        hklout_dict[datasets[0]] = hklout
                    else:
                        hklout_dict['only'] = hklout
                    hklout_files.append(hklout)
            
            self._scalr_scaled_reflection_files = hklout_dict

            return self.get_ccp4_status()

        def quick_scale(self):
            '''Perform a quick scaling - to assess data quality & merging.'''

            self.check_hklin()
            self.check_hklout()

            self.set_task('Quickly scaling reflections from %s => %s' % \
                          (os.path.split(self.get_hklin())[-1],
                           os.path.split(self.get_hklout())[-1]))
            
            self.start()
            # for the harvesting information
            self.input('usecwd')

            # assert here that there is only one dataset in the input...

            self.input('run 1 all')
            self.input('cycles 6')
            self.input('scales rotation spacing 10')
                
            # next any 'generic' parameters

            if self._resolution:
                self.input('resolution %f' % self._resolution)

            if self._anomalous:
                self.input('anomalous on')
            else:
                self.input('anomalous off')

            self.close_wait()

            # check for errors

            try:
                self.check_for_errors()
                self.check_ccp4_errors()
                self.check_scala_errors()

            except RuntimeError, e:
                try:
                    os.remove(self.get_hklout())
                except:
                    pass

                if self._scalepack:
                    try:
                        os.remove(self._scalepack)
                    except:
                        pass

                raise e

            output = self.get_all_output()

            return self.get_ccp4_status()
            
        def get_scaled_reflection_files(self):
            '''Get the names of the actual scaled reflection files - note
            that this is not the same as HKLOUT because Scala splits them
            up...'''
            return self._scalr_scaled_reflection_files

        def get_summary(self):
            '''Get a summary of the data.'''

            # FIXME this will probably have to be improved following
            # the updates beyond UC1.

            output = self.get_all_output()
            length = len(output)

            total_summary = { }

            for i in range(length):
                line = output[i]
                if 'Summary data for' in line:
                    list = line.split()
                    pname, xname, dname = list[4], list[6], list[8]
                    summary = { }
                    i += 1
                    line = output[i]
                    while not '=====' in line:
                        if len(line) > 40:
                            key = line[:40].strip()
                            if key:
                                summary[key] = line[40:].split()
                        i += 1
                        line = output[i]
                    total_summary[(pname, xname, dname)] = summary

            return total_summary

    return ScalaWrapper()

if __name__ == '__output_main__':
    # test parsing the output

    logfile = os.path.join(os.environ['DPA_ROOT'],
                           'Doc', 'Logfiles', 'scala.log')

    s = Scala()
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

if __name__ == '__main__':

    # run a couple of tests - this will depend on the unit tests for
    # XIACore having been run...

    s = Scala()
    
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

    s.write_log_file('scala.log')
    
    results = s.parse_ccp4_loggraph()

    print 'The following loggraphs were found'
    for k in results.keys():
        print k

    summary = s.get_summary()

    for k in summary.keys():
        print k, summary[k]
