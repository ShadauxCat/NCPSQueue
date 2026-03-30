# Copyright (C) 2016 Jaedyn K. Draper
#
# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the "Software"),
# to deal in the Software without restriction, including without limitation
# the rights to use, copy, modify, merge, publish, distribute, sublicense,
# and/or sell copies of the Software, and to permit persons to whom the
# Software is furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL
# THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

"""
.. module:: shared_globals
	:synopsis: Global variables that need to be accessed by multiple modules

.. moduleauthor:: Jaedyn K. Draper
"""

from __future__ import unicode_literals, division, print_function

from . import dag

errors = []
warnings = []
colorSupported = False
logFile = None

toolchains = {}

sortedProjects = dag.DAG(lambda x: x.name)
allTargets = set()
allToolchains = set()
allArchitectures = set()

class GeneratorData(object):
	"""Contains data for a solution generator"""
	def __init__(self, projectTools, solutionTool):
		self.projectTools = projectTools
		self.solutionTool = solutionTool

allGenerators = {}
allGeneratorTools = set()

solutionGeneratorType = ""

runPerfReport = None

toolchainGroups = {}

solutionPath = ""
solutionArgs = ""

class RunMode(object):
	"""
	'enum' representing the way csbuild has been invoked
	"""
	Normal = 0
	Help = 1
	Version = 2
	GenerateSolution = 3
	GenerateDependencyGraph = 4
	QUALAP = 5

runMode = None

defaultTarget = "release"

parser = None

class Verbosity(object):
	"""
	'enum' representing verbosity
	"""
	Verbose = 0
	Normal = 1
	Quiet = 2
	Mute = 3

#Has to default to Verbose for tests to print Info since they don't take command line params
verbosity = Verbosity.Verbose

showCommands = False

projectMap = {}

projectBuildList = []

commandOutputThread = None

columns = 0
clearBar = ""

startTime = 0

totalBuilds = 0
completedBuilds = 0

buildStartedHooks = set()
buildFinishedHooks = set()

class InMemoryOnlySettings(object):
	"""Mockup class for settings_manager.SettingsManager"""
	def __init__(self):
		self.dict = {}

	def Get(self, key, default=None):
		"""
		Get a value from the dict

		:param key: key
		:type key: str
		:param default: value returned if missing
		:type default: any
		:return: the value for this key, or default
		:rtype: any
		"""
		return self.dict.get(key, default)

	def Save(self, key, value):
		"""
		Save a value to the dict

		:param key: The key
		:type key: str
		:param value: The value
		:type value: any
		"""
		self.dict[key] = value

	def Persist(self):
		"""
		NOP for this class.
		"""
		pass

	def Clear(self):
		"""
		NOP for this class.
		"""
		pass

	def Delete(self, key):
		"""
		Remove a key from the dict if it exists, nop otherwise

		:param key: key to remove
		:type key: str
		"""
		self.dict.pop(key, None)

settings = InMemoryOnlySettings()
