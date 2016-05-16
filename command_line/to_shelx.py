from __future__ import division
import datetime
import iotbx.cif.model
import json
import optparse
import sys
import xia2.XIA2Version

def parse_compound(compound):
  import string
  result = { }
  element = ''
  number = ''
  compound += 'X'
  for c in compound:
    if c in string.uppercase:
      if not element:
        element += c
        continue
      if number == '':
        count = 1
      else:
        count = int(number)
      if not element in result:
        result[element] = 0
      result[element] += count
      element = '' + c
      number = ''
      if c == 'X':
        break
    elif c in string.lowercase:
      element += c
    elif c in string.digits:
      number += c
  return result

def generate_cif(prefix='xia2', unit_cell_data=None, wavelength=None, structure=None):
  block = iotbx.cif.model.block()
  block["_audit_creation_method"] = xia2.XIA2Version.Version
  block["_audit_creation_date"] = datetime.date.today().isoformat()

  block["_publ_section_references"] = '''
Winter, G. (2010) Journal of Applied Crystallography 43
'''
  def format_value_with_esd(value, esd, decimal_places):
    return "%%.%df(%%d)" % decimal_places % (value, round(esd * (10 ** decimal_places)))

  if unit_cell_data:
    for parameter, cifname in zip(['a', 'b', 'c', 'alpha', 'beta', 'gamma', 'volume'],
                                  ['length_a', 'length_b', 'length_c', 'angle_alpha', 'angle_beta', 'angle_gamma', 'volume']):
      block['_cell_%s' % cifname] = format_value_with_esd(unit_cell_data['solution_constrained'][parameter]['mean'],
                                                          unit_cell_data['solution_constrained'][parameter]['population_standard_deviation'],
                                                          4)
    block['_cell_measurement_reflns_used'] = unit_cell_data['sampling']['used_reflections']
    block['_cell_measurement_theta_min'] = unit_cell_data['sampling']['used_min_2theta'] / 2
    block['_cell_measurement_theta_max'] = unit_cell_data['sampling']['used_max_2theta'] / 2
    block['_diffrn_reflns_number'] = unit_cell_data['reflections']['count']
    block['_diffrn_reflns_limit_h_min'] = unit_cell_data['reflections']['min_miller'][0]
    block['_diffrn_reflns_limit_h_max'] = unit_cell_data['reflections']['max_miller'][0]
    block['_diffrn_reflns_limit_k_min'] = unit_cell_data['reflections']['min_miller'][1]
    block['_diffrn_reflns_limit_k_max'] = unit_cell_data['reflections']['max_miller'][1]
    block['_diffrn_reflns_limit_l_min'] = unit_cell_data['reflections']['min_miller'][2]
    block['_diffrn_reflns_limit_l_max'] = unit_cell_data['reflections']['max_miller'][2]
    block['_diffrn_reflns_theta_min'] = unit_cell_data['reflections']['min_2theta'] / 2
    block['_diffrn_reflns_theta_max'] = unit_cell_data['reflections']['max_2theta'] / 2

  if structure:
    space_group = structure.space_group()
    sgi = structure.space_group_info()
    block['_space_group_crystal_system'] = space_group.crystal_system().lower()
    block['_space_group_IT_number'] = sgi.type().number()
    block['_symmetry_space_group_name_H-M'] = sgi.type().lookup_symbol()
    block['_cell_formula_units_Z'] = sgi.group().order_z()

    loop = iotbx.cif.model.loop()
    symm_ops = []
    for i in xrange(space_group.n_smx()):
      rt_mx = space_group(0, 0, i)
      if rt_mx.is_unit_mx(): continue
      symm_ops.append(str(rt_mx))
    loop['_symmetry_equiv_pos_as_xyz'] = symm_ops
    block.add_loop(loop)

  if wavelength:
    block['_diffrn_radiation_wavelength'] = wavelength

  cif = iotbx.cif.model.cif()
  cif[prefix] = block
  with open('%s.cif_xia2' % prefix, 'w') as fh:
    cif.show(out=fh)

def to_shelx(hklin, prefix, compound='', options=None):
  '''Read hklin (unmerged reflection file) and generate SHELXT input file
  and HKL file'''
  if options is None:
    options = {}

  from iotbx.reflection_file_reader import any_reflection_file
  from iotbx.shelx import writer
  from iotbx.shelx.hklf import miller_array_export_as_shelx_hklf
  from cctbx.xray.structure import structure
  from cctbx.xray import scatterer

  reader = any_reflection_file(hklin)
  mtz_object = reader.file_content()
  intensities = [ma for ma in reader.as_miller_arrays(merge_equivalents=False)
                 if ma.info().labels == ['I', 'SIGI']][0]

  # FIXME do I need to reindex to a conventional setting here

  indices = reader.file_content().extract_original_index_miller_indices()
  intensities = intensities.customized_copy(indices=indices, info=intensities.info())

  with open('%s.hkl' % prefix, 'wb') as hkl_file_handle:
    # limit values to 4 digits (before decimal point), as this is what shelxt
    # writes in its output files, and shelxl seems to read. ShelXL apparently
    # does not read values >9999 properly
    miller_array_export_as_shelx_hklf(intensities, hkl_file_handle,
      scale_range=(-9999., 9999.), normalise_if_format_overflow=True)

  crystal_symm = intensities.crystal_symmetry()

  wavelength = options.wavelength
  if wavelength is None:
    mtz_crystals = mtz_object.crystals()
    wavelength = mtz_crystals[1].datasets()[0].wavelength()
  print 'Experimental wavelength: %.3f Angstroms' % wavelength

  unit_cell_dims = None
  unit_cell_esds = None
  cell_data = None
  if options.cell:
    with open(options.cell, 'r') as fh:
      cell_data = json.load(fh)
      solution = cell_data.get('solution_constrained', cell_data['solution_unconstrained'])
      unit_cell_dims = tuple([
          solution[dim]['mean'] for dim in ['a', 'b', 'c', 'alpha', 'beta', 'gamma']
        ])
      unit_cell_esds = tuple([
          solution[dim]['population_standard_deviation'] for dim in ['a', 'b', 'c', 'alpha', 'beta', 'gamma']
        ])

  cb_op = crystal_symm.change_of_basis_op_to_reference_setting()

  if cb_op.c().r().as_hkl() == 'h,k,l':
    print 'Change of basis to reference setting: %s' % cb_op
    crystal_symm = crystal_symm.change_basis(cb_op)
    if str(cb_op) != "a,b,c":
      unit_cell_dims = None
      unit_cell_esds = None
      # Would need to apply operation to cell errors, too. Need a test case for this

  # crystal_symm.show_summary()
  xray_structure = structure(crystal_symmetry=crystal_symm)
  if compound:
    result = parse_compound(compound)
    for element in result:
      xray_structure.add_scatterer(scatterer(label=element,
                                             occupancy=result[element]))
  open('%s.ins' % prefix, 'w').write(''.join(
    writer.generator(xray_structure,
                     wavelength=wavelength,
                     full_matrix_least_squares_cycles=0,
                     title=prefix,
                     unit_cell_esds=unit_cell_esds)))
  generate_cif(prefix=prefix, unit_cell_data=cell_data, wavelength=wavelength, structure=xray_structure)

if __name__ == '__main__':
  parser = optparse.OptionParser("usage: %prog .mtz-file output-file [atoms]")
  parser.add_option("-?", action="help", help=optparse.SUPPRESS_HELP)
  parser.add_option("-w", "--wavelength", dest="wavelength", help="Override experimental wavelength (Angstrom)", default=None, type="float")
  parser.add_option("-c", "--cell", dest="cell", metavar="FILE", help="Read unit cell information from a .json file", default=None, type="string")
  options, args = parser.parse_args()
  if len(args) > 2:
    atoms = ''.join(args[2:])
    print 'Atoms: %s' % atoms
    to_shelx(args[0], args[1], atoms, options)
  elif len(args) == 2:
    print options
    to_shelx(args[0], args[1], options=options)
  else:
    parser.print_help()
