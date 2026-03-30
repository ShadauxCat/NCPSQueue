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
.. module:: ps3_linker
	:synopsis: Implementation of the PS3 linker tool.

.. moduleauthor:: Zoe Bare
"""

from __future__ import unicode_literals, division, print_function

import csbuild
import os

from .linker_base import LinkerBase, LibraryError

from ..common import FindLibraries
from ..common.sony_tool_base import Ps3BaseTool, Ps3ProjectType, Ps3ToolsetType

from ... import log
from ..._build.input_file import InputFile
from ..._utils import ordered_set, response_file, shared_globals

class Ps3Linker(Ps3BaseTool, LinkerBase):
	"""
	PS3 linker tool implementation.
	"""
	supportedArchitectures = { "cell" }

	inputGroups = { ".o" }
	outputFiles = { ".self", ".prx", ".sprx", ".a", ".spu_elf", ".spu_so" }
	crossProjectDependencies = { ".prx", ".sprx", ".a" }

	def __init__(self, projectSettings):
		Ps3BaseTool.__init__(self, projectSettings)
		LinkerBase.__init__(self, projectSettings)

		self._ldExeName = None
		self._arExeName = None
		self._linkerExeName = None


	####################################################################################################################
	### Methods implemented from base classes
	####################################################################################################################

	def SetupForProject(self, project):
		Ps3BaseTool.SetupForProject(self, project)

		# Intentionally reimplementing LinkerBase.SetupForProject() since PS3 has different
		# requirements for dependent projects.
		log.Linker("Verifying libraries for {}...", project)

		# Make all the library directory paths are absolute after the macro formatter has been run on them.
		self._libraryDirectories = ordered_set.OrderedSet(
			[os.path.abspath(directory) for directory in self._libraryDirectories]
		)

		if self._libraries:
			self._actualLibraryLocations = self._findLibraries(project, self._libraries)

			if self._actualLibraryLocations is None:
				raise LibraryError(project)

		# Fill in the locations of the depend projects, but only for libraries and SPU programs.
		for dependProject in project.dependencies:
			if dependProject.projectType not in (
				csbuild.ProjectType.Stub,
				Ps3ProjectType.PpuSncApplication,
				Ps3ProjectType.PpuGccApplication
			):
				outputExt = self._getOutputExtension(dependProject.projectType)
				if outputExt is not None:
					self._actualLibraryLocations[dependProject.outputName] = \
						os.path.join(
							dependProject.outputDir,
							"{}{}".format(dependProject.outputName, outputExt)
						)

		self._arExeName = {
			Ps3ToolsetType.PpuSnc: "ps3snarl.exe",
			Ps3ToolsetType.PpuGcc: "ppu-lv2-ar.exe",
			Ps3ToolsetType.Spu:    "spu-lv2-ar.exe",
		}.get(self._ps3BuildInfo.toolsetType, None)

		self._linkerExeName = {
			Ps3ToolsetType.PpuSnc: "ps3ppuld.exe",
			Ps3ToolsetType.PpuGcc: "ppu-lv2-g++.exe",
			Ps3ToolsetType.Spu:    "spu-lv2-g++.exe",
		}.get(self._ps3BuildInfo.toolsetType, None)

		assert self._arExeName and self._linkerExeName, "Invalid PS3 toolset type: {}".format(self._ps3BuildInfo.toolsetType)

	def _getOutputFiles(self, project):
		outputFilename = "{}{}".format(project.outputName, self._getOutputExtension(project.projectType))
		outputFullPath = os.path.join(project.outputDir, outputFilename)

		# PS3 SPU programs and shared libraries will be considered intermediate files since they will be converted
		# to compiled obj files and embedded in PPU programs.
		if project.projectType in (Ps3ProjectType.SpuApplication, Ps3ProjectType.SpuSharedLibrary):
			outputFullPath = os.path.join(project.GetIntermediateDirectory(InputFile(outputFullPath)), outputFilename)

		outputFiles = [outputFullPath]

		# For PPU shared libraries, the linker will automatically generate a stub library and verification log.
		if project.projectType in (Ps3ProjectType.PpuSncSharedLibrary, Ps3ProjectType.PpuGccSharedLibrary):
			outputFiles.extend([
				os.path.join(project.outputDir, "cellPrx_{}_stub.a".format(project.outputName)),
				os.path.join(project.outputDir, "cellPrx_{}_verlog.txt".format(project.outputName)),
			])

		return tuple(outputFiles)

	def _getCommand(self, project, inputFiles):
		if project.projectType in (Ps3ProjectType.PpuSncStaticLibrary, Ps3ProjectType.PpuGccStaticLibrary, Ps3ProjectType.SpuStaticLibrary):
			useResponseFile = False
			cmdExe = self._getArchiverName()
			cmd = ["rcs"] \
				+ self._getCustomLinkerArgs() \
				+ self._getOutputFileArgs(project) \
				+ self._getInputFileArgs(inputFiles)
		else:
			useResponseFile = True
			cmdExe = self._getLinkerName()
			cmd = self._getDefaultArgs(project) \
				+ self._getCustomLinkerArgs() \
				+ self._getOutputFileArgs(project) \
				+ self._getInputFileArgs(inputFiles) \
				+ self._getLibraryPathArgs() \
				+ self._getStartGroupArgs() \
				+ self._getLibraryArgs() \
				+ self._getEndGroupArgs()

		if useResponseFile:
			responseFile = response_file.ResponseFile(project, "linker-{}".format(project.outputName), cmd)

			if shared_globals.showCommands:
				log.Command("ResponseFile: {}\n\t{}".format(responseFile.filePath, responseFile.AsString()))

			cmd = [cmdExe, "@{}".format(responseFile.filePath)]

		else:
			cmd = [cmdExe] + cmd

		return cmd

	def _findLibraries(self, project, libs):
		allLibraryDirectories = list(self._libraryDirectories) + self._ps3SystemLibPaths

		return FindLibraries(libs, allLibraryDirectories, [".sprx", ".prx", ".a"])

	def _getOutputExtension(self, projectType):
		outputExt = {
			Ps3ProjectType.PpuSncApplication: ".self",
			Ps3ProjectType.PpuSncSharedLibrary: ".sprx",
			Ps3ProjectType.PpuSncStaticLibrary: ".a",

			Ps3ProjectType.PpuGccApplication: ".self",
			Ps3ProjectType.PpuGccSharedLibrary: ".prx",
			Ps3ProjectType.PpuGccStaticLibrary: ".a",

			Ps3ProjectType.SpuApplication: ".spu_elf",
			Ps3ProjectType.SpuSharedLibrary: ".spu_so",
			Ps3ProjectType.SpuStaticLibrary: ".a",
		}.get(projectType, None)

		return outputExt


	####################################################################################################################
	### Internal methods
	####################################################################################################################

	def _getLinkerName(self):
		return os.path.join(self._ps3SystemBinPath, self._linkerExeName)

	def _getArchiverName(self):
		return os.path.join(self._ps3SystemBinPath, self._arExeName)

	def _getDefaultArgs(self, project):
		args = {
			Ps3ProjectType.PpuSncApplication: [
				"-oformat=fself",
			],
			Ps3ProjectType.PpuSncSharedLibrary: [
				"-oformat=fsprx",
				"--prx-with-runtime",
			],

			Ps3ProjectType.PpuGccApplication: [
				"-pass-exit-codes",
				"-Wl,-oformat=fself",
			],
			Ps3ProjectType.PpuGccSharedLibrary: [
				"-pass-exit-codes",
				"-mprx-with-runtime",
				"-zgenprx",
				"-zgenstub",
			],

			Ps3ProjectType.SpuApplication: [
				"-pass-exit-codes",
				"-fstack-check",
			],
			Ps3ProjectType.SpuSharedLibrary: [
				"-pass-exit-codes",
				"-fstack-check",
				"-shared",
				"-Wl,-soname={}{}".format(project.outputName, self._getOutputExtension(project.projectType)),
			],
		}.get(project.projectType, [])

		return args

	def _getCustomLinkerArgs(self):
		return sorted(ordered_set.OrderedSet(self._linkerFlags))

	def _getOutputFileArgs(self, project):
		outFile = "{}".format(self._getOutputFiles(project)[0])
		if self._ps3BuildInfo.outputType == csbuild.ProjectType.StaticLibrary:
			return [outFile]
		return ["-o", outFile]

	def _getInputFileArgs(self, inputFiles):
		return [f.filename for f in inputFiles]

	def _getLibraryPathArgs(self):
		return []

	def _getLibraryArgs(self):
		args = []

		for libPath in self._actualLibraryLocations.values():
			libNameExt = os.path.splitext(libPath)

			# PRX libraries can't be linked directly. We have to link against their static stub libraries
			# that are generated when they are built.
			if libNameExt[1] in (".prx", ".sprx"):
				libPath = os.path.join(os.path.dirname(libPath), "cellPrx_{}_stub.a".format(os.path.basename(libNameExt[0])))

			elif libNameExt[1].startswith(".spu_"):
				libPath = "{}{}.a".format(libNameExt[0], libNameExt[1].replace(".", "_"))

			args.append(libPath)

		return args

	def _getStartGroupArgs(self):
		return [
			{
				Ps3ToolsetType.PpuSnc: "--start-group",
			}.get(self._ps3BuildInfo.toolsetType, "-Wl,--start-group")
		]

	def _getEndGroupArgs(self):
		return [
			{
				Ps3ToolsetType.PpuSnc: "--end-group",
			}.get(self._ps3BuildInfo.toolsetType, "-Wl,--end-group")
		]
