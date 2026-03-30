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
.. module:: mac_os_clang_linker
	:synopsis: Clang linker tool for the macOS platform.

.. moduleauthor:: Zoe Bare
"""

from __future__ import unicode_literals, division, print_function

import csbuild
import os

from .clang_linker import ClangLinker

from ..common import FindLibraries
from ..common.apple_tool_base import MacOsToolBase

class MacOsClangLinker(MacOsToolBase, ClangLinker):
	"""
	Clang compiler implementation
	"""
	supportedPlatforms = { "Darwin" }
	outputFiles = { "", ".a", ".dylib" }
	crossProjectDependencies = { ".a", ".dylib" }

	def __init__(self, projectSettings):
		MacOsToolBase.__init__(self, projectSettings)
		ClangLinker.__init__(self, projectSettings)


	####################################################################################################################
	### Methods implemented from base classes
	####################################################################################################################

	def SetupForProject(self, project):
		MacOsToolBase.SetupForProject(self, project)
		ClangLinker.SetupForProject(self, project)

	def _findLibraries(self, project, libs):
		sysLibDirs = [
			"/usr/local/lib",
			"/usr/lib",
		]
		allLibraryDirectories = list(self._libraryDirectories) + sysLibDirs

		return FindLibraries(libs, allLibraryDirectories, [".dylib", ".so", ".a"])

	def _getDefaultArgs(self, project):
		args = ClangLinker._getDefaultArgs(self, project)

		# Get the special library build flag.
		libraryBuildArg = {
			csbuild.ProjectType.SharedLibrary: "-dynamiclib",
		}.get(project.projectType, "")
		args.append(libraryBuildArg)

		# Set the system and SDK properties.
		args.extend([
			"-mmacosx-version-min={}".format(self._macOsVersionMin),
			"-isysroot",
			self._appleToolInfo.defaultMacOsSdkPath,
		])

		return args

	def _rpathStartsWithVariable(self, rpath):
		return rpath.startswith("@")

	def _getRpathOriginVariable(self):
		# TODO: Eventually need a way to switch the default origin variable between @executable_path and @loader_path
		return "@executable_path"

	def _getRpathArgs(self, project):
		args = []

		if project.projectType == csbuild.ProjectType.Application:
			args.extend([
				"-Xlinker", "-rpath",
				"-Xlinker", self._getRpathOriginVariable(),
			])

			rpaths = set()
			outDir = os.path.dirname(self._getOutputFiles(project)[0])

			if project.autoResolveRpaths:
				# Add RPATH arguments for each linked library path.
				for lib in self._actualLibraryLocations.values():
					libDir = os.path.dirname(lib)
					rpath = self._resolveRpath(outDir, libDir)

					if rpath:
						rpaths.add(rpath)

			# Add RPATH arguments for each path specified in the makefile.
			for path in self._rpathDirectories:
				path = self._resolveRpath(outDir, path)

				if path:
					rpaths.add(path)

			# Add each RPATH to the argument list.
			for path in sorted(rpaths):
				args.extend([
					"-Xlinker", "-rpath",
					"-Xlinker", path,
				])

		elif project.projectType == csbuild.ProjectType.SharedLibrary:
			outFile = os.path.basename(self._getOutputFiles(project)[0])
			args.extend([
				"-install_name",
				"@rpath/{}".format(outFile),
			])

		return args

	def _getLibraryArgs(self):
		libArgs = list(self._actualLibraryLocations.values())
		frameworkArgs = ["-F{}".format(path) for path in self._frameworkDirectories]
		for framework in self._frameworks:
			frameworkArgs.extend(["-framework", framework])

		return frameworkArgs + libArgs

	def _getStartGroupArgs(self):
		return []

	def _getEndGroupArgs(self):
		return []

	def _useResponseFileWithArchiver(self):
		return False

	def _getOutputExtension(self, projectType):
		outputExt = {
			csbuild.ProjectType.SharedLibrary: ".dylib",
		}.get(projectType, None)

		if outputExt is None:
			outputExt = ClangLinker._getOutputExtension(self, projectType)

		return outputExt
