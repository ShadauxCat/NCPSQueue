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
.. module:: ps4_cpp_compiler
	:synopsis: Implementation of the PS4 C/C++ compiler tool.

.. moduleauthor:: Zoe Bare
"""

from __future__ import unicode_literals, division, print_function

import csbuild
import os

from .gcc_cpp_compiler import GccCppCompiler

from ..common.sony_tool_base import Ps4BaseTool

class Ps4CppCompiler(Ps4BaseTool, GccCppCompiler):
	"""
	PS4 C/C++ compiler tool implementation.
	"""
	supportedPlatforms = { "Windows" }
	supportedArchitectures = { "x64" }
	outputFiles = { ".o" }

	def __init__(self, projectSettings):
		Ps4BaseTool.__init__(self, projectSettings)
		GccCppCompiler.__init__(self, projectSettings)


	####################################################################################################################
	### Methods implemented from base classes
	####################################################################################################################

	def _getComplierName(self, project, isCpp):
		binPath = os.path.join(self._ps4SdkPath, "host_tools", "bin")
		exeName = "orbis-clang++.exe" if isCpp else "orbis-clang.exe"

		return os.path.join(binPath, exeName)

	def _getDefaultArgs(self, project):
		args = ["-fPIC"] if project.projectType == csbuild.ProjectType.SharedLibrary else []
		return args

	def _getIncludeDirectoryArgs(self):
		args = GccCppCompiler._getIncludeDirectoryArgs(self)

		# Add the PS4 system include directories.
		args.extend([
			"-I{}".format(os.path.join(self._ps4SdkPath, "target", "include")),
			"-I{}".format(os.path.join(self._ps4SdkPath, "target", "include_common")),
		])

		return args

	def SetupForProject(self, project):
		Ps4BaseTool.SetupForProject(self, project)
		GccCppCompiler.SetupForProject(self, project)
