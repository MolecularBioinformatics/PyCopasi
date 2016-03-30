#!/usr/bin/env python3

helptext = '''Copies a given copasi file n times with changed output file name and starts all copied copasi files in parallel. The original Copasi file will remain untouched (i.e. only read access is performed). This script requires GNU parallel.

Tested with Copasi version: 4.14 (build 89)'''


import sys					# To exit
from copasi import Copasi	# Copasi class for all modifications
import argparse				# To parse arguments


# Create a new argument parser object
parser = argparse.ArgumentParser(description=helptext)
# We need one input file
parser.add_argument('infile', metavar='myfile.cps', help='Copasi file that shall be run in parallel.')
# And we need the total number of excecutions
parser.add_argument('totNumber', type=int, metavar='totalNumber', help='How often the given file shall be executed in total.')
# Optionally, we take the path to CopasiSE
parser.add_argument('-c', '--copasi', default='copasise', metavar='copasise', help='Path to CopasiSE or shell command to start CopasiSE.')
# Optionally, we take the maximum number of parallel processes at the same time
parser.add_argument('-p', '--parallel', type=int, default=10, metavar='#', help='Maximum number of parallel processes at the same time.')
args = parser.parse_args()


# create a basefile string that is the infile without ending
basefile = args.infile.replace('.cps', '')

# Create a new Copasi instance
copasi = Copasi(args.infile)

execList = []	# This list saves all copasi-files in order to execute them later

for m in range(args.totNumber):
	outfilebase = basefile + '_' + str(m+1)

	# replace the report file name
	copasi.setReportFileName(outfilebase + '.txt')

	# Save the modified file to disk and add it to the list of files that shall be executed in parallel
	execList.append(copasi.saveCopasiFile(outfilebase + '.cps'))

# Run all generated Copasi files in parallel
copasi.parallelCopasi(execList, copasiPath = args.copasi, maxParallelJobs = args.parallel)
