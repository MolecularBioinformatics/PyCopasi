#!/usr/bin/env python3

'''Extracts species concentrations and reaction fluxes from steady state results. Expects a list of result files that may include placeholders like * and [1-4]. As Copasi does not give any model name or simliar in the output file, the header of the table will be the name of the file without path or extension (path/to/myfile.txt -> myfile).

Start the script e.g. like this:
./extractFluxConcFromResults.py myRes[1-6].txt myOldRes*.txt'''

import re
import os.path

def _get_values_from_single_file(f, fn, conc_dict, flux_dict):
	if not f.startswith('A steady state with given resolution was found.'):
		return

	active = ''

	for line in f.split('\n'):
		line = line.strip()
		if active == 'conc':
			if not line:
				active = ''
				continue
			lline = line.split('\t')
			name = lline[0]
			conc = lline[1]
			if name not in conc_dict:
				conc_dict[name] = {}
			conc_dict[name][fn] = conc
		elif active == 'flux':
			if not line:
				break
			lline = line.split('\t')
			name = lline[0]
			flux = lline[1]
			if name not in flux_dict:
				flux_dict[name] = {}
			flux_dict[name][fn] = flux
		elif line.startswith('Species	Concentration'):
			active = 'conc'
		elif line.startswith('Reaction	Flux'):
			active = 'flux'


def get_tables(filenames):
	conc_dict = {}
	flux_dict = {}

	names = [os.path.splitext(os.path.basename(fn))[0] for fn in filenames]

	for i, fn in enumerate(filenames):
		with open(fn, 'r') as f:
			content = f.read()
		_get_values_from_single_file(content, names[i], conc_dict, flux_dict)

	conc_list = []
	conc_list.append('\t' + '\t'.join(names))
	for conc in sorted(conc_dict.keys()):
		row = [conc]
		for name in names:
			try:
				row.append(conc_dict[conc][name])
			except KeyError:
				row.append('na')
		conc_list.append('\t'.join(row))

	flux_list = []
	flux_list.append('\t' + '\t'.join(names))
	for flux in sorted(flux_dict.keys()):
		row = [flux]
		for name in names:
			try:
				row.append(flux_dict[flux][name])
			except KeyError:
				row.append('na')
		flux_list.append('\t'.join(row))

	return '\n'.join(conc_list), '\n'.join(flux_list)


def get_units(f):
	res = re.search('Species	Concentration \(([^\)]+)\)', f)
	try:
		conc_unit = 'Concentration ({})'.format(res.group(1))
	except AttributeError:
		conc_unit = 'Concentration'

	res = re.search('Reaction	Flux \(([^\)]+)\)', f)
	try:
		flux_unit = 'Flux ({})'.format(res.group(1))
	except AttributeError:
		flux_unit = 'Flux'

	return conc_unit, flux_unit


if __name__ == '__main__':
	from glob import glob
	import sys

	if len(sys.argv) < 2:
		print(__doc__)
		sys.exit()

	filenames = []
	for fn in sys.argv[1:]:
		filenames.extend(glob(fn))

	conc, flux = get_tables(filenames)

	with open('conc_table.tsv', 'w') as f:
		f.write(conc)

	with open('flux_table.tsv', 'w') as f:
		f.write(flux)
