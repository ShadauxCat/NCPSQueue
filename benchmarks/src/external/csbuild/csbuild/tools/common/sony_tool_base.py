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
.. module:: sony_tool_base
	:synopsis: Base tools for all Sony tool implementations.

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
class Ps3ProjectType(object):
	"""
	Replacement of the base ProjectType enum values specifically for PS3 projects.
	The original ProjectType values still work, but they will map directly to the
	PPU SNC output types.

	Note the overlapping types must be set manually since `ProjectType` cannot
	be imported into this module.
	"""
	PpuSncApplication = 1 # Identical to `csbuild.ProjectType.Application`.
	PpuSncSharedLibrary = 2 # Identical to `csbuild.ProjectType.SharedLibrary`.
	PpuSncStaticLibrary = 3 # Identical to `csbuild.ProjectType.StaticLibrary`.

	PpuGccApplication = PpuSncApplication + 3
	PpuGccSharedLibrary = PpuSncSharedLibrary + 3
	PpuGccStaticLibrary = PpuSncStaticLibrary + 3

	SpuApplication = PpuGccApplication + 3
	SpuSharedLibrary = PpuGccSharedLibrary + 3
	SpuStaticLibrary = PpuGccStaticLibrary + 3


@MetaClass(ABCMeta)
class Ps3ToolsetType(object):
	"""
	Identifiers for the toolset that will be used for any given PS3 build.
	"""
	PpuSnc = "ppu-snc"
	PpuGcc = "ppu-gcc"
	Spu = "spu"


class Ps3BuildInfo(object):
	"""
	Collection of info representing the type of a project's output and the toolset it will use for the
	build based on the project type.
	"""
	def __init__(self, projectType):
		self.outputType = {
			Ps3ProjectType.PpuSncApplication: csbuild.ProjectType.Application,
			Ps3ProjectType.PpuSncSharedLibrary: csbuild.ProjectType.SharedLibrary,
			Ps3ProjectType.PpuSncStaticLibrary: csbuild.ProjectType.StaticLibrary,

			Ps3ProjectType.PpuGccApplication: csbuild.ProjectType.Application,
			Ps3ProjectType.PpuGccSharedLibrary: csbuild.ProjectType.SharedLibrary,
			Ps3ProjectType.PpuGccStaticLibrary: csbuild.ProjectType.StaticLibrary,

			Ps3ProjectType.SpuApplication: csbuild.ProjectType.Application,
			Ps3ProjectType.SpuSharedLibrary: csbuild.ProjectType.SharedLibrary,
			Ps3ProjectType.SpuStaticLibrary: csbuild.ProjectType.StaticLibrary,
		}.get(projectType, None)

		self.toolsetType = {
			Ps3ProjectType.PpuSncApplication: Ps3ToolsetType.PpuSnc,
			Ps3ProjectType.PpuSncSharedLibrary: Ps3ToolsetType.PpuSnc,
			Ps3ProjectType.PpuSncStaticLibrary: Ps3ToolsetType.PpuSnc,

			Ps3ProjectType.PpuGccApplication: Ps3ToolsetType.PpuGcc,
			Ps3ProjectType.PpuGccSharedLibrary: Ps3ToolsetType.PpuGcc,
			Ps3ProjectType.PpuGccStaticLibrary: Ps3ToolsetType.PpuGcc,

			Ps3ProjectType.SpuApplication: Ps3ToolsetType.Spu,
			Ps3ProjectType.SpuSharedLibrary: Ps3ToolsetType.Spu,
			Ps3ProjectType.SpuStaticLibrary: Ps3ToolsetType.Spu,
		}.get(projectType, None)

		assert self.outputType is not None, "Cannot determine PS3 build info, invalid project type: {}".format(projectType)
		assert self.toolsetType is not None, "Cannot determine PS3 build info, invalid project type: {}".format(projectType)


@MetaClass(ABCMeta)
class SonyBaseTool(Tool):
	"""
	Parent class for all Sony tools.

	:param projectSettings: A read-only scoped view into the project settings dictionary
	:type projectSettings: toolchain.ReadOnlySettingsView
	"""
	def __init__(self, projectSettings):
		Tool.__init__(self, projectSettings)


@MetaClass(ABCMeta)
class Ps3BaseTool(SonyBaseTool):
	"""
	Parent class for all PS3 tools.

	:param projectSettings: A read-only scoped view into the project settings dictionary
	:type projectSettings: toolchain.ReadOnlySettingsView
	"""
	def __init__(self, projectSettings):
		SonyBaseTool.__init__(self, projectSettings)

		self._ps3SdkPath = projectSettings.get("ps3SdkPath", None)
		self._ps3SnPath = projectSettings.get("ps3SnPath", None)

		self._ps3BuildInfo = None # type: Ps3BuildInfo
		self._ps3HostBinPath = None # type: str
		self._ps3SystemBinPath = None # type: str
		self._ps3SystemLibPaths = [] # type: list[str]
		self._ps3SystemIncludePaths = [] # type: list[str]


	####################################################################################################################
	### Static makefile methods
	####################################################################################################################

	@staticmethod
	def SetPs3SdkPath(path):
		"""
		Set the path to the PS3 SDK.

		:param path: Path to the PS3 SDK.
		:type path: str
		"""
		csbuild.currentPlan.SetValue("ps3SdkPath", os.path.abspath(path) if path else None)

	@staticmethod
	def SetPs3SnPath(path):
		"""
		Set the path to the PS3 SN Systems directory.

		:param path: Path to the PS3 SN Systems installation directory.
		:type path: str
		"""
		csbuild.currentPlan.SetValue("ps3SnPath", os.path.abspath(path) if path else None)


	####################################################################################################################
	### Methods implemented from base classes
	####################################################################################################################

	def SetupForProject(self, project):
		# If the SDK path wasn't set, attempt to find it from the environment.
		if not self._ps3SdkPath:
			self._ps3SdkPath = os.getenv("SCE_PS3_ROOT", None)

		if not self._ps3SnPath:
			self._ps3SnPath = os.getenv("SN_PS3_PATH", None)

		assert self._ps3SdkPath, "No PS3 SDK path has been set"
		assert os.access(self._ps3SdkPath, os.F_OK), "PS3 SDK path does not exist: {}".format(self._ps3SdkPath)

		assert self._ps3SnPath, "No PS3 SN Systems path has been set"
		assert os.access(self._ps3SnPath, os.F_OK), "PS3 SN Systems path does not exist: {}".format(self._ps3SnPath)

		self._ps3BuildInfo = Ps3BuildInfo(project.projectType)

		self._ps3SdkPath = os.path.abspath(self._ps3SdkPath)
		self._ps3SnPath = os.path.abspath(self._ps3SnPath)

		hostRootPath = os.path.join(self._ps3SdkPath, "host-win32")
		self._ps3HostBinPath = os.path.join(hostRootPath, "bin")

		buildToolRootPath = {
			Ps3ToolsetType.PpuSnc: os.path.join(hostRootPath, "sn"),
			Ps3ToolsetType.PpuGcc: os.path.join(hostRootPath, "ppu"),
			Ps3ToolsetType.Spu: os.path.join(hostRootPath, "spu"),
		}.get(self._ps3BuildInfo.toolsetType, None)

		self._ps3SystemBinPath = os.path.join(buildToolRootPath, "bin")
		self._ps3SystemLibPaths = []
		self._ps3SystemIncludePaths = [
			os.path.join(self._ps3SdkPath, "target", "common", "include"),
		]

		if self._ps3BuildInfo.toolsetType == Ps3ToolsetType.Spu:
			self._ps3SystemLibPaths.extend([
				os.path.join(self._ps3SnPath, "spu", "lib", "sn"),
				os.path.join(self._ps3SdkPath, "target", "spu", "lib"),
			])

			self._ps3SystemIncludePaths.extend([
				os.path.join(self._ps3SnPath, "spu", "include", "sn"),
				os.path.join(self._ps3SdkPath, "target", "spu", "include"),
			])

		else:
			self._ps3SystemLibPaths.extend([
				os.path.join(self._ps3SnPath, "ppu", "lib", "sn"),
				os.path.join(self._ps3SdkPath, "target", "ppu", "lib"),
			])

			self._ps3SystemIncludePaths.extend([
				os.path.join(self._ps3SnPath, "ppu", "include", "sn"),
				os.path.join(self._ps3SdkPath, "target", "ppu", "include"),
			])


class Ps3SpuConverter(Ps3BaseTool, HasOptimizationLevel):
	"""
	Tool that converts SPU binaries to PPU compiled objects for linking into PPU binaries.

	:param projectSettings: A read-only scoped view into the project settings dictionary
	:type projectSettings: toolchain.ReadOnlySettingsView
	"""
	supportedPlatforms = { "Windows" }
	supportedArchitectures = { "cell" }
	inputFiles = { ".spu_elf", ".spu_so" }
	outputFiles = { ".a" }

	################################################################################
	### Initialization
	################################################################################

	def __init__(self, projectSettings):
		Ps3BaseTool.__init__(self, projectSettings)
		HasOptimizationLevel.__init__(self, projectSettings)


	################################################################################
	### Internal methods
	################################################################################

	def _getOutputFiles(self, project, inputFile):
		inputFileExtSplit = os.path.splitext(os.path.basename(inputFile.filename))
		outputFilePath = os.path.join(
			project.outputDir,
			"{}{}.a".format(
				inputFileExtSplit[0],
				inputFileExtSplit[1].replace(".", "_")
			)
		)
		return tuple({ outputFilePath })

	def _getCommand(self, project, inputFile):
		cmdExe = self._getExeName()
		cmd = [cmdExe] \
			+ self._getStripModeArgs() \
			+ self._getInputArgs(inputFile) \
			+ self._getOutputArgs(project, inputFile)

		return cmd

	def _getExeName(self):
		return os.path.join(self._ps3HostBinPath, "spu_elf-to-ppu_obj.exe")

	def _getStripModeArgs(self):
		stripMode = {
			OptimizationLevel.Disabled: "none",
			OptimizationLevel.Max: "hard",
		}.get(self._optLevel, "normal")
		return ["--strip-mode={}".format(stripMode)]

	def _getInputArgs(self, inputFile):
		return [inputFile.filename]

	def _getOutputArgs(self, project, inputFile):
		return [self._getOutputFiles(project, inputFile)[0]]


	################################################################################
	### Base class methods containing logic shared by all subclasses
	################################################################################

	def SetupForProject(self, project):
		Ps3BaseTool.SetupForProject(self, project)

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
			"Converting SPU binary {} ({}-{}-{})...",
			os.path.basename(inputFile.filename),
			inputProject.toolchainName,
			inputProject.architectureName,
			inputProject.targetName
		)

		returncode, _, _ = commands.Run(self._getCommand(inputProject, inputFile))
		if returncode != 0:
			raise csbuild.BuildFailureException(inputProject, inputFile)
		return self._getOutputFiles(inputProject, inputFile)


@MetaClass(ABCMeta)
class Ps4BaseTool(SonyBaseTool):
	"""
	Parent class for all PS4 tools.

	:param projectSettings: A read-only scoped view into the project settings dictionary
	:type projectSettings: toolchain.ReadOnlySettingsView
	"""
	def __init__(self, projectSettings):
		SonyBaseTool.__init__(self, projectSettings)

		self._ps4SdkPath = projectSettings.get("ps4SdkPath", None)


	####################################################################################################################
	### Static makefile methods
	####################################################################################################################

	@staticmethod
	def SetPs4SdkPath(sdkPath):
		"""
		Set the path to the PS4 SDK.

		:param sdkPath: Path to the PS4 SDK.
		:type sdkPath: str
		"""
		csbuild.currentPlan.SetValue("ps4SdkPath", os.path.abspath(sdkPath) if sdkPath else None)


	####################################################################################################################
	### Methods implemented from base classes
	####################################################################################################################

	def SetupForProject(self, project):
		# If the SDK path wasn't set, attempt to find it from the environment.
		if not self._ps4SdkPath:
			self._ps4SdkPath = os.getenv("SCE_ORBIS_SDK_DIR", None)

		assert self._ps4SdkPath, "No PS4 SDK path has been set"
		assert os.access(self._ps4SdkPath, os.F_OK), "PS4 SDK path does not exist: {}".format(self._ps4SdkPath)


@MetaClass(ABCMeta)
class Ps5BaseTool(SonyBaseTool):
	"""
	Parent class for all PS5 tools.

	:param projectSettings: A read-only scoped view into the project settings dictionary
	:type projectSettings: toolchain.ReadOnlySettingsView
	"""
	def __init__(self, projectSettings):
		SonyBaseTool.__init__(self, projectSettings)

		self._ps5SdkPath = projectSettings.get("ps5SdkPath", None)


	####################################################################################################################
	### Static makefile methods
	####################################################################################################################

	@staticmethod
	def SetPs5SdkPath(sdkPath):
		"""
		Set the path to the PS5 SDK.

		:param sdkPath: Path to the PS5 SDK.
		:type sdkPath: str
		"""
		csbuild.currentPlan.SetValue("ps5SdkPath", os.path.abspath(sdkPath) if sdkPath else None)


	####################################################################################################################
	### Methods implemented from base classes
	####################################################################################################################

	def SetupForProject(self, project):
		# If the SDK path wasn't set, attempt to find it from the environment.
		if not self._ps5SdkPath:
			self._ps5SdkPath = os.getenv("SCE_PROSPERO_SDK_DIR", None)

		assert self._ps5SdkPath, "No PS5 SDK path has been set"
		assert os.access(self._ps5SdkPath, os.F_OK), "PS5 SDK path does not exist: {}".format(self._ps5SdkPath)


@MetaClass(ABCMeta)
class PsVitaBaseTool(SonyBaseTool):
	"""
	Parent class for all PSVita tools.

	:param projectSettings: A read-only scoped view into the project settings dictionary
	:type projectSettings: toolchain.ReadOnlySettingsView
	"""
	def __init__(self, projectSettings):
		SonyBaseTool.__init__(self, projectSettings)

		self._psVitaSdkPath = projectSettings.get("psVitaSdkPath", None)


	####################################################################################################################
	### Static makefile methods
	####################################################################################################################

	@staticmethod
	def SetPsVitaSdkPath(sdkPath):
		"""
		Set the path to the PSVita SDK.

		:param sdkPath: Path to the PSVita SDK.
		:type sdkPath: str
		"""
		csbuild.currentPlan.SetValue("psVitaSdkPath", os.path.abspath(sdkPath))


	####################################################################################################################
	### Methods implemented from base classes
	####################################################################################################################

	def SetupForProject(self, project):
		# If the SDK path wasn't set, attempt to find it from the environment.
		if not self._psVitaSdkPath:
			self._psVitaSdkPath = os.getenv("SCE_PSP2_SDK_DIR", None)

		assert self._psVitaSdkPath, "No PSVita SDK path has been set"
		assert os.access(self._psVitaSdkPath, os.F_OK), "PS4 PSVita path does not exist: {}".format(self._psVitaSdkPath)
