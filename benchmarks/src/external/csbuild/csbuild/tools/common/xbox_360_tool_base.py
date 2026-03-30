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
.. module:: xbox_360_tool_base
	:synopsis: Base tools for the Xbox 360 tool implementations.

.. moduleauthor:: Zoe Bare
"""

from __future__ import unicode_literals, division, print_function

import csbuild
import os

from abc import ABCMeta

from csbuild import commands, log

from .tool_traits import HasOptimizationLevel

from ..._utils.decorators import MetaClass
from ...toolchain import Tool

OptimizationLevel = HasOptimizationLevel.OptimizationLevel


@MetaClass(ABCMeta)
class Xbox360BaseTool(Tool):
	"""
	Parent class for all Xbox 360 tools.

	:param projectSettings: A read-only scoped view into the project settings dictionary
	:type projectSettings: toolchain.ReadOnlySettingsView
	"""
	def __init__(self, projectSettings):
		Tool.__init__(self, projectSettings)

		self._xbox360SdkPath = projectSettings.get("xbox360SdkPath", None)

		self._xbox360BinPath = None # type: str or None
		self._xbox360LibPath = None # type: str or None
		self._xbox360IncludePath = None # type: str or None


	####################################################################################################################
	### Static makefile methods
	####################################################################################################################

	@staticmethod
	def SetXbox360SdkPath(path):
		"""
		Set the path to the Xbox 360 SDK.

		:param path: Path to the Xbox 360 SDK.
		:type path: str
		"""
		csbuild.currentPlan.SetValue("xbox360SdkPath", os.path.abspath(path) if path else None)


	####################################################################################################################
	### Methods implemented from base classes
	####################################################################################################################

	def SetupForProject(self, project):
		# If the SDK path wasn't set, attempt to find it from the environment.
		if not self._xbox360SdkPath:
			self._xbox360SdkPath = os.getenv("XEDK", None)

		assert self._xbox360SdkPath, "No Xbox 360 SDK path has been set"
		assert os.access(self._xbox360SdkPath, os.F_OK), "Xbox 360 SDK path does not exist: {}".format(self._ps3SdkPath)

		self._xbox360SdkPath = os.path.abspath(self._xbox360SdkPath)

		self._xbox360BinPath = os.path.join(self._xbox360SdkPath, "bin", "win32")
		self._xbox360LibPath = os.path.join(self._xbox360SdkPath, "lib", "xbox")
		self._xbox360IncludePath = os.path.join(self._xbox360SdkPath, "include", "xbox")


class Xbox360ImageXexTool(Xbox360BaseTool):
	"""
	Tool that converts a compiled executable for Xbox 360 into a XEX image capable of running on hardware.

	:param projectSettings: A read-only scoped view into the project settings dictionary
	:type projectSettings: toolchain.ReadOnlySettingsView
	"""
	supportedPlatforms = { "Windows" }
	supportedArchitectures = { "xcpu" }
	inputFiles = { ".exe", ".dll" }
	outputFiles = { ".xex" }

	################################################################################
	### Initialization
	################################################################################

	def __init__(self, projectSettings):
		Xbox360BaseTool.__init__(self, projectSettings)

		self._exePath = None

		self._xexConfigPath = projectSettings.get("xbox360XexConfigPath", None)
		self._xexImageFlags = projectSettings.get("xbox360imageFlags", [])


	####################################################################################################################
	### Static makefile methods
	####################################################################################################################

	@staticmethod
	def SetXbox360ImageConfigFile(path):
		"""
		Set the path to the Xbox 360 XEX config file.
		The properties in this file will override any flags that are set manually

		:param path: Path to the XEX config file.
		:type path: str
		"""
		csbuild.currentPlan.SetValue("xbox360XexConfigPath", os.path.abspath(path) if path else None)

	@staticmethod
	def SetXbox360ImageFlags(*flags):
		"""
		Add flags to pass to the XEX image conversion program.

		:param flags: List of XEX image flags.
		:type flags: str
		"""
		csbuild.currentPlan.ExtendList("xbox360imageFlags", flags)


	################################################################################
	### Internal methods
	################################################################################

	def _getOutputFiles(self, project, inputFile):
		inputFileExtSplit = os.path.splitext(os.path.basename(inputFile.filename))
		outputFilePath = os.path.join(
			project.outputDir,
			"{}.xex".format(inputFileExtSplit[0])
		)
		return tuple({ outputFilePath })

	def _getCommand(self, project, inputFile):
		cmdExe = self._getExeName()
		cmd = [cmdExe] \
			+ self._getDefaultArgs() \
			+ self._getInputArgs(inputFile) \
			+ self._getOutputArgs(project, inputFile) \
			+ self._getTitleConfigArgs() \
			+ self._getMiscArgs()

		return cmd

	def _getExeName(self):
		return os.path.join(self._xbox360BinPath, "imagexex.exe")

	def _getDefaultArgs(self):
		return ["/nologo"]

	def _getInputArgs(self, inputFile):
		arg = "/IN:{}".format(inputFile.filename)
		return [arg]

	def _getOutputArgs(self, project, inputFile):
		arg = "/OUT:{}".format(self._getOutputFiles(project, inputFile)[0])
		return [arg]

	def _getTitleConfigArgs(self):
		args = []

		if self._xexConfigPath:
			args.append("/CONFIG:{}".format(self._xexConfigPath))

		return args

	def _getMiscArgs(self):
		return self._xexImageFlags


	################################################################################
	### Base class methods containing logic shared by all subclasses
	################################################################################

	def SetupForProject(self, project):
		Xbox360BaseTool.SetupForProject(self, project)

	def Run(self, inputProject, inputFile):
		"""
		Execute a single build step. Note that this method is run massively in parallel with other build steps.
		It is NOT thread-safe in ANY way. If you need to change shared state within this method, you MUST use a
		mutex.

		:param inputProject: project being built
		:type inputProject: csbuild._build.project.Project
		:param inputFile: File to build
		:type inputFile: input_file.InputFile
		:return: tuple of files created by the tool - all files must have an extension in the outputFiles list
		:rtype: tuple[str]

		:raises BuildFailureException: Build process exited with an error.
		"""
		log.Build(
			"Building XEX image for {} ({}-{}-{})...",
			os.path.basename(inputFile.filename),
			inputProject.toolchainName,
			inputProject.architectureName,
			inputProject.targetName
		)

		returncode, _, _ = commands.Run(self._getCommand(inputProject, inputFile))
		if returncode != 0:
			raise csbuild.BuildFailureException(inputProject, inputFile)
		return self._getOutputFiles(inputProject, inputFile)
