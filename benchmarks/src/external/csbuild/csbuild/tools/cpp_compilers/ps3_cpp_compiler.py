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
.. module:: ps3_cpp_compiler
	:synopsis: Implementation of the PS3 C/C++ compiler tool.

.. moduleauthor:: Zoe Bare
"""

from __future__ import unicode_literals, division, print_function

import os

from .cpp_compiler_base import CppCompilerBase

from ..common.sony_tool_base import Ps3BaseTool, Ps3ProjectType, Ps3ToolsetType
from ..common.tool_traits import HasDebugLevel, HasOptimizationLevel
from ... import log
from ..._utils import response_file, shared_globals

DebugLevel = HasDebugLevel.DebugLevel
OptimizationLevel = HasOptimizationLevel.OptimizationLevel

class Ps3CppCompiler(Ps3BaseTool, CppCompilerBase):
	"""
	PS3 C/C++ compiler tool implementation.
	"""
	supportedPlatforms = { "Windows" }
	supportedArchitectures = { "cell" }
	outputFiles = { ".o" }

	def __init__(self, projectSettings):
		Ps3BaseTool.__init__(self, projectSettings)
		CppCompilerBase.__init__(self, projectSettings)

		self._compilerExeName = None


	####################################################################################################################
	### Methods implemented from base classes
	####################################################################################################################

	def SetupForProject(self, project):
		Ps3BaseTool.SetupForProject(self, project)
		CppCompilerBase.SetupForProject(self, project)

		self._compilerExeName = {
			Ps3ToolsetType.PpuSnc: ("ps3ppusnc.exe", "ps3ppusnc.exe"),
			Ps3ToolsetType.PpuGcc: ("ppu-lv2-gcc.exe", "ppu-lv2-g++.exe"),
			Ps3ToolsetType.Spu:    ("spu-lv2-gcc.exe", "spu-lv2-g++.exe"),
		}.get(self._ps3BuildInfo.toolsetType, None)
		assert self._compilerExeName, "Invalid PS3 toolset type: {}".format(self._ps3BuildInfo.toolsetType)

	def _getOutputFiles(self, project, inputFile):
		intDirPath = project.GetIntermediateDirectory(inputFile)
		filename = os.path.splitext(os.path.basename(inputFile.filename))[0] + ".o"
		return tuple({ os.path.join(intDirPath, filename) })

	def _getCommand(self, project, inputFile, isCpp):
		cmdExe = self._getComplierName(isCpp)
		cmd = self._getCustomArgs(isCpp) \
			+ self._getOptimizationArgs() \
			+ self._getDebugArgs() \
			+ self._getLanguageStandardArgs(isCpp) \
			+ self._getPreprocessorArgs(project) \
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

	def _getComplierName(self, isCpp):
		return os.path.join(self._ps3SystemBinPath, self._compilerExeName[1] if isCpp else self._compilerExeName[0])

	def _getCustomArgs(self, isCpp):
		return self._globalFlags + self._cxxFlags if isCpp else self._cFlags

	def _getInputFileArgs(self, inputFile):
		return ["-c", inputFile.filename]

	def _getOutputFileArgs(self, project, inputFile):
		outputFiles = self._getOutputFiles(project, inputFile)
		return ["-o", outputFiles[0]]

	def _getPreprocessorArgs(self, project):
		args = ["-D__PS3__"]

		if self._ps3BuildInfo.toolsetType != Ps3ToolsetType.Spu:
			if self._ps3BuildInfo.toolsetType == Ps3ToolsetType.PpuGcc:
				args.append("-D__GCC__")

			if project.projectType in (Ps3ProjectType.PpuSncSharedLibrary, Ps3ProjectType.PpuGccSharedLibrary):
				args.extend([
					"-DCSB_PS3_PPU_PRX_LIBNAME=cellPrx_{}".format(project.name),
					"-DCSB_PS3_PPU_PRX_STUBNAME=cellPrx_{}_stub".format(project.name),
				])

		args.extend(["-D{}".format(d) for d in self._defines])
		args.extend(["-U{}".format(u) for u in self._undefines])

		return args

	def _getIncludeDirectoryArgs(self):
		args = ["-I{}".format(path) for path in sorted(self._includeDirectories) + self._ps3SystemIncludePaths]

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
		if self._ps3BuildInfo.toolsetType == Ps3ToolsetType.PpuSnc:
			argName = "Xstd"
			standard = self._cxxStandard if isSourceCpp else self._ccStandard

			if isSourceCpp:
				# The SNC compiler only supports the c++03 and c++11 standard, but they have non-standard names.
				assert self._cxxStandard in { "c++03", "c++11" }, "Unsupported C++ standard: {}".format(self._cxxStandard)
				standard = "cpp{}".format(self._cxxStandard[3:])

		else:
			if isSourceCpp:
				# The GCC compilers do not support setting the c++ standard
				return []

			argName = "std"
			standard = self._ccStandard

		arg = "-{}={}".format(argName, standard) if standard else None
		return [arg]
