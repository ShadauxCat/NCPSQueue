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
.. module:: gcc_cpp_compiler
	:synopsis: gcc compiler tool for C++

.. moduleauthor:: Jaedyn K. Draper
"""

from __future__ import unicode_literals, division, print_function

import os

import csbuild

from .cpp_compiler_base import CppCompilerBase
from ..common.tool_traits import HasDebugLevel, HasOptimizationLevel
from ... import log
from ..._utils import response_file, shared_globals

DebugLevel = HasDebugLevel.DebugLevel
OptimizationLevel = HasOptimizationLevel.OptimizationLevel

def _ignore(_):
	pass

class GccCppCompiler(CppCompilerBase):
	"""
	GCC compiler implementation
	"""
	supportedArchitectures = {"x86", "x64", "arm", "arm64"}
	outputFiles = {".o"}


	####################################################################################################################
	### Methods implemented from base classes
	####################################################################################################################

	def _getOutputFiles(self, project, inputFile):
		intDirPath = project.GetIntermediateDirectory(inputFile)
		filename = os.path.splitext(os.path.basename(inputFile.filename))[0] + ".o"
		return tuple({ os.path.join(intDirPath, filename) })

	def _getCommand(self, project, inputFile, isCpp):
		cmdExe = self._getComplierName(project, isCpp)
		cmd = self._getDefaultArgs(project) \
			+ self._getCustomArgs(project, isCpp) \
			+ self._getArchitectureArgs(project) \
			+ self._getOptimizationArgs() \
			+ self._getDebugArgs() \
			+ self._getSystemArgs(project, isCpp) \
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

	def _getComplierName(self, project, isCpp):
		_ignore(project)
		return "g++" if isCpp else "gcc"

	def _getDefaultArgs(self, project):
		args = ["--pass-exit-codes"]
		if project.projectType == csbuild.ProjectType.SharedLibrary:
			args.append("-fPIC")
		return args

	def _getCustomArgs(self, project, isCpp):
		_ignore(project)
		return self._globalFlags + (self._cxxFlags if isCpp else self._cFlags)

	def _getInputFileArgs(self, inputFile):
		return ["-c", inputFile.filename]

	def _getOutputFileArgs(self, project, inputFile):
		outputFiles = self._getOutputFiles(project, inputFile)
		return ["-o", outputFiles[0]]

	def _getPreprocessorArgs(self):
		return ["-D{}".format(d) for d in self._defines] + ["-U{}".format(u) for u in self._undefines]

	def _getIncludeDirectoryArgs(self):
		return ["-I{}".format(d) for d in self._includeDirectories]

	def _getDebugArgs(self):
		if self._debugLevel != DebugLevel.Disabled:
			return ["-g"]
		return []

	def _getOptimizationArgs(self):
		arg = {
			OptimizationLevel.Size: "s",
			OptimizationLevel.Speed: "2",
			OptimizationLevel.Max: "3",
		}
		return ["-O{}".format(arg.get(self._optLevel, "0"))]

	def _getArchitectureArgs(self, project):
		args = {
			"x86": ["-m32"],
			"x64": ["-m64"],
		}.get(project.architectureName, [])
		return args

	def _getSystemArgs(self, project, isCpp):
		_ignore(project)
		_ignore(isCpp)
		return []

	def _getLanguageStandardArgs(self, isSourceCpp):
		standard = self._cxxStandard if isSourceCpp else self._ccStandard
		arg = "-std={}".format(standard) if standard else None
		return [arg]
