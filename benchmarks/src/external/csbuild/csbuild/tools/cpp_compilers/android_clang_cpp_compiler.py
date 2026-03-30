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
.. module:: android_clang_cpp_compiler
	:synopsis: Android clang compiler tool for C++.

.. moduleauthor:: Zoe Bare
"""

from __future__ import unicode_literals, division, print_function

import csbuild
import os

from .android_gcc_cpp_compiler import AndroidGccCppCompiler

class AndroidClangCppCompiler(AndroidGccCppCompiler):
	"""
	Android clang compiler implementation
	"""
	def __init__(self, projectSettings):
		AndroidGccCppCompiler.__init__(self, projectSettings)

	####################################################################################################################
	### Methods implemented from base classes
	####################################################################################################################

	def _getComplierName(self, project, isCpp):
		assert os.access(self._androidInfo.clangPath, os.F_OK), "No Android clang executable found for architecture: {}".format(project.architectureName)
		assert os.access(self._androidInfo.clangppPath, os.F_OK), "No Android clang++ executable found for architecture: {}".format(project.architectureName)
		return self._androidInfo.clangppPath if isCpp else self._androidInfo.clangPath

	def _getDefaultArgs(self, project):
		baseArgs = []
		defaultAndroidArgs = self._getDefaultCompilerArgs()
		if project.projectType == csbuild.ProjectType.SharedLibrary:
			baseArgs.append("-fPIC")
		return baseArgs + defaultAndroidArgs + [
			"-gcc-toolchain",
			self._androidInfo.gccToolchainRootPath,
		]

	def _getArchitectureArgs(self, project):
		targetName = self._getTargetTripleName(project.architectureName)
		return ["-target", targetName]
