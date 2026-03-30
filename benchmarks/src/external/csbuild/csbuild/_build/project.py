# Copyright (C) 2013 Jaedyn K. Draper
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
.. module:: project
	:synopsis: A project that's been finalized for building.
		Unlike ProjectPlan, Project is a completely finalized class specialized on a single toolchain, and is ready to build
"""

from __future__ import unicode_literals, division, print_function

import os
import collections
import threading

import csbuild
from .. import log, perf_timer
from .._utils import ordered_set, shared_globals, StrType, BytesType, PlatformString, PlatformUnicode
from .._utils.decorators import TypeChecked
from .._utils.string_abc import String
from .._build import input_file
from ..toolchain.toolchain import Toolchain

class UserData(object):
	"""
	Wrapper around a dict that allows its contents to be accessed as if they were class properties instead
	:param dataDict: dict to wrap
	:type dataDict: dict
	"""
	def __init__(self, dataDict):
		self.dataDict = dataDict

	def __getattr__(self, item):
		return object.__getattribute__(self, "dataDict")[item]

	def __contains__(self, item):
		return item in self.dataDict

class Project(object):
	"""
	A finalized, concrete project

	:param name: The project's name. Must be unique.
	:type name: str

	:param workingDirectory: The location on disk containing the project's files, which should be examined to collect source files.
		If autoDiscoverSourceFiles is False, this parameter is ignored.
	:type workingDirectory: str or bytes

	:param depends: List of names of other prjects this one depends on.
	:type depends: ordered_set.OrderedSet[str or bytes]

	:param priority: Priority in the build queue, used to cause this project to get built first in its dependency ordering. Higher number means higher priority.
	:type priority: int

	:param ignoreDependencyOrdering: Treat priority as a global value and use priority to raise this project above, or lower it below, the dependency order
	:type ignoreDependencyOrdering: bool

	:param autoDiscoverSourceFiles: If False, do not automatically search the working directory for files, but instead only build files that are manually added.
	:type autoDiscoverSourceFiles: bool

	:param autoResolveRpaths: Automatically add RPATH arguments for linked shared libraries.
	:type autoResolveRpaths: bool

	:param projectSettings: Finalized settings from the project plan
	:type projectSettings: dict

	:param toolchainName: Toolchain name
	:type toolchainName: str or bytes

	:param archName: Architecture name
	:type archName: str or bytes

	:param targetName: Target name
	:type targetName: str or bytes

	:param scriptDir: Directory of the script where this project is defined
	:type scriptDir: str or bytes
	"""

	_lock = threading.Lock()

	def __init__(self, name, workingDirectory, depends, priority, ignoreDependencyOrdering, autoDiscoverSourceFiles, autoResolveRpaths, projectSettings, toolchainName, archName, targetName, scriptDir):
		with perf_timer.PerfTimer("Project init"):

			self.name = name
			self.workingDirectory = workingDirectory
			self.dependencyNames = depends
			self.dependencies = []
			self.priority = priority
			self.ignoreDependencyOrdering = ignoreDependencyOrdering
			self.autoDiscoverSourceFiles = autoDiscoverSourceFiles
			self.autoResolveRpaths = autoResolveRpaths

			self.toolchainName = toolchainName
			self.architectureName = archName
			self.targetName = targetName

			self.scriptDir = scriptDir

			#: type: dict[str, set[str]]
			self.builtThisRun = {}

			log.Build("Preparing build tasks for {}", self)

			#: type: set[Tool]
			self.tools = projectSettings["tools"] - projectSettings.get("disabledTools", set())
			self.checkers = projectSettings.get("checkers", {})

			if shared_globals.runMode == shared_globals.RunMode.GenerateSolution:
				tools = []
				generatorTools = shared_globals.allGenerators[shared_globals.solutionGeneratorType].projectTools
				for tool in self.tools:
					if tool in generatorTools:
						tools.append(tool)
				self.tools = tools

			self.userData = UserData(projectSettings.get("_userData", {}))

			def _convertSet(toConvert):
				ret = toConvert.__class__()
				for item in toConvert:
					ret.add(_convertItem(item))
				return ret

			def _convertDict(toConvert):
				for key, val in toConvert.items():
					toConvert[key] = _convertItem(val)
				return toConvert

			def _convertList(toConvert):
				for i, item in enumerate(toConvert):
					toConvert[i] = _convertItem(item)
				return toConvert

			def _convertItem(toConvert):
				if isinstance(toConvert, list):
					return _convertList(toConvert)
				if isinstance(toConvert, (dict, collections.OrderedDict)):
					return _convertDict(toConvert)
				if isinstance(toConvert, (set, ordered_set.OrderedSet)):
					return _convertSet(toConvert)
				if isinstance(toConvert, (StrType, BytesType)):
					return self.FormatMacro(toConvert)
				return toConvert

			with perf_timer.PerfTimer("Macro formatting"):
				# We set self.settings here because _convertItem calls FormatMacro and FormatMacro uses self.settings
				self.settings = projectSettings
				self.settings = _convertItem(projectSettings)

			self.toolchain = Toolchain(self.settings, *self.tools, checkers=self.checkers)

			self.projectType = self.settings.get("projectType", csbuild.ProjectType.Application)

			#: type: set[str]
			self.excludeFiles = self.settings.get("excludeFiles", set())
			#: type: set[str]
			self.excludeDirs = self.settings.get("excludeDirs", set())
			#: type: set[str]
			self.sourceFiles = self.settings.get("sourceFiles", set())
			#: type: set[str]
			self.sourceDirs = self.settings.get("sourceDirs", set())

			#: type: str
			self.intermediateDir = os.path.join(
				self.scriptDir,
				self.settings.get(
					"intermediateDir",
					os.path.join(
						"intermediate",
						self.toolchainName,
						self.architectureName,
						self.targetName,
						self.name
					)
				)
			)

			#: type: str
			self.outputDir = os.path.join(
				self.scriptDir,
				self.settings.get(
					"outputDir",
					os.path.join(
						"out",
						self.toolchainName,
						self.architectureName,
						self.targetName,
					)
				)
			)

			#: type: str
			self.csbuildDir = os.path.join(self.scriptDir, ".csbuild")

			if not os.access(self.csbuildDir, os.F_OK):
				os.makedirs(self.csbuildDir)

			self.lastRunArtifacts = shared_globals.settings.Get(repr(self)+".artifacts", collections.OrderedDict())

			self.artifacts = collections.OrderedDict()

			self.outputName = self.settings.get("outputName", self.name)

			# Stub projects will not be built, so they don't need intermediate or output directories.
			if self.projectType != csbuild.ProjectType.Stub:
				if not os.access(self.intermediateDir, os.F_OK):
					os.makedirs(self.intermediateDir)
				if not os.access(self.outputDir, os.F_OK):
					os.makedirs(self.outputDir)

			#: type: dict[str, set[csbuild._build.input_file.InputFile]]
			self.inputFiles = {}

			self.RediscoverFiles()

	def __repr__(self):
		return "{} ({}-{}-{})".format(self.name, self.toolchainName, self.architectureName, self.targetName)

	def FormatMacro(self, toConvert):
		"""
		Format a string containing macros with data from the project.
		i.e., in a project with toolchainName = msvc, FormatMacro("{toolchainName}.foo") would return "msvc.foo"
		This will also convert any values of type unicode (in python2) or bytes (in python3) to the platform-appropriate
		str type.

		:param toConvert: The macroized string to convert
		:type toConvert: str or bytes

		:return: The converted string
		:rtype: str
		"""
		# TODO: This could be optimized:
		# Make a proxy class that gets items from the list of valid items
		# and convert them as we come across them, using memoization to avoid redundant
		# conversions. If we do that, we could do each string in one pass.
		if "{" in toConvert:
			prev = ""
			while toConvert != prev:
				log.Info("Formatting {}", toConvert)
				prev = toConvert
				toConvert = toConvert.format(
					name=self.name,
					workingDirectory=self.workingDirectory,
					dependencyNames=self.dependencyNames,
					priority=self.priority,
					ignoreDependencyOrdering=self.ignoreDependencyOrdering,
					autoDiscoverSourceFiles=self.autoDiscoverSourceFiles,
					settings=self.settings,
					toolchainName=self.toolchainName,
					architectureName=self.architectureName,
					targetName=self.targetName,
					userData=self.userData,
					**self.settings
				)
				log.Info("  => {}", toConvert)
		return PlatformString(toConvert)

	def ResolveDependencies(self):
		"""
		Called after shared_globals.projectMap is filled out, this will populate the dependencies map.
		"""
		for name in self.dependencyNames:
			project = shared_globals.projectMap \
				.get(self.toolchainName, {}) \
				.get(self.architectureName, {}) \
				.get(self.targetName, {}) \
				.get(name, None)

			if project:
				self.dependencies.append(project)
			else:
				log.Error("Dependency does not exist for configuration ({}/{}/{}) for project \"{}\": {}", self.toolchainName, self.architectureName, self.targetName, self.name, name)

	@TypeChecked(inputs=(input_file.InputFile, list, ordered_set.OrderedSet, type(None)), artifact=String)
	def AddArtifact(self, inputs, artifact):
		"""
		Add an artifact - i.e., a file created by the build

		:param inputs: Inputs being used to generate this artifact
		:type inputs: input_file.InputFile or list[input_file.InputFile] or ordered_set.OrderedSet[input_file.InputFile]

		:param artifact: Absolute path to the file
		:type artifact: str
		"""
		if shared_globals.runMode == shared_globals.RunMode.GenerateSolution:
			if artifact not in self.artifacts.get(inputs, {}):
				self.artifacts.setdefault(inputs, ordered_set.OrderedSet()).add(artifact)
			return

		if inputs is not None:
			if isinstance(inputs, input_file.InputFile):
				inputs = [inputs]
			inputs = tuple(sorted(i.filename for i in inputs))
		if artifact not in self.artifacts.get(inputs, {}):
			self.artifacts.setdefault(inputs, ordered_set.OrderedSet()).add(artifact)
			shared_globals.settings.Save(repr(self)+".artifacts", self.artifacts)

	@TypeChecked(inputs=(input_file.InputFile, list, ordered_set.OrderedSet))
	def GetLastResult(self, inputs):
		"""
		Get the list of files that were created from a set of inputs in the last run.

		:param inputs: The input or inputs being used for this compile unit.
		:type inputs: input_file.InputFile or list[input_file.InputFile] or ordered_set.OrderedSet[input_file.InputFile]

		:return: The list of outputs from the last run
		:rtype: ordered_set.OrderedSet[str]
		"""
		if isinstance(inputs, input_file.InputFile):
			inputs = [inputs]
		inputs = tuple(sorted(i.filename for i in inputs))
		return self.lastRunArtifacts.get(inputs, None)

	def ClearArtifacts(self):
		"""Remove the artifacts for this project from the settings"""
		shared_globals.settings.Delete(repr(self)+".artifacts")

	@TypeChecked(inputFile=input_file.InputFile, _return=StrType)
	def GetIntermediateDirectory(self, inputFile):
		"""
		Get the unique, intermediate directory path for an input file.  The directory will be created if it does not exist.

		:param inputFile: The input file to use for constructing the directory.
		:type inputFile: input_file.InputFile

		:return: Unique intermediate directory path.
		:rtype: str
		"""
		directory = os.path.join(self.intermediateDir, self.name, inputFile.uniqueDirectoryId)

		#TODO: Investigate a lock-free solution to creating this directory.
		if not os.access(directory, os.F_OK):
			# Lock in case multiple threads get here at the same time.
			#pylint: disable=not-context-manager
			with Project._lock:
				# If the directory still does not exist, create it.
				if not os.access(directory, os.F_OK):
					os.makedirs(directory)
		return PlatformUnicode(directory)

	def RediscoverFiles(self):
		"""
		(Re)-Run source file discovery.
		If autoDiscoverSourceFiles is enabled, this will recursively search the working directory and all extra directories
		to find source files.
		Manually specified source files are then added to this list.
		Note that even if autoDiscoverSourceFiles is disabled, this must be called again in order to update the source
		file list after a preBuildStep.
		"""
		with perf_timer.PerfTimer("File discovery"):
			log.Info("Discovering files for {}...", self)
			self.inputFiles = {}

			searchDirectories = ordered_set.OrderedSet(self.sourceDirs)

			if self.autoDiscoverSourceFiles:
				searchDirectories |= ordered_set.OrderedSet([self.workingDirectory])

			extensionList = self.toolchain.GetSearchExtensions()

			excludeFiles = [
				os.path.abspath(os.path.join(self.workingDirectory, filename))
				for filename in self.excludeFiles
			]

			with perf_timer.PerfTimer("Walking working dir"):
				for sourceDir in searchDirectories:
					log.Build("Collecting files from {}", sourceDir)
					for root, _, filenames in os.walk(sourceDir):
						if not filenames:
							continue
						absroot = os.path.abspath(root)
						if absroot in self.excludeDirs:
							if absroot != self.csbuildDir:
								log.Info("Skipping dir {}", root)
							continue
						if ".csbuild" in root \
								or root.startswith(self.intermediateDir) \
								or (root.startswith(self.outputDir) and self.outputDir != self.workingDirectory):
							continue
						if absroot == self.csbuildDir or absroot.startswith(self.csbuildDir):
							continue
						found = False
						for testDir in self.excludeDirs:
							if absroot.startswith(testDir):
								found = True
								continue
						if found:
							if not absroot.startswith(self.csbuildDir):
								log.Info("Skipping directory {}", root)
							continue
						log.Info("Looking in directory {}", root)
						with perf_timer.PerfTimer("Collecting files"):
							for extension in extensionList:
								log.Info("Checking for {}", extension)
								self.inputFiles.setdefault(extension, ordered_set.OrderedSet()).update(
									[
										input_file.InputFile(
											os.path.join(absroot, filename)
										) for filename in filenames if os.path.splitext(filename)[1] == extension
										and os.path.join(absroot, filename) not in self.lastRunArtifacts
										and os.path.join(absroot, filename) not in excludeFiles
									]
								)

			with perf_timer.PerfTimer("Processing source files"):
				for filename in self.sourceFiles:
					extension = os.path.splitext(filename)[1]
					self.inputFiles.setdefault(extension, ordered_set.OrderedSet()).add(input_file.InputFile(filename))

			log.Info("Discovered {}", self.inputFiles)
