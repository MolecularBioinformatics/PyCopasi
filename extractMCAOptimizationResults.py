#!/usr/bin/env python3

helptext = '''Extracts results from an MCA optimization. Expects a list of files with MCA optimization results. The names of the result files must be in this format: `someName_row_column.txt`. This format is automatically generated when `updateMCAOptimizationTarget.py` was used to generate the output files.

Start the script e.g. like this:
./extractMCAOptimizationResults.py myResult_abc_def.txt myResult_abc_ghi.txt'''

import sys

if len(sys.argv) < 2:
	print(helptext)
	sys.exit()

results = {}

for filename in sys.argv[1:]:
	with open(filename, 'r') as f:
		basefile = filename.replace('.txt', '')
		reactions = basefile.split('_')
		column = reactions.pop()
		row = reactions.pop()
		scan = '_'.join(reactions)
		for line in f:
			if 'Objective Function Value:' in line:
				value = line.split('\t')[1].strip()
				if scan not in results:
					results[scan] = []
				results[scan].append('\t'.join((row, column, value)))

for scan in sorted(results.keys()):
	outfile = scan + '_summary.txt'
	with open(outfile, 'w') as out:
		out.write('\n'.join(results[scan]))
