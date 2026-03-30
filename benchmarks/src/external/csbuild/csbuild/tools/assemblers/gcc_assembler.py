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
.. module:: gcc_assembler
	:synopsis: GCC assember tool

.. moduleauthor:: Zoe Bare
"""

from __future__ import unicode_literals, division, print_function

import os
import csbuild

from .assembler_base import AssemblerBase

class GccAssembler(AssemblerBase):
	"""
	GCC assembler implementation
	"""
	supportedArchitectures = {"x86", "x64", "arm", "arm64"}
	inputFiles={".s", ".S"}
	outputFiles = {".o"}

	def __init__(self, projectSettings):
		AssemblerBase.__init__(self, projectSettings)


	####################################################################################################################
	### Methods implemented from base classes
	####################################################################################################################

	def _getOutputFiles(self, project, inputFile):
		intDirPath = project.GetIntermediateDirectory(inputFile)
		filename = os.path.splitext(os.path.basename(inputFile.filename))[0] + ".o"
		return tuple({ os.path.join(intDirPath, filename) })

	def _getCommand(self, project, inputFile):
		cmd = [self._getComplierName()] \
			+ self._getInputFileArgs(inputFile) \
			+ self._getDefaultArgs(project) \
			+ self._getCustomArgs() \
			+ self._getOutputFileArgs(project, inputFile) \
			+ self._getPreprocessorArgs() \
			+ self._getIncludeDirectoryArgs() \
			+ self._getArchitectureArgs(project)

		return [arg for arg in cmd if arg]


	####################################################################################################################
	### Internal methods
	####################################################################################################################

	def _getComplierName(self):
		return "gcc"

	def _getDefaultArgs(self, project):
		args = ["--pass-exit-codes"]
		if project.projectType == csbuild.ProjectType.SharedLibrary:
			args.append("-fPIC")
		return args

	def _getCustomArgs(self):
		return self._asmFlags

	def _getInputFileArgs(self, inputFile):
		return ["-c", "{}".format(inputFile.filename)]

	def _getOutputFileArgs(self, project, inputFile):
		outputFiles = self._getOutputFiles(project, inputFile)
		return ["-o", "{}".format(outputFiles[0])]

	def _getPreprocessorArgs(self):
		return ["-D{}".format(d) for d in self._defines]

	def _getIncludeDirectoryArgs(self):
		return ["-I{}".format(d) for d in self._includeDirectories]

	def _getArchitectureArgs(self, project):
		args = {
			"x86": ["-m32"],
			"x64": ["-m64"],
		}.get(project.architectureName, [])
		return args
