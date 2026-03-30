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
.. module:: psvita_linker
	:synopsis: Implementation of the PSVita linker tool.

.. moduleauthor:: Zoe Bare
"""

from __future__ import unicode_literals, division, print_function

import csbuild
import os

from .linker_base import LinkerBase

from ..common import FindLibraries
from ..common.sony_tool_base import PsVitaBaseTool

from ... import log
from ..._utils import response_file, shared_globals

class PsVitaLinker(PsVitaBaseTool, LinkerBase):
	"""
	PSVita linker tool implementation.
	"""
	supportedArchitectures = { "arm" }

	inputGroups = { ".o" }
	outputFiles = { ".self", ".a", ".suprx" }
	crossProjectDependencies = { ".a", ".suprx" }

	def __init__(self, projectSettings):
		PsVitaBaseTool.__init__(self, projectSettings)
		LinkerBase.__init__(self, projectSettings)


	####################################################################################################################
	### Methods implemented from base classes
	####################################################################################################################

	def SetupForProject(self, project):
		PsVitaBaseTool.SetupForProject(self, project)
		LinkerBase.SetupForProject(self, project)

	def _getOutputFiles(self, project):
		projectOutputName = project.outputName

		# PSVita requires that libraries being with the "lib" prefix.
		if project.projectType == csbuild.ProjectType.SharedLibrary and not projectOutputName.startswith("lib"):
			projectOutputName = "lib{}".format(projectOutputName)

		outputFilename = "{}{}".format(projectOutputName, self._getOutputExtension(project.projectType))
		outputFullPath = os.path.join(project.outputDir, outputFilename)
		outputFiles = [outputFullPath]

		# For shared libraries, the linker will automatically generate a stub library that can be linked against.
		# Note the stub will only be generated if something in the project is being exported.  But, since dynamic
		# loading at runtime isn't possible, such a project would be pointless, so we can assume the developer will
		# always export something.
		if project.projectType == csbuild.ProjectType.SharedLibrary:
			outputFiles.extend([
				os.path.join(project.outputDir, "{}_stub.a".format(projectOutputName)),
			])

		return tuple(outputFiles)

	def _getCommand(self, project, inputFiles):
		if project.projectType == csbuild.ProjectType.StaticLibrary:
			useResponseFile = False
			cmdExe = self._getArchiverName()
			cmd = ["rcs"] \
				+ self._getCustomLinkerArgs() \
				+ self._getOutputFileArgs(project) \
				+ self._getInputFileArgs(inputFiles)
		else:
			useResponseFile = True
			cmdExe = self._getLinkerName()
			cmd = self._getDefaultArgs(project) \
				+ self._getCustomLinkerArgs() \
				+ self._getOutputFileArgs(project) \
				+ self._getInputFileArgs(inputFiles) \
				+ self._getLibraryPathArgs() \
				+ self._getStartGroupArgs() \
				+ self._getLibraryArgs() \
				+ self._getEndGroupArgs()

		if useResponseFile:
			responseFile = response_file.ResponseFile(project, "linker-{}".format(project.outputName), cmd)

			if shared_globals.showCommands:
				log.Command("ResponseFile: {}\n\t{}".format(responseFile.filePath, responseFile.AsString()))

			cmd = [cmdExe, "@{}".format(responseFile.filePath)]

		else:
			cmd = [cmdExe] + cmd

		return cmd

	def _findLibraries(self, project, libs):
		targetLibPath = os.path.join(self._psVitaSdkPath, "target", "lib")
		allLibraryDirectories = list(self._libraryDirectories) + [targetLibPath]

		return FindLibraries(libs, allLibraryDirectories, [".suprx", ".a"])

	def _getOutputExtension(self, projectType):
		outputExt = {
			csbuild.ProjectType.Application: ".self",
			csbuild.ProjectType.SharedLibrary: ".suprx",
			csbuild.ProjectType.StaticLibrary: ".a",
		}.get(projectType, None)

		return outputExt


	####################################################################################################################
	### Internal methods
	####################################################################################################################

	def _getLinkerName(self):
		binPath = os.path.join(self._psVitaSdkPath, "host_tools", "build", "bin")
		exeName = "psp2ld.exe"

		return os.path.join(binPath, exeName)

	def _getArchiverName(self):
		binPath = os.path.join(self._psVitaSdkPath, "host_tools", "build", "bin")
		exeName = "psp2snarl.exe"

		return os.path.join(binPath, exeName)

	def _getDefaultArgs(self, project):
		args = []
		if project.projectType == csbuild.ProjectType.SharedLibrary:
			args.extend([
				"-oformat=prx",
				"-prx-stub-output-dir={}".format(project.outputDir),
			])
		return args

	def _getCustomLinkerArgs(self):
		return self._linkerFlags

	def _getOutputFileArgs(self, project):
		outFile = "{}".format(self._getOutputFiles(project)[0])
		if project.projectType == csbuild.ProjectType.StaticLibrary:
			return [outFile]
		return ["-o", outFile]

	def _getInputFileArgs(self, inputFiles):
		return [f.filename for f in inputFiles]

	def _getLibraryPathArgs(self):
		args = ["-L{}".format(os.path.dirname(lib)) for lib in self._actualLibraryLocations.values()]
		return args

	def _getLibraryArgs(self):
		libNames = [os.path.basename(lib) for lib in self._actualLibraryLocations.values()]
		args = []

		for lib in libNames:
			libName, libExt = os.path.splitext(lib)
			if libName.startswith("lib"):
				libName = libName[3:]

			if libExt == ".suprx":
				libName = "{}_stub".format(libName)

			args.append("-l{}".format(libName))

		return args

	def _getStartGroupArgs(self):
		return ["--start-group"]

	def _getEndGroupArgs(self):
		return ["--end-group"]
