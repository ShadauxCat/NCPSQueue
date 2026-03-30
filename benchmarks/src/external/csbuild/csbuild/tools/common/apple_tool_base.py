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
.. module:: apple_tool_base
	:synopsis: Abstract base class for macOS tools.

.. moduleauthor:: Zoe Bare
"""

from __future__ import unicode_literals, division, print_function

import csbuild
import os
import re
import subprocess

from abc import ABCMeta

from ..._utils import ordered_set
from ..._utils.decorators import MetaClass
from ...toolchain import Tool
from ... import commands


def _ignore(_):
	pass

def _noLogOnRun(shared, msg):
	_ignore(shared)
	_ignore(msg)


class AppleHostToolInfo(object):
	"""
	Class for maintaining data output by Xcode tools installed on the host OS.
	"""
	Instance = None

	def __init__(self):
		try:
			# Verify the 'xcrun' program exists.
			subprocess.call(["xcrun"], stdout = subprocess.PIPE, stderr = subprocess.PIPE)
		except:
			raise IOError("Program 'xcrun' could not be found; please make sure you have installed Xcode and the command line build tools")

		try:
			# Verify the 'xcode-select' program exists.
			subprocess.call(["xcode-select"], stdout = subprocess.PIPE, stderr = subprocess.PIPE)
		except:
			raise IOError("Program 'xcode-select' could not be found; please make sure you have installed Xcode and the command line build tools")

		_, activeXcodeDevPath, _ = commands.Run(["xcode-select", "-p"], stdout = _noLogOnRun, stderr = _noLogOnRun)

		_, defaultMacOsSdkPath, _ = commands.Run(["xcrun", "--sdk", "macosx", "--show-sdk-path"], stdout = _noLogOnRun, stderr = _noLogOnRun)
		_, defaultIPhoneOsSdkPath, _, = commands.Run(["xcrun", "--sdk", "iphoneos", "--show-sdk-path"], stdout = _noLogOnRun, stderr = _noLogOnRun)
		_, defaultIPhoneSimSdkPath, _, = commands.Run(["xcrun", "--sdk", "iphonesimulator", "--show-sdk-path"], stdout = _noLogOnRun, stderr = _noLogOnRun)

		_, defaultMacOsSdkVersion, _, = commands.Run(["xcrun", "--sdk", "macosx", "--show-sdk-version"], stdout = _noLogOnRun, stderr = _noLogOnRun)
		_, defaultIPhoneOsSdkVersion, _, = commands.Run(["xcrun", "--sdk", "iphoneos", "--show-sdk-version"], stdout = _noLogOnRun, stderr = _noLogOnRun)
		_, defaultIPhoneSimSdkVersion, _, = commands.Run(["xcrun", "--sdk", "iphonesimulator", "--show-sdk-version"], stdout = _noLogOnRun, stderr = _noLogOnRun)

		self.activeXcodeToolchainPath = os.path.join(activeXcodeDevPath.strip(), "Toolchains", "XcodeDefault.xctoolchain")

		self.defaultMacOsSdkPath = defaultMacOsSdkPath.strip()
		self.defaultIPhoneOsSdkPath = defaultIPhoneOsSdkPath.strip()
		self.defaultIPhoneSimSdkPath = defaultIPhoneSimSdkPath.strip()

		self.defaultMacOsSdkVersion = defaultMacOsSdkVersion.strip()
		self.defaultIPhoneOsSdkVersion = defaultIPhoneOsSdkVersion.strip()
		self.defaultIPhoneSimSdkVersion = defaultIPhoneSimSdkVersion.strip()


@MetaClass(ABCMeta)
class AppleToolBase(Tool):
	"""
	Parent class for all tools targetting Apple platforms.

	:param projectSettings: A read-only scoped view into the project settings dictionary
	:type projectSettings: toolchain.ReadOnlySettingsView
	"""
	def __init__(self, projectSettings):
		Tool.__init__(self, projectSettings)

		self._frameworkDirectories = projectSettings.get("frameworkDirectories", ordered_set.OrderedSet())
		self._frameworks = projectSettings.get("frameworks", ordered_set.OrderedSet())

		# Add the default library framework locations.
		self._frameworkDirectories.update([
			x
			for x in [
				"/Library/Frameworks",
				os.path.expanduser("~/Library/Frameworks"),
			]
			if os.access(x, os.F_OK)
		])

		self._appleToolInfo = None


	####################################################################################################################
	### Static makefile methods
	####################################################################################################################

	@staticmethod
	def AddFrameworkDirectories(*dirs):
		"""
		Add directories to search for frameworks.

		:param dirs: List of directories
		:type dirs: str
		"""
		csbuild.currentPlan.UnionSet("frameworkDirectories", [os.path.abspath(directory) for directory in dirs])

	@staticmethod
	def AddFrameworks(*frameworks):
		"""
		Add frameworks to the current project.

		:param frameworks: List of frameworks.
		:type frameworks: str
		"""
		csbuild.currentPlan.UnionSet("frameworks", frameworks)


	####################################################################################################################
	### Methods implemented from base classes
	####################################################################################################################

	def SetupForProject(self, project):
		Tool.SetupForProject(self, project)

		# Create the mac tool info if the singleton doesn't already exist.
		if not AppleHostToolInfo.Instance:
			AppleHostToolInfo.Instance = AppleHostToolInfo()

		self._appleToolInfo = AppleHostToolInfo.Instance


@MetaClass(ABCMeta)
class MacOsToolBase(AppleToolBase):
	"""
	Parent class for all tools targetting the macOS platform.

	:param projectSettings: A read-only scoped view into the project settings dictionary
	:type projectSettings: toolchain.ReadOnlySettingsView
	"""
	def __init__(self, projectSettings):
		AppleToolBase.__init__(self, projectSettings)

		self._macOsVersionMin = projectSettings.get("macOsVersionMin", None)

		# When a version is not provided, default to the current version of the OS.
		if not self._macOsVersionMin:
			self._macOsVersionMin = self._getMacOsCurrentVersion()


	####################################################################################################################
	### Static makefile methods
	####################################################################################################################

	def SetMacOsVersionMin(self, version):
		"""
		Set the minimum version of macOS to build for.

		:param version: macOS version (e.g., "10.8", "10.9", "10.10", etc)
		:type version: str
		"""
		self._macOsVersionMin = csbuild.currentPlan.SetValue("macOsVersionMin", version)


	####################################################################################################################
	### Internal methods
	####################################################################################################################

	def _getMacOsCurrentVersion(self):
		currentVersion = subprocess.check_output(["sw_vers", "-productVersion"]).decode("utf-8")

		# The version number is returned in the "x.y.z" format, but we only need "x.y".
		versionRegex = re.compile(r"(\d+).(\d+)")
		match = versionRegex.match(currentVersion)
		assert match, f"Failed to parse macOS version: {currentVersion}"

		return f"{match.group(1)}.{match.group(2)}"
