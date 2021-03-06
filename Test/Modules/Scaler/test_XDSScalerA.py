from __future__ import absolute_import, division, print_function

import os
import sys

import mock
import pytest

@pytest.mark.slow
@pytest.mark.parametrize('nproc', [1])
def test_xds_scalerA(ccp4, dials_regression, tmpdir, nproc):
  if nproc is not None:
    from xia2.Handlers.Phil import PhilIndex
    PhilIndex.params.xia2.settings.multiprocessing.nproc = nproc

  template = os.path.join(dials_regression, "xia2_demo_data", "insulin_1_###.img")

  tmpdir.chdir()
  tmpdir = tmpdir.strpath

  from xia2.Modules.Indexer.XDSIndexer import XDSIndexer
  from xia2.Modules.Integrater.XDSIntegrater import XDSIntegrater
  from xia2.Modules.Scaler.XDSScalerA import XDSScalerA
  indexer = XDSIndexer()
  indexer.set_working_directory(tmpdir)
  from dxtbx.datablock import DataBlockTemplateImporter
  importer = DataBlockTemplateImporter([template])
  datablocks = importer.datablocks
  imageset = datablocks[0].extract_imagesets()[0]
  indexer.add_indexer_imageset(imageset)

  from xia2.Schema.XCrystal import XCrystal
  from xia2.Schema.XWavelength import XWavelength
  from xia2.Schema.XSweep import XSweep
  from xia2.Schema.XSample import XSample
  cryst = XCrystal("CRYST1", None)
  wav = XWavelength("WAVE1", cryst, imageset.get_beam().get_wavelength())
  samp = XSample("X1", cryst)
  directory, image = os.path.split(imageset.get_path(1))
  with mock.patch.object(sys, 'argv', []):
    sweep = XSweep('SWEEP1', wav, samp, directory=directory, image=image)
  indexer.set_indexer_sweep(sweep)

  from xia2.Modules.Refiner.XDSRefiner import XDSRefiner
  refiner = XDSRefiner()
  refiner.set_working_directory(tmpdir)
  refiner.add_refiner_indexer(sweep.get_epoch(1), indexer)

  integrater = XDSIntegrater()
  integrater.set_working_directory(tmpdir)
  integrater.setup_from_image(imageset.get_path(1))
  integrater.set_integrater_refiner(refiner)
  #integrater.set_integrater_indexer(indexer)
  integrater.set_integrater_sweep(sweep)
  integrater.set_integrater_sweep_name('SWEEP1')
  integrater.set_integrater_project_info('CRYST1', 'WAVE1', 'SWEEP1')

  scaler = XDSScalerA()
  scaler.add_scaler_integrater(integrater)
  scaler.set_scaler_xcrystal(cryst)
  scaler.set_scaler_project_info('CRYST1', 'WAVE1')

  check_scaler_files_exist(scaler)

  # test serialization of scaler
  json_str = scaler.as_json()
  #print json_str
  scaler2 = XDSScalerA.from_json(string=json_str)
  scaler2.set_scaler_xcrystal(cryst)

  check_scaler_files_exist(scaler2)

  scaler2.set_scaler_finish_done(False)
  check_scaler_files_exist(scaler2)

  scaler2.set_scaler_done(False)
  check_scaler_files_exist(scaler2)

  scaler2._scalr_integraters = {} # XXX
  scaler2.add_scaler_integrater(integrater)
  scaler2.set_scaler_prepare_done(False)
  check_scaler_files_exist(scaler2)


def check_scaler_files_exist(scaler):
  merged = scaler.get_scaled_merged_reflections()
  for filetype in ('mtz', 'sca', 'sca_unmerged'):
    assert filetype in merged
    if isinstance(merged[filetype], basestring):
      files = [merged[filetype]]
    else:
      files = merged[filetype].values()
    for f in files:
      assert os.path.isfile(f)
