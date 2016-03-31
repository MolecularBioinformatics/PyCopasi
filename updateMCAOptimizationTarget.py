#!/usr/bin/env python3

helptext = '''Change the targets for MCA optimization. The script expects a file name
that points to a Copasi file that shall be changed. In addition, it
expects a comma-seperated list of numbers or names of reactions or
metabolites that should be used for the left side and another list for
the right side. Alternatively, either of the lists (or both) can be
replaced by "all" (w/o "). No spaces are allowed in the lists. The type
of MCA optimization is derived from the Copasi file. By this, the type
of lists (reactions or metabolites) is determined. Output file names a
derived from the input file name.

Start the script e.g. like this:
./updateMCAOptimizationTarget.py myCopasiFile.cps 4,6,ReactA all'''


import sys
from copasi import Copasi	# Copasi class for all modifications
import argparse				# To parse arguments


def makeList(x):
	"""
	Helper for Argument Parser

	:param x: A string with elements seperated by kommas (,)
	:returns: A list with the elements
	"""

	return x.split(',')


# Create a new argument parser object
parser = argparse.ArgumentParser(description=helptext)
# We need one input file
parser.add_argument('infile', metavar='myfile.cps', help='Copasi file that shall be modified and run.')
# List of row parameters
parser.add_argument('objLeft', type=makeList, metavar='rows', help='The parameters of rows that shall be changed. These can be numbers, names or both, seperated by kommas (,). May also be "all" without quotation marks to address all parameters.')
# List of column parameters
parser.add_argument('objRight', type=makeList, metavar='columns', help='The parameters of columns that shall be changed. See "rows" for details.')
# Optionally, we take a switch to use a server Jobarray instead of a local system
parser.add_argument('-j', '--jobarray', action='store_true', help='If active, Copasi filenames are just numbered and not changed to meaningful names. This implies -n.')
# Optionally, we take a switch whether to run the generated files or not
parser.add_argument('-n', '--norun', action='store_true', help='If active, Copasi files are just generated but Copasi is not started.')
args = parser.parse_args()


objectiveleft = args.objLeft
objectiveright = args.objRight

# if the files are prepared for a jobarray, we don't want to run them anyway on the local computer
if args.jobarray:
	args.norun = True

# create a basefile that is the infile without ending
basefile = args.infile.replace('.cps', '')

# create a new Copasi instance
copasi = Copasi(args.infile)

# Get a list of reactions and (usable) metabolites with name and number
reactions = copasi.getReactions()
metabolites = copasi.getMetabolites()

# See, what kind of components we need for left and right objectives (reactions or metabolites)
mcatype = copasi.getMCAType()
if mcatype == 'ccc':
	lefttype = metabolites
	righttype = reactions
elif mcatype == 'e':
	lefttype = reactions
	righttype = metabolites
elif mcatype == 'fcc':
	lefttype = reactions
	righttype = reactions
else:
	print('This MCA type is unknown: {}. Aborting.'.format(mcatype), file=sys.stderr)
	sys.exit(56)

# replace the keyword "all" with the full list of reactions/metabolites
if objectiveleft[0] == 'all':
	objectiveleft = list(lefttype)
if objectiveright[0] == 'all':
	objectiveright = list(righttype)

# turn every element of the lists into an integer
objectiveleft = copasi.turnToNumbers(objectiveleft, lefttype)
objectiveright = copasi.turnToNumbers(objectiveright, righttype)

execList = []	# This list saves all copasi-files in order to execute them later

i = 1 # This variable is used for renaming the files when they are used on Stallo

# modify the original file for each objective-pair and create new files accordingly
for objleft in objectiveleft:
	if objleft >= len(lefttype):
		print('The objective ({0}) is not part of the model! Continuing with other objectives.'.format(objleft), file=sys.stderr)
		continue

	for objright in objectiveright:
		if objright >= len(righttype):
			print('The objective ({0}) is not part of the model! Continuing with other objectives.'.format(objright), file=sys.stderr)
			continue

		# It doesn't make sense to have both parts the same in FCC, as both are reactions. In ccc and e, one is reaction, the other metabolite, so it's ok
		if objleft == objright and mcatype == 'fcc':
			continue

		outfilebase = basefile + '_' + lefttype[objleft] + '_' + righttype[objright]

		if args.jobarray:
			outfilebase += '_' + str(i)

		# replace the original reactions/metabolites with the new ones
		copasi.setMCAOptiParameters(objleft, objright)

		# Set the task to Metabolic Control Analysis
		copasi.setTaskToMCA()

		# replace the report file name
		copasi.setReportFileName(outfilebase + '.txt')

		# Save the modified file to disk and add it to the list of files that shall be executed in parallel
		execList.append(copasi.saveCopasiFile(outfilebase + '.cps'))

		i += 1

if not args.norun:
	# Run all generated Copasi files in parallel
	copasi.parallelCopasi(execList)#, copasiPath = 'echo') # echo is for debugging
