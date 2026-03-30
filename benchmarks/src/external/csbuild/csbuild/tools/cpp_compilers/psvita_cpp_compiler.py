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
.. module:: psvita_cpp_compiler
	:synopsis: Implementation of the PSVita C/C++ compiler tool.

.. moduleauthor:: Zoe Bare
"""

from __future__ import unicode_literals, division, print_function

import os

from .cpp_compiler_base import CppCompilerBase

from ..common.sony_tool_base import PsVitaBaseTool
from ..common.tool_traits import HasDebugLevel, HasOptimizationLevel
from ... import log
from ..._utils import response_file, shared_globals

DebugLevel = HasDebugLevel.DebugLevel
OptimizationLevel = HasOptimizationLevel.OptimizationLevel

class PsVitaCppCompiler(PsVitaBaseTool, CppCompilerBase):
	"""
	PSVita C/C++ compiler tool implementation.
	"""
	supportedPlatforms = { "Windows" }
	supportedArchitectures = { "arm" }
	outputFiles = { ".o" }

	def __init__(self, projectSettings):
		PsVitaBaseTool.__init__(self, projectSettings)
		CppCompilerBase.__init__(self, projectSettings)


	####################################################################################################################
	### Methods implemented from base classes
	####################################################################################################################

	def SetupForProject(self, project):
		PsVitaBaseTool.SetupForProject(self, project)
		CppCompilerBase.SetupForProject(self, project)

	def _getOutputFiles(self, project, inputFile):
		intDirPath = project.GetIntermediateDirectory(inputFile)
		filename = os.path.splitext(os.path.basename(inputFile.filename))[0] + ".o"
		return tuple({ os.path.join(intDirPath, filename) })

	def _getCommand(self, project, inputFile, isCpp):
		cmdExe = self._getComplierName()
		cmd = self._getCustomArgs(isCpp) \
			+ self._getOptimizationArgs() \
			+ self._getDebugArgs() \
			+ self._getLanguageStandardArgs(isCpp) \
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
		binPath = os.path.join(self._psVitaSdkPath, "host_tools", "build", "bin")
		exeName = "psp2snc.exe"

		return os.path.join(binPath, exeName)

	def _getCustomArgs(self, isCpp):
		return self._globalFlags + self._cxxFlags if isCpp else self._cFlags

	def _getInputFileArgs(self, inputFile):
		return ["-c", inputFile.filename]

	def _getOutputFileArgs(self, project, inputFile):
		outputFiles = self._getOutputFiles(project, inputFile)
		return ["-o", outputFiles[0]]

	def _getPreprocessorArgs(self):
		args = []
		args.extend(["-D{}".format(d) for d in self._defines])
		args.extend(["-U{}".format(u) for u in self._undefines])
		return args

	def _getIncludeDirectoryArgs(self):
		args = []

		for dirPath in self._includeDirectories:
			args.extend([
				"-I{}".format(os.path.abspath(dirPath)),
			])

		# Add the PSVita system include directories.
		args.extend([
			"-I{}".format(os.path.join(self._psVitaSdkPath, "target", "include")),
			"-I{}".format(os.path.join(self._psVitaSdkPath, "target", "include_common")),
		])

		return args

	def _getDebugArgs(self):
		if self._debugLevel != DebugLevel.Disabled:
			return ["-g"]
		return []

	def _getOptimizationArgs(self):
		arg = {
			OptimizationLevel.Size: "s",
			OptimizationLevel.Speed: "d",
			OptimizationLevel.Max: "3",
		}
		return ["-O{}".format(arg.get(self._optLevel, "0"))]

	def _getLanguageStandardArgs(self, isSourceCpp):
		standard = self._cxxStandard if isSourceCpp else self._ccStandard

		if isSourceCpp:
			# The SNC compiler only supports the c++03 and c++11 standard, but they have non-standard names.
			assert self._cxxStandard in { "c++03", "c++11" }, "Unsupported C++ standard: {}".format(self._cxxStandard)
			standard = "cpp{}".format(self._cxxStandard[3:])

		arg = "-Xstd={}".format(standard) if standard else None
		return [arg]
