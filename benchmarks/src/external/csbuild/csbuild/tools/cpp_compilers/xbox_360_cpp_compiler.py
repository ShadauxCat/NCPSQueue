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
.. module:: xbox_360_cpp_compiler
	:synopsis: Xbox 360 compiler tool for C++

.. moduleauthor:: Zoe Bare
"""

from __future__ import unicode_literals, division, print_function

import os

from .cpp_compiler_base import CppCompilerBase
from ..common.xbox_360_tool_base import Xbox360BaseTool
from ..common.tool_traits import HasDebugLevel, HasOptimizationLevel
from ... import log
from ..._utils import response_file, shared_globals

DebugLevel = HasDebugLevel.DebugLevel
OptimizationLevel = HasOptimizationLevel.OptimizationLevel

def _ignore(_):
	pass

class Xbox360CppCompiler(Xbox360BaseTool, CppCompilerBase):
	"""
	Xbox 360 compiler tool implementation.
	"""
	supportedPlatforms = { "Windows" }
	supportedArchitectures = { "xcpu" }
	outputFiles = { ".obj" }

	def __init__(self, projectSettings):
		Xbox360BaseTool.__init__(self, projectSettings)
		CppCompilerBase.__init__(self, projectSettings)

		self._exePath = None


	####################################################################################################################
	### Methods implemented from base classes
	####################################################################################################################

	def _getOutputFiles(self, project, inputFile):
		outputPath = os.path.join(project.GetIntermediateDirectory(inputFile), os.path.splitext(os.path.basename(inputFile.filename))[0])
		outputFiles = ["{}.obj".format(outputPath)]

		if self._debugLevel in [DebugLevel.ExternalSymbols, DebugLevel.ExternalSymbolsPlus]:
			outputFiles.append("{}.pdb".format(outputPath))

			if self._debugLevel == DebugLevel.ExternalSymbolsPlus:
				outputFiles.append("{}.idb".format(outputPath))

		return tuple(outputFiles)

	def _getCommand(self, project, inputFile, isCpp):
		cmd = self._getDefaultArgs() \
			+ self._getCustomArgs(project, isCpp) \
			+ self._getPreprocessorArgs() \
			+ self._getDebugArgs() \
			+ self._getOptimizationArgs() \
			+ self._getIncludeDirectoryArgs() \
			+ self._getOutputFileArgs(project, inputFile) \
			+ [inputFile.filename]

		inputFileBasename = os.path.basename(inputFile.filename)
		responseFile = response_file.ResponseFile(project, "{}-{}".format(inputFile.uniqueDirectoryId, inputFileBasename), cmd)

		if shared_globals.showCommands:
			log.Command("ResponseFile: {}\n\t{}".format(responseFile.filePath, responseFile.AsString()))

		return [self._exePath, "@{}".format(responseFile.filePath)]

	def SetupForProject(self, project):
		Xbox360BaseTool.SetupForProject(self, project)
		CppCompilerBase.SetupForProject(self, project)

		self._exePath = os.path.join(self._xbox360BinPath, "cl.exe")


	####################################################################################################################
	### Internal methods
	####################################################################################################################

	def _getDefaultArgs(self):
		args = ["/nologo", "/c", "/Oi", "/GS"]
		if self._optLevel == OptimizationLevel.Disabled:
			args.append("/RTC1")
		return args

	def _getCustomArgs(self, project, isCpp):
		_ignore(project)
		return self._globalFlags + self._cxxFlags if isCpp else self._cFlags

	def _getDebugArgs(self):
		arg = {
			DebugLevel.EmbeddedSymbols: "/Z7",
			DebugLevel.ExternalSymbols: "/Zi",
			DebugLevel.ExternalSymbolsPlus: "/Zi",
		}
		return [arg.get(self._debugLevel, "")]

	def _getOptimizationArgs(self):
		arg = {
			OptimizationLevel.Size: ["/O1", "/Os"],
			OptimizationLevel.Speed: ["/O2", "/Ot"],
			OptimizationLevel.Max: ["/Ox", "/Ot", "/Oz"],
		}
		return arg.get(self._optLevel, ["/Od"])

	def _getPreprocessorArgs(self):
		defineArgs = ["/D_XBOX", "/DXBOX"] + ["/D{}".format(d) for d in self._defines]
		undefineArgs = ["/U{}".format(u) for u in self._undefines]
		return defineArgs + undefineArgs

	def _getIncludeDirectoryArgs(self):
		args = ["/I{}".format(self._xbox360IncludePath)]
		args.extend(["/I{}".format(directory) for directory in self._includeDirectories])
		return args

	def _getOutputFileArgs(self, project, inputFile):
		outputFiles = self._getOutputFiles(project, inputFile)
		args = ["/Fo{}".format(filePath) for filePath in outputFiles if os.path.splitext(filePath)[1] in [".obj"]]

		if self._debugLevel in [DebugLevel.ExternalSymbols, DebugLevel.ExternalSymbolsPlus]:
			args.extend(["/Fd{}".format(filePath) for filePath in outputFiles if os.path.splitext(filePath)[1] in [".pdb"]])

		return args
