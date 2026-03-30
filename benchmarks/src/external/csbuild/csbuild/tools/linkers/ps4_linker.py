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
.. module:: ps4_linker
	:synopsis: Implementation of the PS4 linker tool.

.. moduleauthor:: Zoe Bare
"""

from __future__ import unicode_literals, division, print_function

import csbuild
import os

from .gcc_linker import GccLinker

from ..common import FindLibraries
from ..common.sony_tool_base import Ps4BaseTool

def _ignore(_):
	pass

class Ps4Linker(Ps4BaseTool, GccLinker):
	"""
	PS4 linker tool implementation
	"""
	supportedPlatforms = { "Windows" }
	supportedArchitectures = { "x64" }

	outputFiles = { ".elf", ".a", ".prx" }
	crossProjectDependencies = { ".a", ".prx" }

	def __init__(self, projectSettings):
		Ps4BaseTool.__init__(self, projectSettings)
		GccLinker.__init__(self, projectSettings)

	####################################################################################################################
	### Methods implemented from base classes
	####################################################################################################################

	def SetupForProject(self, project):
		Ps4BaseTool.SetupForProject(self, project)
		GccLinker.SetupForProject(self, project)

	def _getOutputFiles(self, project):
		outputFilename = "{}{}".format(project.outputName, self._getOutputExtension(project.projectType))
		outputFullPath = os.path.join(project.outputDir, outputFilename)
		outputFiles = [outputFullPath]

		# For shared libraries, the linker will automatically generate stub libraries that can be linked against.
		# Note the stubs will only be generated if something in the project is being exported.  But, since dynamic
		# loading at runtime isn't possible, such a project would be pointless, so we can assume the developer will
		# always export something.
		if project.projectType == csbuild.ProjectType.SharedLibrary:
			outputFiles.extend([
				os.path.join(project.outputDir, "{}_stub.a".format(project.outputName)),
				os.path.join(project.outputDir, "{}_stub_weak.a".format(project.outputName)),
			])

		return tuple(outputFiles)

	def _findLibraries(self, project, libs):
		targetLibPath = os.path.join(self._ps4SdkPath, "target", "lib")
		allLibraryDirectories = list(self._libraryDirectories) + [targetLibPath]

		return FindLibraries(libs, allLibraryDirectories, [".prx", ".a"])

	def _getOutputExtension(self, projectType):
		outputExt = {
			csbuild.ProjectType.Application: ".elf",
			csbuild.ProjectType.SharedLibrary: ".prx",
			csbuild.ProjectType.StaticLibrary: ".a",
		}.get(projectType, None)

		return outputExt

	def _getBinaryLinkerName(self):
		return os.path.join(self._ps4SdkPath, "host_tools", "bin", "orbis-clang++.exe")

	def _getArchiverName(self):
		return os.path.join(self._ps4SdkPath, "host_tools", "bin", "orbis-ar.exe")

	def _getDefaultArgs(self, project):
		args = [
			"-fPIC",
			"-Wl,-oformat=prx",
			"-Wl,-prx-stub-output-dir={}".format(project.outputDir)
		] if project.projectType == csbuild.ProjectType.SharedLibrary \
			else []
		return args

	def _getLibraryPathArgs(self, project):
		_ignore(project)
		return []

	def _getRpathArgs(self, project):
		return []

	def _getLibraryArgs(self):
		args = []

		for libPath in self._actualLibraryLocations.values():
			libNameExt = os.path.splitext(libPath)

			# PRX libraries can't be linked directly. We have to link against their static stub libraries
			# that are generated when they are built.
			if libNameExt[1] in (".prx", ".sprx"):
				libPath = os.path.join(os.path.dirname(libPath), "{}_stub.a".format(os.path.basename(libNameExt[0])))

			args.append(libPath)

		return args

	def _getStartGroupArgs(self):
		return ["-Wl,--start-group"]
