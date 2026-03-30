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
.. module:: assembler_base
	:synopsis: Base class for assemblers

.. moduleauthor:: Zoe Bare
"""

from __future__ import unicode_literals, division, print_function

import csbuild

from abc import ABCMeta, abstractmethod

from ..common.tool_traits import (
	HasDebugLevel,
	HasDefines,
	HasIncludeDirectories,
)

from ... import commands, log

from ..._utils.decorators import MetaClass

def _ignore(_):
	pass

@MetaClass(ABCMeta)
class AssemblerBase(HasDebugLevel, HasDefines, HasIncludeDirectories):
	"""
	Base class for assemblers

	:param projectSettings: A read-only scoped view into the project settings dictionary
	:type projectSettings: toolchain.ReadOnlySettingsView
	"""
	################################################################################
	### Initialization
	################################################################################

	def __init__(self, projectSettings):
		HasDebugLevel.__init__(self, projectSettings)
		HasDefines.__init__(self, projectSettings)
		HasIncludeDirectories.__init__(self, projectSettings)

		self._asmFlags = projectSettings.get("asmFlags", [])

		self._projectTypeDefines = {
			csbuild.ProjectType.Application: "CSB_APPLICATION=1",
			csbuild.ProjectType.SharedLibrary: "CSB_SHARED_LIBRARY=1",
			csbuild.ProjectType.StaticLibrary: "CSB_STATIC_LIBRARY=1",
		}


	################################################################################
	### Static makefile methods
	################################################################################

	@staticmethod
	def AddAssemblerFlags(*flags):
		"""
		Add assembler flags.

		:param flags: List of asm flags
		:type flags: str
		"""
		csbuild.currentPlan.ExtendList("asmFlags", flags)


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
	def _getCommand(self, project, inputFile):
		return []


	################################################################################
	### Base class methods containing logic shared by all subclasses
	################################################################################

	def SetupForProject(self, project):
		HasDebugLevel.SetupForProject(self, project)
		HasDefines.SetupForProject(self, project)
		HasIncludeDirectories.SetupForProject(self, project)

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
			"Assembling {} ({}-{}-{})...",
			inputFile,
			inputProject.toolchainName,
			inputProject.architectureName,
			inputProject.targetName
		)

		returncode, _, _ = commands.Run(self._getCommand(inputProject, inputFile), env=self._getEnv(inputProject))
		if returncode != 0:
			raise csbuild.BuildFailureException(inputProject, inputFile)
		return self._getOutputFiles(inputProject, inputFile)
