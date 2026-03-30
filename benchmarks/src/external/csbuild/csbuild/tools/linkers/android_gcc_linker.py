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
.. module:: android_gcc_linker
	:synopsis: Android gcc linker tool.

.. moduleauthor:: Zoe Bare
"""

from __future__ import unicode_literals, division, print_function

import os

import csbuild

from .gcc_linker import GccLinker
from ..common.android_tool_base import AndroidToolBase

class AndroidGccLinker(GccLinker, AndroidToolBase):
	"""
	Android gcc linker implementation
	"""
	supportedArchitectures = AndroidToolBase.supportedArchitectures

	outputFiles = {".a", ".so"}


	####################################################################################################################
	### Methods implemented from base classes
	####################################################################################################################

	def SetupForProject(self, project):
		"""
		Run project setup, if any, before building the project, but after all dependencies have been resolved.

		:param project: project being set up
		:type project: csbuild._build.project.Project
		"""
		GccLinker.SetupForProject(self, project)
		AndroidToolBase.SetupForProject(self, project)

	def _getOutputExtension(self, projectType):
		# Android doesn't have a native application type.  Applications are linked as shared libraries.
		outputExt = {
			csbuild.ProjectType.Application: ".so",
			csbuild.ProjectType.SharedLibrary: ".so",
			csbuild.ProjectType.StaticLibrary: ".a",
		}.get(projectType, None)

		return outputExt

	def _getLdName(self):
		return self._androidInfo.ldPath

	def _getBinaryLinkerName(self):
		return self._androidInfo.gppPath

	def _getArchiverName(self):
		return self._androidInfo.arPath

	def _getDefaultArgs(self, project):
		baseArgs = [] if project.projectType == csbuild.ProjectType.StaticLibrary else ["-shared", "-fPIC"]
		defaultAndroidArgs = self._getDefaultLinkerArgs()
		return baseArgs + defaultAndroidArgs

	def _getStdLibArgs(self):
		# Android handles this manually through library arguments.
		return []

	def _getLibraryPathArgs(self, project):
		args = []
		paths = set()

		# Add the STL lib path first since it's technically a system path.
		if self._androidInfo.stlLibPath:
			args.append("-L{}".format(self._androidInfo.stlLibPath))

		# Extract all of the library paths.
		for lib in self._actualLibraryLocations.values():
			paths.add(os.path.dirname(lib))

		for libPath in sorted(paths):
			args.append("-L\"{}\"".format(libPath))

		return args

	def _getRpathArgs(self, project):
		return []

	def _getLibraryArgs(self):
		args = ["-lc", "-lm", "-lgcc", "-llog", "-landroid"]

		if self._androidInfo.stlLibName:
			ext = "_static.a" if self._staticRuntime else "_shared.so"
			args.append("-l:{}".format("{}{}".format(self._androidInfo.stlLibName, ext)))

		# Add only the basename for each library.
		for lib in self._actualLibraryLocations.values():
			args.append("-l:{}".format(os.path.basename(lib)))

		return args

	def _getArchitectureArgs(self, project):
		buildArchName = self._getBuildArchName(project.architectureName)
		return ["-march={}".format(buildArchName)] if buildArchName else []

	def _getSystemArgs(self, project):
		return [
			"--sysroot",
			self._androidInfo.sysRootPath,
			"-Wl,--rpath-link={}".format(self._androidInfo.systemLibPath),
		]

	def _getLibrarySearchDirectories(self):
		return [self._androidInfo.systemLibPath] + list(self._libraryDirectories)
