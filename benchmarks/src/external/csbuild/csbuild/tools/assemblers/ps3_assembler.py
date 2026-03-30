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
.. module:: ps3_assembler
	:synopsis: Implementation of the PS3 assembler tool.

.. moduleauthor:: Zoe Bare
"""

from __future__ import unicode_literals, division, print_function

import os

from .assembler_base import AssemblerBase

from ..common.sony_tool_base import Ps3BaseTool, Ps3ProjectType, Ps3ToolsetType
from ..common.tool_traits import HasDebugLevel, HasOptimizationLevel
from ... import log
from ..._utils import response_file, shared_globals

DebugLevel = HasDebugLevel.DebugLevel
OptimizationLevel = HasOptimizationLevel.OptimizationLevel

class Ps3Assembler(Ps3BaseTool, AssemblerBase):
	"""
	PS3 assembler tool implementation.
	"""
	supportedPlatforms = { "Windows" }
	supportedArchitectures = { "cell" }
	inputFiles={".s", ".S"}
	outputFiles = { ".o" }

	def __init__(self, projectSettings):
		Ps3BaseTool.__init__(self, projectSettings)
		AssemblerBase.__init__(self, projectSettings)

		self._compilerExeName = None


	####################################################################################################################
	### Methods implemented from base classes
	####################################################################################################################

	def SetupForProject(self, project):
		Ps3BaseTool.SetupForProject(self, project)
		AssemblerBase.SetupForProject(self, project)

		self._compilerExeName = {
			Ps3ToolsetType.PpuSnc: "ps3ppusnc.exe",
			Ps3ToolsetType.PpuGcc: "ppu-lv2-gcc.exe",
			Ps3ToolsetType.Spu:    "spu-lv2-gcc.exe",
		}.get(self._ps3BuildInfo.toolsetType, None)
		assert self._compilerExeName, "Invalid PS3 toolset type: {}".format(self._ps3BuildInfo.toolsetType)

	def _getOutputFiles(self, project, inputFile):
		intDirPath = project.GetIntermediateDirectory(inputFile)
		filename = os.path.splitext(os.path.basename(inputFile.filename))[0] + ".o"
		return tuple({ os.path.join(intDirPath, filename) })

	def _getCommand(self, project, inputFile):
		cmdExe = self._getComplierName()
		cmd = self._getCustomArgs() \
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

	def _getComplierName(self):
		return os.path.join(self._ps3SystemBinPath, self._compilerExeName)

	def _getCustomArgs(self):
		return self._asmFlags

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
		args = ["-I{}".format(path) for path in self._includeDirectories]

		return args
