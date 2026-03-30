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
.. module:: tool_traits
	:synopsis: Optional add-ins for tools.

.. moduleauthor:: Zoe Bare
"""

from __future__ import unicode_literals, division, print_function

import csbuild
import os

from ... import log
from ...toolchain import Tool
from ..._utils import ordered_set

class HasDebugLevel(Tool):
	"""
	Helper class to add debug level support to a tool.

	:param projectSettings: A read-only scoped view into the project settings dictionary
	:type projectSettings: toolchain.ReadOnlySettingsView
	"""
	class DebugLevel(object):
		"""
		'enum' representing various levels of debug information
		"""
		Disabled = 0
		EmbeddedSymbols = 1
		ExternalSymbols = 2
		ExternalSymbolsPlus = 3

	def __init__(self, projectSettings):
		Tool.__init__(self, projectSettings)
		self._debugLevel = projectSettings.get("debugLevel", HasDebugLevel.DebugLevel.Disabled)

	@staticmethod
	def SetDebugLevel(debugLevel):
		"""
		Set a project's desired debug level.

		:param debugLevel: Project debug level.
		:type debugLevel: :class:`csbuild.tools.common.tool_traits.HasDebugLevel.DebugLevel`
		"""
		csbuild.currentPlan.SetValue("debugLevel", debugLevel)

	@staticmethod
	def SetDebugLevelIfUnset(debugLevel):
		"""
		Set a project's desired debug level. If already set, does nothing.

		:param debugLevel: Project debug level.
		:type debugLevel: :class:`csbuild.tools.common.tool_traits.HasDebugLevel.DebugLevel`
		"""
		if not csbuild.currentPlan.HasValue("debugLevel"):
			log.Info("Setting default debug level.")
			csbuild.currentPlan.SetValue("debugLevel", debugLevel)


class HasOptimizationLevel(Tool):
	"""
	Helper class to add optimization level support to a tool.

	:param projectSettings: A read-only scoped view into the project settings dictionary
	:type projectSettings: toolchain.ReadOnlySettingsView
	"""
	class OptimizationLevel(object):
		"""
		'enum' representing various optimization levels
		"""
		Disabled = 0
		Size = 1
		Speed = 2
		Max = 3

	def __init__(self, projectSettings):
		Tool.__init__(self, projectSettings)
		self._optLevel = projectSettings.get("optLevel", HasOptimizationLevel.OptimizationLevel.Disabled)

	@staticmethod
	def SetOptimizationLevel(optLevel):
		"""
		Set a project's desired optimization level.

		:param optLevel: Project optimization level.
		:type optLevel: :class:`csbuild.tools.common.has_debug_level.OptimizationLevel`
		"""
		csbuild.currentPlan.SetValue("optLevel", optLevel)

	@staticmethod
	def SetOptimizationLevelIfUnset(optLevel):
		"""
		Set a project's desired optimization level. If already set, does nothing.

		:param optLevel: Project optimization level.
		:type optLevel: :class:`csbuild.tools.common.has_debug_level.OptimizationLevel`
		"""
		if not csbuild.currentPlan.HasValue("optLevel"):
			log.Info("Setting default optimization level.")
			csbuild.currentPlan.SetValue("optLevel", optLevel)


class HasStaticRuntime(Tool):
	"""
	Helper class to add static runtime support to a tool.

	:param projectSettings: A read-only scoped view into the project settings dictionary
	:type projectSettings: toolchain.ReadOnlySettingsView
	"""
	def __init__(self, projectSettings):
		Tool.__init__(self, projectSettings)
		self._staticRuntime = projectSettings.get("staticRuntime", False)

	@staticmethod
	def SetStaticRuntime(staticRuntime):
		"""
		Set whether or not a project should use the static runtime library.

		:param staticRuntime: Use the static runtime library.
		:type staticRuntime: bool
		"""
		csbuild.currentPlan.SetValue("staticRuntime", staticRuntime)


class HasDebugRuntime(Tool):
	"""
	Helper class to add debug runtime support to a tool.

	:param projectSettings: A read-only scoped view into the project settings dictionary
	:type projectSettings: toolchain.ReadOnlySettingsView
	"""
	def __init__(self, projectSettings):
		Tool.__init__(self, projectSettings)
		self._debugRuntime = projectSettings.get("debugRuntime", False)

	@staticmethod
	def SetDebugRuntime(debugRuntime):
		"""
		Set whether or not a project should use the debug runtime library.

		:param debugRuntime: Use the debug runtime library.
		:type debugRuntime: bool
		"""
		csbuild.currentPlan.SetValue("debugRuntime", debugRuntime)

	@staticmethod
	def SetDebugRuntimeIfUnset(debugRuntime):
		"""
		Set whether or not a project should use the debug runtime library. If already set, does nothing.

		:param debugRuntime: Use the debug runtime library.
		:type debugRuntime: bool
		"""
		if not csbuild.currentPlan.HasValue("debugRuntime"):
			log.Info("Setting default debug runtime setting.")
			csbuild.currentPlan.SetValue("debugRuntime", debugRuntime)


class HasIncludeDirectories(Tool):
	"""
	Helper class to add C++ include directories.

	:param projectSettings: A read-only scoped view into the project settings dictionary
	:type projectSettings: toolchain.ReadOnlySettingsView
	"""
	def __init__(self, projectSettings):
		Tool.__init__(self, projectSettings)
		self._includeDirectories = projectSettings.get("includeDirectories", ordered_set.OrderedSet())

	@staticmethod
	def AddIncludeDirectories(*dirs):
		"""
		Add directories to search for headers in.

		:param dirs: list of directories
		:type dirs: str
		"""
		csbuild.currentPlan.UnionSet("includeDirectories", [os.path.abspath(d) for d in dirs if d])

	def GetIncludeDirectories(self):
		"""
		Get the list of include directories.

		:return: include dirs
		:rtype: ordered_set.OrderedSet[str]
		"""
		return self._includeDirectories

	def SetupForProject(self, project):
		self._includeDirectories = ordered_set.OrderedSet(self._includeDirectories)


class HasDefines(Tool):
	"""
	Helper class to add C++ defines and undefines.

	:param projectSettings: A read-only scoped view into the project settings dictionary
	:type projectSettings: toolchain.ReadOnlySettingsView
	"""
	def __init__(self, projectSettings):
		Tool.__init__(self, projectSettings)
		self._defines = projectSettings.get("defines", ordered_set.OrderedSet())
		self._undefines = projectSettings.get("undefines", ordered_set.OrderedSet())

	@staticmethod
	def AddDefines(*defines):
		"""
		Add preprocessor defines to the current project.

		:param defines: List of defines.
		:type defines: str
		"""
		csbuild.currentPlan.UnionSet("defines", defines)

	@staticmethod
	def AddUndefines(*undefines):
		"""
		Add preprocessor undefines to the current project.

		:param undefines: List of undefines.
		:type undefines: str
		"""
		csbuild.currentPlan.UnionSet("undefines", undefines)


class HasCcLanguageStandard(Tool):
	"""
	Helper class to set the C language standard to a tool.

	:param projectSettings: A read-only scoped view into the project settings dictionary
	:type projectSettings: toolchain.ReadOnlySettingsView
	"""
	def __init__(self, projectSettings):
		Tool.__init__(self, projectSettings)
		self._ccStandard = projectSettings.get("ccLanguageStandard", None)

	@staticmethod
	def SetCcLanguageStandard(standard):
		"""
		Set the C language standard.

		:param standard: C language standard.
		:type standard: str
		"""
		standard = standard.strip().lower()
		assert standard.startswith("c") and not standard.startswith("c+"), "Invalid C standard: {}".format(standard)
		csbuild.currentPlan.SetValue("ccLanguageStandard", standard)


class HasCxxLanguageStandard(Tool):
	"""
	Helper class to set the C++ language standard to a tool.

	:param projectSettings: A read-only scoped view into the project settings dictionary
	:type projectSettings: toolchain.ReadOnlySettingsView
	"""
	def __init__(self, projectSettings):
		Tool.__init__(self, projectSettings)
		self._cxxStandard = projectSettings.get("cxxLanguageStandard", None)

	@staticmethod
	def SetCxxLanguageStandard(standard):
		"""
		Set the C++ language standard.

		:param standard: C++ language standard.
		:type standard: str
		"""
		standard = standard.strip().lower()
		assert standard.startswith("c++"), "Invalid C++ standard: {}".format(standard)
		csbuild.currentPlan.SetValue("cxxLanguageStandard", standard)


class HasIncrementalLink(Tool):
	"""
	Helper class to enable incremental linking in linker tools that support it.

	:param projectSettings: A read-only scoped view into the project settings dictionary
	:type projectSettings: toolchain.ReadOnlySettingsView
	"""
	def __init__(self, projectSettings):
		Tool.__init__(self, projectSettings)
		self._incrementalLink = projectSettings.get("incrementalLink", False)

	@staticmethod
	def SetIncrementalLink(incrementalLink):
		"""
		Set the incremental link property.

		:param incrementalLink: Incremental link toggle
		:type incrementalLink: bool
		"""
		csbuild.currentPlan.SetValue("incrementalLink", incrementalLink)

class HasWinRtSupport(Tool):
	"""
	Helper class to add support for compiling WinRT projects.

	:param projectSettings: A read-only scoped view into the project settings dictionary
	:type projectSettings: toolchain.ReadOnlySettingsView
	"""
	class WinRtSupport(object):
		"""
		'enum' representing various levels of WinRT support
		"""
		Disabled = 0
		Enabled = 1
		EnabledNoStdLib = 2

	def __init__(self, projectSettings):
		Tool.__init__(self, projectSettings)
		self._winrtSupport = projectSettings.get("winrtSupport", HasWinRtSupport.WinRtSupport.Disabled)

	@staticmethod
	def SetWinRtSupport(winrtSupport):
		"""
		Set WinRT support.

		:param winrtSupport: Incremental link toggle
		:type winrtSupport: :class:`csbuild.tools.common.tool_traits.HasWinRtSupport.WinRtSupport`
		"""
		csbuild.currentPlan.SetValue("winrtSupport", winrtSupport)
