#!/usr/bin/env python3

import sys						# For exiting and stderr printing
import re						# Regular expressions
import subprocess				# To start subprocesses like GNU parallel or Copasi
from datetime import datetime	# To get a feeling of time
from shutil import which		# To check whether a given Copasi program name is valid

class Copasi:
	"""
	This class opens a Copasi file (*.cps), checks its version and provides useful tools to manipulate it.
	"""

	def __init__(self, filename):
		self.testedVersions = ['4.14 (Build 89)', '4.15 (Build 95)']
		self.filename = filename
		if not self.filename.endswith('.cps'):
			self.filename += '.cps'
		self.content = self.openCopasiFile()
		self.version = self.getVersion()
		if not self.checkVersion():
			self._errorReport('The Copasi file version ({}) is not supported.'.format(self.version))


	def __str__(self):
		return 'Copasi model object "{}", file version {}, with {} compartments, {} species, and {} reactions'.format(self.getTitle(), self.version, len(self.getCompartments()), len(self.getMetabolites()), len(self.getReactions()))


	def _getValidFilename(self, filename):
		"""
		Turns any string into a valid and sanitized path and filename.

		:param filename: The filename to be sanitized
		:returns: A valid (conservative) filename
		"""

		keepcharacters = ('.', '_', '/')
		return ''.join(c for c in filename if c.isalnum() or c in keepcharacters)


	def _errorReport(self, text, fatal = False):
		"""
		Reports errors and aborts if the error is fatal.

		:param text: String to be printed
		:param fatal: Boolean to state whether the error is fatal
		"""

		textend = ('Continuing.', 'Aborting.')

		print('{} {}: {} - {}'.format(datetime.now().strftime('%c'), self.filename, text, textend[fatal]), file=sys.stderr)
		if fatal:
			sys.exit(1)


	def getVersion(self):
		"""
		Extracts the version of the loaded Copasi file.

		:returns: The version of the Copasi file as a string
		"""

		reResult = re.search(r'<!-- generated with COPASI ([0-9\.]+ \(Build [0-9]+\)) \(http://www.copasi.org\)', self.content)
		try:
			copVersion = reResult.group(1)
		except AttributeError:
			self._errorReport('The version of the Copasi file could not be determined.')
			copVersion = None

		return copVersion


	def checkVersion(self):
		"""
		Checks if the loaded Copasi version is compatible with this script.

		:returns: Whether or not the given Copasi version is compatible with this script (bool)
		"""

		return self.version in self.testedVersions


	def openCopasiFile(self):
		"""
		Opens a Copasi file.

		:returns: The content of the Copasi file as a string
		"""

		try:
			with open(self.filename, 'r', encoding='utf-8') as f:
				content = f.read()
		except OSError as e:
			self._errorReport('An OS Error was raised while reading the input file.\n{}'.format(e), fatal = True)

		return content


	def saveCopasiFile(self, filename):
		"""
		Saves a Copasi file to disk.

		:param filename: The name for the file to save (may include some path)
		:returns: The actual, sanitized filename that was used to save the file
		"""

		filename = self._getValidFilename(filename)

		try:
			with open(filename, 'w', encoding='utf-8') as f:
				f.write(self.content)
		except OSError as e:
			self._errorReport('An OS Error was raised while writing an output file.\n{}'.format(e), fatal = True)

		return filename


	def checkCopasiSE(self, copasiPath):
		"""
		Checks whether a given CopasiSE program exists and if it is the right version. If a program defined by the user is not existing, the standard names in the $PATH are checked (i.e. copasise and CopasiSE).

		:param copasiPath: A user-given path to Copasi (may also contain just the name for calling, like "copasise", if the program is in the PATH)
		:returns: A valid Copasi path or name
		"""

		# Check for existance of a given CopasiSE path or the standard names.
		if which(copasiPath) is None:
			if which('CopasiSE') is None:
				if which('copasise') is None:
					self._errorReport('CopasiSE not found. Neither in the given path ({}), nor as "CopasiSE".'.format(copasiPath), fatal = True)
				else:
					self._errorReport('"{}" not found, switching to "copasise"'.format(copasiPath))
					copasiPath = 'copasise'
			else:
				self._errorReport('"{}" not found, switching to "CopasiSE"'.format(copasiPath))
				copasiPath = 'CopasiSE'

		# Check the program version of the given CopasiSE. Call e.g. copasise -h and only keep the stdout, not stderr
		output = subprocess.check_output([copasiPath, "-h"], universal_newlines = True, stderr=subprocess.DEVNULL)
		if self.version not in output:
			self._errorReport('The version of the given CopasiSE ({}) is not the same as for the given Copasi file ({}).'.format(output.split('\n')[0][7:], self.version))

		return copasiPath


	def parallelCopasi(self, fileList, copasiPath = 'copasise', maxParallelJobs = 0, evalExitCode = True):
		"""
		Execute CopasiSE in parallel with a given list of files. This function requires GNU parallel!

		:param fileList: The list of Copasi files as strings that shall be executed
		:param copasiPath: Path to CopasiSE or it's name in the PATH variable. Defaults to 'copasise'
		:param maxParallelJobs: Maximum number of jobs to execute in parallel. Defaults to the number of cores (incl. hyperthreading)
		:param evalExitCode: When True, this script waits for CopasiSE to exit and gives notice. If false, this scripts starts CopasiSE in independet process(es) and exits.
		"""

		copasiPath = self.checkCopasiSE(copasiPath)

		if len(fileList) > 0:
			if evalExitCode:
				# Starts parallel, waits until it's finished and evaluates the exit code
				startTime = datetime.now()
				self._notify(subprocess.call("parallel -j {} {} '>>' copasiOut.txt '2>&1' ::: {}".format(maxParallelJobs, copasiPath, ' '.join(fileList)), shell=True), fileList, startTime)
			else:
				# Starts parallel and exits.
				subprocess.Popen("parallel -j {} {} '>>' copasiOut.txt '2>&1' ::: {}".format(maxParallelJobs, copasiPath, ' '.join(fileList)), shell=True)
		else:
			self._errorReport('No file found to execute.')


	def runCopasi(self, cpsFile, copasiPath = 'copasise'):
		"""
		Run Copasi with a given file. This function is intended to use on a computer or cluster with another Python script calling it with multiprocessing to allow for parallel excecution without GNU parallel.

		:param fileList: The Copasi file to be excecuted
		:param copasiPath: Path to CopasiSE or it's name in the PATH variable. Defaults to 'copasise'
		"""

		copasiPath = self.checkCopasiSE(copasiPath)

		subprocess.call('{} {}'.format(copasiPath, cpsFile), shell=True)


	def _notify(self, exitCode, fileList, startTime):
		"""
		Give some sort of notification when CopasiSE is finished.
		##### I don't know yet, what kind of notification is best. Writing to some file would be ok. An e-mail would be great, but I need access to some SMTP server to do that.

		:param exitCode: The exit code of the former programm call (usually CopasiSE)
		:param fileList: The list of Copasi files as strings that were executed
		:param startTime: A datetime object of the starting time of the process(es)
		"""

		# Get total wallclock time for execution.
		totalTime = datetime.now() - startTime

		if exitCode > 0:
			cpsError = 'WITH EXIT CODE {} (i.e. an error occured)'.format(exitCode)
		else:
			cpsError = 'without error'

		with open('AA_FINISHED_' + self.filename.replace('.cps', ''), 'w') as f:
			f.write('CopasiSE finished {} the following files in {}:\n\n{}\n\nNothing more to do.'.format(cpsError, str(totalTime), '\n'.join(fileList)))


	def turnToNumbers(self, mylist, referenceList):
		"""
		Tries to turn every element of a list into an integer, using the provided reference dict. If a non-number element of mylist is not found in referencelist, an error is printed to stderr and the script aborts.

		:param mylist: list that shall be turned to integers.
		:param referenceList: tuple in the form that can be used as reference for non-number strings in mylist
		:returns: A list of integers that correspond to the elements in referencelist
		"""

		for n in range(len(mylist)):
			# If we have a number, use it
			try:
				mylist[n] = int(mylist[n])
			# If we don't have a number, see if we find it in the reference list (reactions or metabolites) and use it. Otherwise abort.
			except ValueError:
				if mylist[n] in referenceList:
					mylist[n] = referenceList.index(mylist[n])	# Use the index of that element in the reference List
				else:
					self._errorReport('The element "{}" was not found.'.format(mylist[n]), fatal = True)

		return mylist


	def getReactions(self):
		"""
		Extracts all reactions from a given Copasi file and orders them according to the MCA optimization in CopasiUI.

		:returns: A tuple of strings in the form (str(reactionA), str(reactionB), ...). The tuple index of each string is the reaction number.
		"""

		# Rules for getting reaction numbers in the right order (Copasi 4.14 build 89):
		# - Search for all »<Reaction key="Reaction_XX" name="YY" ... >«
		# - The number to the according name (YY) is simply the order in which it occures in the cps file, starting with 0 (zero)
		# - The reaction number (XX) is NOT important at all

		reactions = []	# We first need to store reactions in a list, as lists are mutable, while tuples are not
		# read every line of the Copasi file (might be more efficient if we stop after a certain number of lines of no match).
		for line in self.content.split('\n'):
			# "<Reaction" only occurs in lines defining new reactions
			if '<Reaction' in line:
				# We look for »key="Reaction_INT" name="STRING"« in that line and extract number and name
				reResult = re.search('key="Reaction_[0-9]+" name="([^"]+)"', line)
				try:
					reactions.append(reResult.group(1))
				except AttributeError as e:
					self._errorReport('There is a failure in finding reactions. This should never happen!\n{}'.format(e), fatal = True)

		return tuple(reactions)	# We use a tuple as it is immutable and a consistent tuple is important for various tasks


	def getMetabolites(self):
		"""
		Extracts all metabolites from a given Copasi file and orders them accoring to the MCA optimization in CopasiUI. If the model consists of more than one compartment, the compartment names are appended to the metabolite names with an underscore between them. So NAD in the cytosol will turn to NAD_cytosol if there are more compartments present.

		:returns: A tuple of strings in the form (str(metaboliteA), str(metaboliteB), ...). The tuple index of each string is the metabolite number.
		"""

		# Rules for getting metabolite numbers in the right order (Copasi 4.14 build 89):
		# - Search for all »<Metabolite key="Metabolite_XX" name="YY" simulationType="reactions" ... >«
		# - Now you have a list of all relevant metobolites (with »simulationType="reactions"« NOT »"fixed"«)
		# - Search for »<StateTemplateVariable objectReference="Metabolite_XX"/>«
		# - The number to the according name (YY) is the order in which its number (XX) occures »<StateTemplateVariable«-list, starting with 0 (zero)
		# - The metabolite number (XX) is NOT important for the order, just for identification in the »<StateTemplateVariable«-list

		# Retreive all compartments. If there are more than one, the compartment name shall be appended to the metabolite name
		compartments = self.getCompartments()
		appendComp = len(compartments) > 1

		metabolites = []	# We first need to store metabolites in a list, as lists are mutable, while tuples are not
		metaBuffer = {}		# For first storing all available metabolites without any order
		# read every line of the Copasi file (might be more efficient if we stop after certain lines of no match).
		for line in self.content.split('\n'):
			# "<Metabolite" only occurs in lines defining new metabolites
			if '<Metabolite' in line:
				# We look for »key="Metabolite_INT" name="STRING" simulationType="reactions" compartment="Compartment_INT"« in that line and extract number, name, and compartment name
				# Only »simulationType="reactions"« can be used for MCA (all others are fixed)
				reResult = re.search('key="Metabolite_([0-9]+)" name="([^"]+)" simulationType="reactions" compartment="(Compartment_[0-9]+)"', line)
				if reResult is not None:
					if appendComp:
						metaBuffer[reResult.group(1)] = reResult.group(2) + '_' + compartments[reResult.group(3)]
					else:
						metaBuffer[reResult.group(1)] = reResult.group(2)
			elif '<StateTemplateVariable' in line:
				reResult = re.search('objectReference="Metabolite_([0-9]+)"', line)
				if reResult is not None and reResult.group(1) in metaBuffer:
					metabolites.append(metaBuffer[reResult.group(1)])

		return tuple(metabolites)	# We use a tuple as it is immutable and a consistent tuple is important for various tasks


	def getCompartments(self):
		"""
		Extracts all compartments from a given Copasi file.

		:returns: A dictionary with the compartments in the form {'Compartment_n': 'visibleName', ...}
		"""

		compartments = {}
		# read every line of the Copasi file (might be more efficient if we stop after certain lines of no match or start later).
		for line in self.content.split('\n'):
			# Tags with "<Compartment" only occur in lines defining new compartments
			if '<Compartment' in line:
				# We look for »key="Compartment_INT" name="STRING"« in that line and extract number and name
				reResult = re.search('key="(Compartment_[0-9]+)" name="([^"]+)"', line)
				if reResult is not None:
					compartments[reResult.group(1)] = reResult.group(2)

		return compartments


	def getTitle(self):
		"""
		Extracts the model title from a given Copasi file.

		:returns: A string with the title
		"""

		# read every line of the Copasi file until we find the model definition.
		for line in self.content.split('\n'):
			# The space after »Model« is important as there are also »<ModelParameterSet« tags
			if '<Model ' in line:
				# We look for »name="STRING"« in that line and extract the title/name
				reResult = re.search('name="([^"]+)"', line)
				if reResult is None:
					self._errorReport('I could not find a title.')
					title = '!No title found!'
				else:
					title = reResult.group(1)
				break

		return title


	def getMCAType(self):
		"""
		Determines the type of MCA optimization. Scaled/unscaled is not determined.
		- concentration control coefficients (ccc): metabolites/reactions
		- elasticities (e): reactions/metabolites
		- flux control coefficients (fcc): reactions/reactions

		:returns: A string with the type of the MCA optimization (short form) or None if the type could not be determined
		"""

		# The possible outcomes and their abbreviations
		outcomes = {'concentration control coefficients': 'ccc', 'elasticities': 'e', 'flux control coefficients': 'fcc'}

		# Trying to find »caled TYPE[« where TYPE is the MCA optimization type. This string should only be available once in a Copasi file.
		try:
			reResult = re.search('caled ([^\[]+)\[', self.content)
			result = outcomes[reResult.group(1)]
		except (AttributeError, IndexError): # If nothing is found, .group() is called on None, so it raises an AttributeError; If something was found but it is not in the dict of possible outcomes, it raises an Index Error
			result = None

		return result


	def setMCAOptiParameters(self, objleft, objright):
		"""
		Replaces the original reactions/metabolites in an MCA optimization in a given Copasi file with the new ones.

		:param objleft: The first optimization objective (row)
		:param objright: The second optimization objective (column)
		"""

		# subn returns a tupel: (new_string, number_of_subs_made)
		reBuffer = re.subn('\[\d*\]\[\d*\]', '[' + str(objleft) + '][' + str(objright) + ']', self.content)
		# If no replacement was made, abort.
		if reBuffer[1] == 0:
			self._errorReport('The optimization targets could not be replaced. The Copasi file is probably not configured for MCA optimization. Please see, if you chose the correct Copasi file and if it is configured correctly for MCA.', fatal = True)
		# If more than one replacement was made, print an error, but go on executing.
		elif reBuffer[1] > 1:
			self._errorReport('There were more than one objectives that were changed.')

		self.content = reBuffer[0]


	def setOptiMinMax(self, minimize, warn = False):
		"""
		Sets the optimization to maximize or minimize the target.

		:param minimize: Boolean. If True, minimize target, else maximize the target
		"""

		# subn returns a tupel: (new_string, number_of_subs_made)
		reBuffer = re.subn('<Parameter name="Maximize" type="bool" value="\d"/>', '<Parameter name="Maximize" type="bool" value="' + str(int(bool(not minimize))) + '"/>', self.content)
		# If no replacement was made, abort.
		if reBuffer[1] == 0:
			self._errorReport('The setting whether to minimize or maximize the target could not be set.', fatal = True)
		# If more than one replacement was made, print an error, but go on executing.
		elif reBuffer[1] > 1 and warn:
			self._errorReport('The setting whether to minimize or maximize the target was changed multiple times.')

		self.content = reBuffer[0]


	def setOptimizationTargetType(self, optiType):
		"""
		Sets the optimization target type (FCC, CCC, E, uFCC, uCCC, uE), where "u" stands for unscaled.

		:param optiType: A string with the optimization type (see above)
		"""

		types = {'CCC': 'Scaled concentration control coefficients',
				'FCC': 'Scaled flux control coefficients',
				'E': 'Scaled elasticities',
				'uCCC': 'Unscaled concentration control coefficients',
				'uFCC': 'Unscaled flux control coefficients',
				'uE': 'Unscaled elasticities'}

		if optiType not in types:
			self._errorReport('The optimization target type "{}" is no valid target type'.format(optiType), fatal = True)

		# subn returns a tupel: (new_string, number_of_subs_made)
		reBuffer = re.subn(r'Array=[^\[]+\[(\d+)\]\[(\d+)\]', 'Array=' + types[optiType] + r'[\1][\2]', self.content)
		# If no replacement was made, abort.
		if reBuffer[1] == 0:
			self._errorReport('The optimization target type could not be set. The Copasi file is probably not configured for MCA optimization.', fatal = True)
		# If more than one replacement was made, print an error, but go on executing.
		elif reBuffer[1] > 1:
			self._errorReport('There were more than one target types that were changed.')

		self.content = reBuffer[0]



	def setOptimizationMethod(self, method):
		"""
		Sets the method for an optimization. Not all methods are available, yet. Only standard parameters will be set.

		:param method: A string with the method. Choose from: EP, PS
		"""

		toSearch = r'<Task ([^n]+) name="Optimization"([\S\s]+?)<Method [\S\s]+?</Method>'

		if method == 'EP':
			toReplace = r'''<Task \1 name="Optimization"\2<Method name="Evolutionary Programming" type="EvolutionaryProgram">
        <Parameter name="Number of Generations" type="unsignedInteger" value="200"/>
        <Parameter name="Population Size" type="unsignedInteger" value="40"/>
        <Parameter name="Random Number Generator" type="unsignedInteger" value="1"/>
        <Parameter name="Seed" type="unsignedInteger" value="0"/>
      </Method>'''
		elif method == 'PS':
			toReplace = r'''<Task \1 name="Optimization"\2<Method name="Particle Swarm" type="ParticleSwarm">
        <Parameter name="Iteration Limit" type="unsignedInteger" value="2000"/>
        <Parameter name="Swarm Size" type="unsignedInteger" value="50"/>
        <Parameter name="Std. Deviation" type="unsignedFloat" value="1e-06"/>
        <Parameter name="Random Number Generator" type="unsignedInteger" value="1"/>
        <Parameter name="Seed" type="unsignedInteger" value="0"/>
      </Method>'''
		else:
			self._errorReport('Optimization method {} not implemented'.format(method), fatal = True)

		# subn returns a tupel: (new_string, number_of_subs_made)
		reBuffer = re.subn(toSearch, toReplace, self.content)
		# If no replacement was made, abort.
		if reBuffer[1] == 0:
			self._errorReport('The optimization method could not be changed to {} in {}.'.format(method, self.filename), fatal = True)
		# If more than one replacement was made, print an error, but go on executing.
		elif reBuffer[1] > 1:
			self._errorReport('The optimization method was changed to {} more than once in {}.'.format(method, self.filename), fatal = True)

		self.content = reBuffer[0]


	def setTaskToMCA(self):
		"""
		Sets the Optimization Task to MCA.
		"""

		# subn returns a tupel: (new_string, number_of_subs_made)
		reBuffer = re.subn(r'<Parameter name="Subtask" type="cn" value="CN=Root,Vector=TaskList\[[^\]]+\]"/>', '<Parameter name="Subtask" type="cn" value="CN=Root,Vector=TaskList[Metabolic Control Analysis]"/>', self.content)
		# If no replacement was made, abort.
		if reBuffer[1] == 0:
			self._errorReport('The target could not be set to MCA.', fatal = True)
		# If more than one replacement was made, print an error, but go on executing.
		elif reBuffer[1] > 1:
			self._errorReport('The optimization target was changed to MCA more than once.')

		self.content = reBuffer[0]


	def setReportFileName(self, reportFile, warn = False):
		"""
		Changes the report file name in a given Copasi file.

		:param reportFile: A string with the new file name of the report file
		"""

		reportFile = self._getValidFilename(reportFile)

		# subn returns a tupel: (new_string, number_of_subs_made)
		reBuffer = re.subn('target="[^"]+"', 'target="' + reportFile + '"', self.content)
		# If no replacement was made, abort.
		if reBuffer[1] == 0:
			self._errorReport('The output filename could not be changed.', fatal = True)
		# If more than one replacement was made, print an error, but go on executing.
		elif reBuffer[1] > 1 and warn:
			self._errorReport('The output filename was changed on several occurances.')

		self.content = reBuffer[0]


	def setOptimizationItem(self, name, lower, start, upper, parameter = None):
		"""
		Changes the values of an optimization item.

		There are two types of optimization targets. For values (1), you don't need an parameter, for reactions (2) you do need one.

		(1) CN=xxx,Model=xxx,Vector=Values[NAME],Reference=xxx
		(2) CN=xxx,Model=xxx,Vector=Reactions[NAME],ParameterGroup=xxx,Parameter=PARAMETER,Reference=xxx

		:param name: The name of the parameter to change
		:param lower: The lower bound of the parameter
		:param start: The start value of the parameter
		:param upper: The upper bound of the parameter
		:param parameter: The parameter to change
		"""

		if parameter is None:
			toSearch = r'<Parameter name="LowerBound" type="cn" value="[^"]+"/>\s+<Parameter name="ObjectCN" type="cn" value="(.+)\[' + name + r'\](.+)"/>\s+<Parameter name="StartValue" type="float" value="[^"]+"/>\s+<Parameter name="UpperBound" type="cn" value="[^"]+"/>'

			toReplace = r'<Parameter name="LowerBound" type="cn" value="' + lower + r'"/>\n            <Parameter name="ObjectCN" type="cn" value="\1[' + name + r']\2"/>\n            <Parameter name="StartValue" type="float" value="' + start + r'"/>\n            <Parameter name="UpperBound" type="cn" value="' + upper + r'"/>'
		else:
			toSearch = r'<Parameter name="LowerBound" type="cn" value="[^"]+"/>\s+<Parameter name="ObjectCN" type="cn" value="([^\[]+)\[' + name + r'\]([^"]+)Parameter=' + parameter + r'([^"]+)"/>\s+<Parameter name="StartValue" type="float" value="[^"]+"/>\s+<Parameter name="UpperBound" type="cn" value="[^"]+"/>'

			toReplace = r'<Parameter name="LowerBound" type="cn" value="' + lower + r'"/>\n            <Parameter name="ObjectCN" type="cn" value="\1[' + name + r']\2Parameter=' + parameter + '\3"/>\n            <Parameter name="StartValue" type="float" value="' + start + r'"/>\n            <Parameter name="UpperBound" type="cn" value="' + upper + r'"/>'

		# subn returns a tupel: (new_string, number_of_subs_made)
		reBuffer = re.subn(toSearch, toReplace, self.content)
		# If no replacement was made, abort.
		if reBuffer[1] == 0:
			self._errorReport('The item {} could not be changed.'.format(name), fatal = True)
		# If more than one replacement was made, print an error, but go on executing.
		elif reBuffer[1] > 1:
			self._errorReport('The item {} was changed on several occurances.'.format(name))

		self.content = reBuffer[0]


	def delOptimizationItem(self, name, parameter = None):
		"""
		Deletes an optimization item.

		There are two types of optimization targets. For values (1), you don't need an parameter, for reactions (2) you do need one.

		(1) CN=xxx,Model=xxx,Vector=Values[NAME],Reference=xxx
		(2) CN=xxx,Model=xxx,Vector=Reactions[NAME],ParameterGroup=xxx,Parameter=PARAMETER,Reference=xxx

		:param name: The name of the item to delete
		:param parameter: The name of the parameter of the item to delete or None
		"""

		if parameter is None:
			toSearch = r'\s+<ParameterGroup name="OptimizationItem">\s+<[^>]+>\s+<Parameter name="ObjectCN" type="cn" value="[^\[]+\[' + name + r'\][^"]+"/>\s+<[^>]+>\s+<[^>]+>\s+</ParameterGroup>'
		else:
			toSearch = r'\s+<ParameterGroup name="OptimizationItem">\s+<[^>]+>\s+<Parameter name="ObjectCN" type="cn" value="[^\[]+\[' + name + r'\][^"]+Parameter=' + parameter + r'[^"]+"/>\s+<[^>]+>\s+<[^>]+>\s+</ParameterGroup>'

		# subn returns a tupel: (new_string, number_of_subs_made)
		reBuffer = re.subn(toSearch, '', self.content)
		p = ':'+parameter if parameter is not None else ''
		# If no replacement was made, abort.
		if reBuffer[1] == 0:
			self._errorReport('The item "{}{}" to delete could not be found.'.format(name, p), fatal = True)
		# If more than one replacement was made, print an error, and abort.
		elif reBuffer[1] > 1:
			self._errorReport('The item "{}{}" was deleted on several occurances.'.format(name, p), fatal = True)

		self.content = reBuffer[0]


	def setParameter(self, reaction, parameter, value):
		"""
		Changes a parameter of a reaction to a given value.

		:param reaction: The reaction of which the parameter shall be changed
		:param parameter: The parameter to change
		:param value: The new value of the parameter
		"""

		# subn returns a tupel: (new_string, number_of_subs_made)
		reBuffer = re.subn(r'Reactions\[' + reaction + r'\],ParameterGroup=([^,]+),Parameter=' + parameter + r'" value="[^"]+"', r'Reactions[' + reaction + r'],ParameterGroup=\1,Parameter=' + parameter + r'" value="' + str(value) + r'"', self.content)
		# If no replacement was made, print an error, but go on executing.
		if reBuffer[1] == 0:
			self._errorReport('The parameter {} in reaction {} could not be found.'.format(parameter, reaction))
		# If more than one replacement was made, print an error, but go on executing.
		elif reBuffer[1] > 1:
			self._errorReport('The parameter {} in reaction {} was found multiple times. All were replaced.'.format(parameter, reaction))

		self.content = reBuffer[0]
