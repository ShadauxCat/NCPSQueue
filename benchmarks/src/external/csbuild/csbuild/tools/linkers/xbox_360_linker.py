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
.. module:: xbox_360_linker
	:synopsis: Xbox 360 linker tool for C/C++ and assembly.

.. moduleauthor:: Zoe Bare
"""

from __future__ import unicode_literals, division, print_function

import os
import csbuild

from .linker_base import LinkerBase
from ..common import FindLibraries
from ..common.xbox_360_tool_base import Xbox360BaseTool
from ..common.tool_traits import HasDebugLevel
from ... import log
from ..._utils import response_file, shared_globals

DebugLevel = HasDebugLevel.DebugLevel

class Xbox360Linker(Xbox360BaseTool, LinkerBase):
	"""
	Xbox 360 linker tool implementation for c/c++ and asm.
	"""
	supportedPlatforms = {"Windows"}
	supportedArchitectures = {"xcpu"}
	inputGroups = {".obj", ".o"}
	outputFiles = {".exe", ".lib", ".dll"}
	crossProjectDependencies = {".lib"}


	####################################################################################################################
	### Methods implemented from base classes
	####################################################################################################################

	def __init__(self, projectSettings):
		Xbox360BaseTool.__init__(self, projectSettings)
		LinkerBase.__init__(self, projectSettings)

	def _getOutputFiles(self, project):
		outputPath = os.path.join(project.outputDir, project.outputName)
		outputFiles = {
			csbuild.ProjectType.Application: ["{}.exe".format(outputPath)],
			csbuild.ProjectType.StaticLibrary: ["{}.lib".format(outputPath)],
			csbuild.ProjectType.SharedLibrary: ["{}.dll".format(outputPath)],
		}[project.projectType]

		# Output files when not building a static library.
		if project.projectType != csbuild.ProjectType.StaticLibrary:
			outputFiles.extend([
				"{}.ilk".format(outputPath),
				"{}.pe".format(outputPath),
				"{}.xdb".format(outputPath),
			])

			# Add the PDB file if debugging is enabled.
			if self._debugLevel != DebugLevel.Disabled:
				outputFiles.append("{}.pdb".format(outputPath))

		# Can't predict these things, linker will make them if it decides to.
		possibleFiles = ["{}.exp".format(outputPath), "{}.lib".format(outputPath)]
		outputFiles.extend([filename for filename in possibleFiles if os.access(filename, os.F_OK)])

		return tuple(set(outputFiles))

	def _getCommand(self, project, inputFiles):
		if project.projectType == csbuild.ProjectType.StaticLibrary:
			cmdExe = os.path.join(self._xbox360BinPath, "lib.exe")
			cmd = self._getDefaultArgs(project) \
				+ self._getOutputFileArgs(project) \
				+ self._getInputFileArgs(inputFiles)

		else:
			cmdExe = os.path.join(self._xbox360BinPath, "link.exe")
			cmd = self._getDefaultArgs(project) \
				+ self._getCustomArgs() \
				+ self._getOutputFileArgs(project) \
				+ self._getInputFileArgs(inputFiles) \
				+ self._getLibraryArgs(project)

		responseFile = response_file.ResponseFile(project, "linker-{}".format(project.outputName), cmd)

		if shared_globals.showCommands:
			log.Command("ResponseFile: {}\n\t{}".format(responseFile.filePath, responseFile.AsString()))

		return [cmdExe, "@{}".format(responseFile.filePath)]

	def _findLibraries(self, project, libs):
		allLibraryDirectories = list(self._libraryDirectories)

		return FindLibraries(libs, allLibraryDirectories, [".lib"])

	def _getOutputExtension(self, projectType):
		# These are extensions of the files that can be output from the linker or librarian.
		# The library extensions should represent the file types that can actually linked against.
		ext = {
			csbuild.ProjectType.Application: ".exe",
			csbuild.ProjectType.SharedLibrary: ".lib",
			csbuild.ProjectType.StaticLibrary: ".lib",
		}
		return ext.get(projectType, None)

	def SetupForProject(self, project):
		Xbox360BaseTool.SetupForProject(self, project)
		LinkerBase.SetupForProject(self, project)

		# Xbox 360 does not support linking directly against dynamic libraries so we
		# need to remove any project dependencies of that type from the library list.
		for dependProject in project.dependencies:
			if dependProject.projectType == csbuild.ProjectType.SharedLibrary:
				del self._actualLibraryLocations[dependProject.outputName]


	####################################################################################################################
	### Internal methods
	####################################################################################################################

	def _getDefaultArgs(self, project):
		args = [
			"/ERRORREPORT:NONE",
			"/NOLOGO",
			"/MACHINE:PPCBE",
			"/SUBSYSTEM:XBOX"
		]

		# Arguments for any project that is not a static library.
		if project.projectType != csbuild.ProjectType.StaticLibrary:
			if self._debugLevel != DebugLevel.Disabled:
				args.append("/DEBUG")
			if project.projectType == csbuild.ProjectType.SharedLibrary:
				args.append("/DLL")
		return args

	def _getCustomArgs(self):
		return self._linkerFlags

	def _getLibraryArgs(self, project):
		# Static libraries don't require the default libraries to be linked, so only add them when building an application or shared library.
		args = [] if project.projectType == csbuild.ProjectType.StaticLibrary else [
			"/LIBPATH:{}".format(self._xbox360LibPath),
			"xboxkrnl.lib",
			"xbdm.lib",
		]
		args.extend(list(self._actualLibraryLocations.values()))
		return args

	def _getOutputFileArgs(self, project):
		outExt = {
			csbuild.ProjectType.SharedLibrary: ".dll",
			csbuild.ProjectType.StaticLibrary: ".lib",
		}.get(project.projectType, ".exe")

		outputPath = os.path.join(project.outputDir, project.outputName)
		args = ["/OUT:{}{}".format(outputPath, outExt)]

		if project.projectType == csbuild.ProjectType.SharedLibrary:
			args.append("/IMPLIB:{}.lib".format(outputPath))

		if project.projectType != csbuild.ProjectType.StaticLibrary:
			#args.append("/PGD:{}.pgd".format(outputPath))

			if self._debugLevel != DebugLevel.Disabled:
				args.append("/PDB:{}.pdb".format(outputPath))

		return args

	def _getInputFileArgs(self, inputFiles):
		return [f.filename for f in inputFiles]
