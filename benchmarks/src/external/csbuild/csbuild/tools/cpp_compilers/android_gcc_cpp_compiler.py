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
.. module:: android_gcc_cpp_compiler
	:synopsis: Android GCC compiler tool for C++.

.. moduleauthor:: Zoe Bare
"""

from __future__ import unicode_literals, division, print_function

import os

import csbuild

from .gcc_cpp_compiler import GccCppCompiler
from ..common.android_tool_base import AndroidToolBase
from ..._build.input_file import  InputFile

class AndroidGccCppCompiler(GccCppCompiler, AndroidToolBase):
	"""
	Android GCC c++ compiler implementation
	"""
	supportedArchitectures = AndroidToolBase.supportedArchitectures

	def __init__(self, projectSettings):
		GccCppCompiler.__init__(self, projectSettings)
		AndroidToolBase.__init__(self, projectSettings)


	####################################################################################################################
	### Methods implemented from base classes
	####################################################################################################################

	def SetupForProject(self, project):
		"""
		Run project setup, if any, before building the project, but after all dependencies have been resolved.

		:param project: project being set up
		:type project: csbuild._build.project.Project
		"""
		GccCppCompiler.SetupForProject(self, project)
		AndroidToolBase.SetupForProject(self, project)

		# Applications should automatically add the default native app glue source file, but only when told to do so.
		if project.projectType == csbuild.ProjectType.Application and self._androidNativeAppGlue:
			nativeAppGlueSourcePath = os.path.join(self._androidInfo.nativeAppGluPath, "android_native_app_glue.c")
			assert os.access(nativeAppGlueSourcePath, os.F_OK), "Android native app glue source file not found at path: {}".format(nativeAppGlueSourcePath)

			# Add it directly to the project's list of input files.
			project.inputFiles[".c"].add(InputFile(nativeAppGlueSourcePath))

	def _getComplierName(self, project, isCpp):
		assert self._androidInfo.gccPath, "No Android gcc executable found for architecture: {}".format(project.architectureName)
		assert self._androidInfo.gppPath, "No Android g++ executable found for architecture: {}".format(project.architectureName)
		return self._androidInfo.gppPath if isCpp else self._androidInfo.gccPath

	def _getDefaultArgs(self, project):
		baseArgs = GccCppCompiler._getDefaultArgs(self, project)
		defaultAndroidArgs = self._getDefaultCompilerArgs()
		return baseArgs + defaultAndroidArgs + [
			"-funswitch-loops",
			"-finline-limit=100",
		]

	def _getPreprocessorArgs(self):
		args = [
			"-D__ANDROID_API__={}".format(self._androidTargetSdkVersion),
			"-DANDROID_NDK",
			"-DANDROID",
			"-D__ANDROID__",
		]
		return args + GccCppCompiler._getPreprocessorArgs(self)

	def _getArchitectureArgs(self, project):
		buildArchName = self._getBuildArchName(project.architectureName)
		return ["-march={}".format(buildArchName)] if buildArchName else []

	def _getSystemArgs(self, project, isCpp):
		args = []

		if isCpp:
			# Add each include path for the selected version of STL.
			for path in self._androidInfo.stlIncludePaths:
				args.extend([
					"-isystem",
					path,
				])

		# Add the sysroot include paths.
		for path in self._androidInfo.systemIncludePaths:
			args.extend([
				"-isystem",
				path,
			])

		if self._androidNativeAppGlue:
			args.extend([
				"-isystem",
				self._androidInfo.nativeAppGluPath,
			])

		return args
