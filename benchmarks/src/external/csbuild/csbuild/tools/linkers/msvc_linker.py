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
.. module:: msvc_linker
	:synopsis: msvc linker tool for C++, d, asm, etc

.. moduleauthor:: Zoe Bare
"""

from __future__ import unicode_literals, division, print_function

import os
import csbuild

from .linker_base import LinkerBase
from ..common import FindLibraries
from ..common.msvc_tool_base import MsvcToolBase
from ..common.tool_traits import HasDebugLevel, HasIncrementalLink
from ... import log
from ..._utils import ordered_set, response_file, shared_globals

DebugLevel = HasDebugLevel.DebugLevel

def _ignore(_):
	pass

class MsvcLinker(MsvcToolBase, LinkerBase, HasIncrementalLink):
	"""
	MSVC linker tool implementation for c++ and asm.
	"""
	supportedPlatforms = { "Windows" }
	supportedArchitectures = { "x86", "x64", "arm64" }
	inputGroups = { ".obj", ".o" }
	outputFiles = { ".exe", ".lib", ".dll" }
	crossProjectDependencies = { ".lib" }

	####################################################################################################################
	### Methods implemented from base classes
	####################################################################################################################

	def __init__(self, projectSettings):
		MsvcToolBase.__init__(self, projectSettings)
		LinkerBase.__init__(self, projectSettings)
		HasIncrementalLink.__init__(self, projectSettings)

		self._libExePath = None
		self._linkExePath = None

	def _getEnv(self, project):
		return self.vcvarsall.env

	def _getOutputFiles(self, project):
		outputPath = os.path.join(project.outputDir, project.outputName)
		outputFiles = {
			csbuild.ProjectType.Application: ["{}.exe".format(outputPath)],
			csbuild.ProjectType.StaticLibrary: ["{}.lib".format(outputPath)],
			csbuild.ProjectType.SharedLibrary: ["{}.dll".format(outputPath)],
		}[project.projectType]

		# Output files when not building a static library.
		if project.projectType != csbuild.ProjectType.StaticLibrary:
			outputFiles.append("{}.ilk".format(outputPath))

			# Add the PDB file if debugging is enabled.
			if self._debugLevel != DebugLevel.Disabled:
				outputFiles.append("{}.pdb".format(outputPath))

		# Can't predict these things, linker will make them if it decides to.
		possibleFiles = ["{}.exp".format(outputPath), "{}.lib".format(outputPath)]
		outputFiles.extend([filename for filename in possibleFiles if os.access(filename, os.F_OK)])

		return tuple(set(outputFiles))

	def _getCommand(self, project, inputFiles):
		if project.projectType == csbuild.ProjectType.StaticLibrary:
			cmdExe = self._libExePath
			cmd = self._getDefaultArgs(project) \
				+ self._getOutputFileArgs(project) \
				+ self._getInputFileArgs(inputFiles)

		else:
			cmdExe = self._linkExePath
			cmd = self._getDefaultArgs(project) \
				+ self._getIncrementalLinkArgs(project) \
				+ self._getUwpArgs(project) \
				+ self._getCustomArgs() \
				+ self._getOutputFileArgs(project) \
				+ self._getInputFileArgs(inputFiles) \
				+ self._getLibraryArgs(project)

		# De-duplicate any repeated items in the command list.
		cmd = list(ordered_set.OrderedSet(cmd))

		responseFile = response_file.ResponseFile(project, "linker-{}".format(project.outputName), cmd)

		if shared_globals.showCommands:
			log.Command("ResponseFile: {}\n\t{}".format(responseFile.filePath, responseFile.AsString()))

		return [cmdExe, "@{}".format(responseFile.filePath)]

	def _findLibraries(self, project, libs):
		allLibraryDirectories = list(self._libraryDirectories) + self.vcvarsall.libPaths

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
		MsvcToolBase.SetupForProject(self, project)
		LinkerBase.SetupForProject(self, project)
		HasIncrementalLink.SetupForProject(self, project)

		self._libExePath = os.path.join(self.vcvarsall.binPath, "lib.exe")
		self._linkExePath = os.path.join(self.vcvarsall.binPath, "link.exe")

	####################################################################################################################
	### Internal methods
	####################################################################################################################

	def _getDefaultArgs(self, project):
		args = [
			"/ERRORREPORT:NONE",
			"/NOLOGO",
			"/MACHINE:{}".format(project.architectureName.upper()),
		]

		# Add the subsystem argument if specified.
		if self.msvcSubsystem:
			subsystemArg = ["/SUBSYSTEM:{}".format(self.msvcSubsystem)]

			# The subsystem version is optional.
			if self.msvcSubsystemVersion:
				subsystemArg.append(",{}.{}".format(self.msvcSubsystemVersion[0], self.msvcSubsystemVersion[1]))

			args.append("".join(subsystemArg))

		# Arguments for any project that is not a static library.
		if project.projectType != csbuild.ProjectType.StaticLibrary:
			args.extend([
				"/NXCOMPAT",
				"/DYNAMICBASE",
			])
			if self._debugLevel != DebugLevel.Disabled:
				args.append("/DEBUG")
			if project.projectType == csbuild.ProjectType.SharedLibrary:
				args.append("/DLL")
		return args

	def _getIncrementalLinkArgs(self, project):
		args = []

		if project.projectType != csbuild.ProjectType.StaticLibrary and self._incrementalLink:
			args.extend([
				"/INCREMENTAL",
				"/ILK:{}.ilk".format(os.path.join(project.outputDir, project.outputName)),
			])

		return args

	def _getUwpArgs(self, project):
		_ignore(project)
		return []

	def _getCustomArgs(self):
		# Eliminate duplicate entries without wrecking the argument order.
		args = list(ordered_set.OrderedSet(self._linkerFlags))
		return args

	def _getLibraryArgs(self, project):
		# Static libraries don't require the default libraries to be linked, so only add them when building an application or shared library.
		args = [] if project.projectType == csbuild.ProjectType.StaticLibrary else [
			"kernel32.lib",
			"user32.lib",
			"gdi32.lib",
			"winspool.lib",
			"comdlg32.lib",
			"advapi32.lib",
			"shell32.lib",
			"ole32.lib",
			"oleaut32.lib",
			"uuid.lib",
			"odbc32.lib",
			"odbccp32.lib",
		]
		args.extend(list(self._actualLibraryLocations.values()))
		return args

	def _getOutputFileArgs(self, project):
		outExt = {
			csbuild.ProjectType.SharedLibrary: ".dll",
			csbuild.ProjectType.StaticLibrary: ".lib",
		}
		outputPath = os.path.join(project.outputDir, project.outputName)
		args = ["/OUT:{}{}".format(outputPath, outExt.get(project.projectType, ".exe"))]

		if project.projectType == csbuild.ProjectType.SharedLibrary:
			args.append("/IMPLIB:{}.lib".format(outputPath))

		if project.projectType != csbuild.ProjectType.StaticLibrary and self._debugLevel != DebugLevel.Disabled:
			args.append("/PDB:{}.pdb".format(outputPath))

		return args

	def _getInputFileArgs(self, inputFiles):
		return [f.filename for f in inputFiles]
