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
.. module:: msvc_uwp_linker
	:synopsis: MSVC linker tool for C++, d, asm, etc, to build apps for the Universal Windows Platform

.. moduleauthor:: Zoe Bare
"""

from __future__ import unicode_literals, division, print_function

import os
import csbuild

from .msvc_linker import MsvcLinker

class MsvcUwpLinker(MsvcLinker):
	"""
	MSVC linker tool implementation for building apps for the Universal Windows Platform
	"""
	outputFiles = {".exe", ".lib", ".dll", ".winmd"}

	####################################################################################################################
	### Methods implemented from base classes
	####################################################################################################################

	def __init__(self, projectSettings):
		MsvcLinker.__init__(self, projectSettings)

		# Enable UWP builds so the base tool setups up the toolchain backend properly.
		self._enableUwp = True

	def _getOutputFiles(self, project):
		outputFiles = MsvcLinker._getOutputFiles(self, project)

		if project.projectType != csbuild.ProjectType.StaticLibrary:
			outputFiles = set(outputFiles)
			outputFiles.add("{}.winmd".format(os.path.join(project.outputDir, project.outputName)))
			outputFiles = tuple(outputFiles)

		return outputFiles

	def _getUwpArgs(self, project):
		args = [
			"/APPCONTAINER",
		]
		return args

	def _getLibraryArgs(self, project):
		# Static libraries don't require the default libraries to be linked, so only add them when building an application or shared library.
		args = [] if project.projectType == csbuild.ProjectType.StaticLibrary else [
			"WindowsApp.lib",
		]
		args.extend(list(self._actualLibraryLocations.values()))
		return args

	def _getOutputFileArgs(self, project):
		args = MsvcLinker._getOutputFileArgs(self, project)

		if project.projectType != csbuild.ProjectType.StaticLibrary:
			args.extend([
				"/WINMD",
				"/WINMDFILE:{}.winmd".format(os.path.join(project.outputDir, project.outputName))
			])

		return args
