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
.. module:: ps5_assembler
	:synopsis: Implementation of the PS5 assembler tool.

.. moduleauthor:: Zoe Bare
"""

from __future__ import unicode_literals, division, print_function

import os

from .assembler_base import AssemblerBase
from ..common.sony_tool_base import Ps5BaseTool
from ... import log
from ..._utils import response_file, shared_globals

class Ps5Assembler(Ps5BaseTool, AssemblerBase):
	"""
	PS5 assembler tool implementation.
	"""
	supportedPlatforms = { "Windows" }
	supportedArchitectures = { "x64" }
	inputFiles={".s", ".S"}
	outputFiles = { ".o" }

	def __init__(self, projectSettings):
		Ps5BaseTool.__init__(self, projectSettings)
		AssemblerBase.__init__(self, projectSettings)


	####################################################################################################################
	### Methods implemented from base classes
	####################################################################################################################

	def SetupForProject(self, project):
		Ps5BaseTool.SetupForProject(self, project)
		AssemblerBase.SetupForProject(self, project)

	def _getOutputFiles(self, project, inputFile):
		intDirPath = project.GetIntermediateDirectory(inputFile)
		filename = os.path.splitext(os.path.basename(inputFile.filename))[0] + ".o"
		return tuple({ os.path.join(intDirPath, filename) })

	def _getCommand(self, project, inputFile):
		cmdExe = self._getComplierName()
		cmd = self._getCustomArgs() \
			+ self._getPreprocessorArgs() \
			+ self._getIncludeDirectoryArgs() \
			+ self._getOutputFileArgs(project, inputFile) \
			+ self._getInputFileArgs(inputFile)

		inputFileBasename = os.path.basename(inputFile.filename)
		responseFile = response_file.ResponseFile(project, "{}-{}".format(inputFile.uniqueDirectoryId, inputFileBasename), cmd)

		if shared_globals.showCommands:
			log.Command("ResponseFile: {}\n\t{}".format(responseFile.filePath, responseFile.AsString()))

		return [cmdExe, "@{}".format(responseFile.filePath)]


	####################################################################################################################
	### Internal methods
	####################################################################################################################

	def _getComplierName(self):
		binPath = os.path.join(self._ps5SdkPath, "host_tools", "bin")
		exeName = "prospero-clang.exe"

		return os.path.join(binPath, exeName)

	def _getCustomArgs(self):
		return self._asmFlags

	def _getInputFileArgs(self, inputFile):
		return ["-c", inputFile.filename]

	def _getOutputFileArgs(self, project, inputFile):
		outputFiles = self._getOutputFiles(project, inputFile)
		return ["-o", outputFiles[0]]

	def _getPreprocessorArgs(self):
		return ["-D{}".format(d) for d in self._defines]

	def _getIncludeDirectoryArgs(self):
		args = []

		for dirPath in self._includeDirectories:
			args.extend([
				"-I",
				os.path.abspath(dirPath),
			])

		# Add the PS5 system include directories.
		args.extend([
			"-I", os.path.join(self._ps5SdkPath, "target", "include"),
			"-I", os.path.join(self._ps5SdkPath, "target", "include_common"),
		])

		return args
