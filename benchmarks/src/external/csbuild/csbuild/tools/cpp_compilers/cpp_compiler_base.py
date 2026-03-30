# Copyright (C) 2016 Jaedyn K. Draper
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
.. module:: cpp_compiler_base
	:synopsis: Basic class for C++ compilers

.. moduleauthor:: Jaedyn K. Draper
"""

from __future__ import unicode_literals, division, print_function

import os
import csbuild

from abc import ABCMeta, abstractmethod

from ..common.tool_traits import \
	HasDebugLevel, \
	HasDebugRuntime, \
	HasDefines, \
	HasIncludeDirectories, \
	HasOptimizationLevel, \
	HasStaticRuntime, \
	HasCcLanguageStandard, \
	HasCxxLanguageStandard \

from ... import commands, log
from ..._utils.decorators import MetaClass

def _ignore(_):
	pass

@MetaClass(ABCMeta)
class CppCompilerBase(
	HasDebugLevel,
	HasDebugRuntime,
	HasDefines,
	HasIncludeDirectories,
	HasOptimizationLevel,
	HasStaticRuntime,
	HasCcLanguageStandard,
	HasCxxLanguageStandard
):
	"""
	Base class for C++ compilers

	:param projectSettings: A read-only scoped view into the project settings dictionary
	:type projectSettings: toolchain.ReadOnlySettingsView
	"""
	inputFiles={".cpp", ".c", ".cc", ".cxx"}
	dependencies={".gch", ".pch"}

	################################################################################
	### Initialization
	################################################################################

	def __init__(self, projectSettings):
		self._globalFlags = projectSettings.get("globalFlags", [])
		self._cFlags = projectSettings.get("cFlags", [])
		self._cxxFlags = projectSettings.get("cxxFlags", [])

		HasDebugLevel.__init__(self, projectSettings)
		HasDebugRuntime.__init__(self, projectSettings)
		HasDefines.__init__(self, projectSettings)
		HasIncludeDirectories.__init__(self, projectSettings)
		HasOptimizationLevel.__init__(self, projectSettings)
		HasStaticRuntime.__init__(self, projectSettings)
		HasCcLanguageStandard.__init__(self, projectSettings)
		HasCxxLanguageStandard.__init__(self, projectSettings)

		self._projectTypeDefines = {
			csbuild.ProjectType.Application: "CSB_APPLICATION=1",
			csbuild.ProjectType.SharedLibrary: "CSB_SHARED_LIBRARY=1",
			csbuild.ProjectType.StaticLibrary: "CSB_STATIC_LIBRARY=1",
		}


	################################################################################
	### Static makefile methods
	################################################################################

	@staticmethod
	def AddCompilerFlags(*flags):
		"""
		Add compiler flags that are applid to both C and C++ files.

		:param flags: List of flags
		:type flags: str
		"""
		csbuild.currentPlan.ExtendList("globalFlags", flags)

	@staticmethod
	def AddCompilerCcFlags(*flags):
		"""
		Add compiler C flags.

		:param flags: List of C flags
		:type flags: str
		"""
		csbuild.currentPlan.ExtendList("cFlags", flags)

	@staticmethod
	def AddCompilerCxxFlags(*flags):
		"""
		Add compiler C++ flags.

		:param flags: List of C++ flags
		:type flags: str
		"""
		csbuild.currentPlan.ExtendList("cxxFlags", flags)


	################################################################################
	### Methods that may be implemented by subclasses as needed
	################################################################################

	def _getEnv(self, project):
		_ignore(project)
		return None


	################################################################################
	### Abstract methods that need to be implemented by subclasses
	################################################################################

	@abstractmethod
	def _getOutputFiles(self, project, inputFile):
		return ("", )

	@abstractmethod
	def _getCommand(self, project, inputFile, isCpp):
		return []


	################################################################################
	### Base class methods containing logic shared by all subclasses
	################################################################################

	def SetupForProject(self, project):
		HasDebugLevel.SetupForProject(self, project)
		HasDebugRuntime.SetupForProject(self, project)
		HasDefines.SetupForProject(self, project)
		HasIncludeDirectories.SetupForProject(self, project)
		HasOptimizationLevel.SetupForProject(self, project)
		HasStaticRuntime.SetupForProject(self, project)
		HasCcLanguageStandard.SetupForProject(self, project)
		HasCxxLanguageStandard.SetupForProject(self, project)

		if project.projectType in self._projectTypeDefines:
			self._defines.add(self._projectTypeDefines[project.projectType])

		self._defines.add("CSB_TARGET_{}=1".format(project.targetName.upper()))

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
			"Compiling {} ({}-{}-{})...",
			inputFile,
			inputProject.toolchainName,
			inputProject.architectureName,
			inputProject.targetName
		)

		_, extension = os.path.splitext(inputFile.filename)
		returncode, _, _ = commands.Run(self._getCommand(inputProject, inputFile, extension in {".cpp", ".cc", ".cxx", ".mm"}), env=self._getEnv(inputProject))
		if returncode != 0:
			raise csbuild.BuildFailureException(inputProject, inputFile)
		return self._getOutputFiles(inputProject, inputFile)
