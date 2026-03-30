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
.. module:: msvc_tool_base
	:synopsis: Abstract base class for msvc tools.

.. moduleauthor:: Zoe Bare
"""

from __future__ import unicode_literals, division, print_function

import csbuild
import json
import os

from abc import ABCMeta, abstractmethod

from csbuild import log
from ..._utils.decorators import MetaClass, TypeChecked
from ..._utils import PlatformString
from ...toolchain import Tool
from ... import commands


def _ignore(_):
	pass

def _noLogOnRun(shared, msg):
	_ignore(shared)
	_ignore(msg)


class Vcvarsall(object):
	"""
	Class for maintaining data output by vcvarsall.bat.

	:param binPath: Path to the msvc binaries.
	:type binPath: str

	:param libPaths: List of paths to Windows SDK libraries.
	:type libPaths: list

	:param winSdkVersion: Selected Windows SDK version (can be None for versions of Visual Studio that do not support selecting the SDK to be built against).
	:type winSdkVersion: str

	:param env: Custom environment dictionary extracted from the vcvarsall.bat output.
	:type env: dict
	"""

	Instances = dict()

	def __init__(self, binPath, libPaths, winSdkVersion, env):
		self.binPath = binPath
		self.libPaths = libPaths
		self.winSdkVersion = winSdkVersion
		self.env = env


	@staticmethod
	def Create(fullEnvString):
		"""
		Factory function for creating a Vcvarsall instance from a string containing all environment variables to parse.

		:param fullEnvString: New-line separated string of all environment variables.
		:type fullEnvString: str

		:return: New Vcvarsall instance.
		:rtype: :class:`csbuild.tools.common.msvc_tool_base.Vcvarsall`
		"""
		envLines = fullEnvString.splitlines()

		binPath = ""
		libPaths = []
		winSdkVersion = None
		env = dict()

		for line in envLines:
			line = PlatformString(line)

			# Skip empty lines.
			if not line:
				continue

			keyValue = line.split("=", 1)

			# Skip lines that are not in the valid key/value format.
			if len(keyValue) < 2:
				continue

			key = PlatformString(keyValue[0])
			value = PlatformString(keyValue[1])

			env[key] = value
			keyLowered = key.lower()

			if keyLowered == "path":
				# Passing a custom environment to subprocess.Popen() does not always help in locating a command
				# to execute on Windows (seems to be a bug with CreateProcess()), so we still need to find the
				# path where the tools live.
				for envPath in [path for path in value.split(";") if path]:
					if os.access(os.path.join(envPath, "cl.exe"), os.F_OK):
						binPath = PlatformString(envPath)
						break
			elif keyLowered == "lib":
				# Extract the SDK library directory paths.
				libPaths = [PlatformString(path) for path in value.split(";") if path]
			elif keyLowered == "windowssdkversion":
				winSdkVersion = value.strip("\\")
			elif keyLowered == "windowssdklibversion":
				# Windows SDK 8.1 doesn't show up in a user friendly way, so we attempt to manually detect it.
				if value == "winv6.3\\":
					winSdkVersion = "8.1"

		# No bin path means the environment is not valid.
		if not binPath:
			return None

		return Vcvarsall(binPath, libPaths, winSdkVersion, env)


class _ArchitectureInfo(object):
	def __init__(self, currentArch, projectArch, vcvarsArch, winSdkVersion, universalApp):
		self.currentArch = currentArch
		self.projectArch = projectArch
		self.vcvarsArch = vcvarsArch
		self.winSdkVersion = winSdkVersion
		self.universalApp = universalApp


class _BaseInstallData(object):
	def __init__(self, version, displayName, path):
		self.version = version
		self.displayName = displayName
		self.path = path


	@staticmethod
	@abstractmethod
	def FindInstallations():
		"""
		Static function to find all available installations of Visual Studio.

		:rtype: list[:class:`csbuild.tools.common.msvc_tool_base._BaseInstallData`]
		"""
		pass


	@abstractmethod
	def GetEnvironment(self, archInfo):
		"""
		Retrieve the Vcvarsall instance for the current install data using the supplied architecture info.

		:param archInfo: Architecture info.
		:type archInfo: :class:`csbuild.tools.common.msvc_tool_base._ArchitectureInfo`

		:rtype: :class:`csbuild.tools.common.msvc_tool_base.Vcvarsall`
		"""
		pass


class _InstallDataPost2017(_BaseInstallData):
	def __init__(self, version, displayName, path):
		_BaseInstallData.__init__(self, version, displayName, path)


	@staticmethod
	def FindInstallations():
		progFilesX86Path = os.getenv("ProgramFiles(x86)")
		assert progFilesX86Path, "Failed to find the \"Program Files (x86)\" path"

		vsWhereFilePath = os.path.join(progFilesX86Path, "Microsoft Visual Studio", "Installer", "vswhere.exe")

		if not os.access(vsWhereFilePath, os.F_OK):
			# The file doesn't exist, so Visual Studio 2017 (or newer) hasn't been installed.
			return []

		cmd = [
			vsWhereFilePath,
			"-format", "json",
			"-requires", "Microsoft.VisualStudio.Component.VC.Tools.x86.x64",
		]

		# Launch vswhere.exe to output information about each supported install.
		_, output, _ = commands.Run(cmd, stdout=_noLogOnRun, stderr=_noLogOnRun)

		# Load the install data from json.
		foundInstallations = json.loads(output)

		installDataMap = {}
		installDataList = []

		# Parse the install information.
		for install in foundInstallations:
			version = int(install["installationVersion"].split(".")[0])
			displayName = install["displayName"]
			path = install["installationPath"]

			if version not in installDataMap:
				installDataMap.update({ version: [] })

			installDataMap[version].append(_InstallDataPost2017(version, displayName, path))

		# Sort the versions by latest to oldest.
		sortedKeys = reversed(sorted(installDataMap.keys()))

		for versionKey in sortedKeys:
			installsForVersion = installDataMap[versionKey]
			installDataList.extend(installsForVersion)

		return installDataList


	def GetEnvironment(self, archInfo):
		toolsRootPath = os.path.join(self.path, "Common7", "Tools")
		batchFilePath = os.path.join(toolsRootPath, "VsDevCmd.bat")

		cmd = [
			batchFilePath,
			"-no_logo",
			"-arch={}".format(archInfo.projectArch),
			"-host_arch={}".format(archInfo.currentArch),
			"-winsdk={}".format(archInfo.winSdkVersion) if archInfo.winSdkVersion else "",
			"-app_platform={}".format("UWP" if archInfo.universalApp else "Desktop"),
			"&",
			"set",
		]

		_, output, _ = commands.Run([x for x in cmd if x], stdout=_noLogOnRun, stderr=_noLogOnRun)

		# Strip out the \r characters.
		output = output.replace("\r", "")

		assert not output.startswith("[ERROR"), output.split("\n", 1)[0]

		return Vcvarsall.Create(output)


class _InstallDataPre2017(_BaseInstallData):
	def __init__(self, version, displayName, path):
		_BaseInstallData.__init__(self, version, displayName, path)


	@staticmethod
	def FindInstallations():
		vsVersionMacros = [
			("14", "VS140COMNTOOLS", "Visual Studio 2015"),
			("12", "VS120COMNTOOLS", "Visual Studio 2013"),
			("11", "VS110COMNTOOLS", "Visual Studio 2012"),
			("10", "VS100COMNTOOLS", "Visual Studio 2010"),
		]

		installDataList = []

		# Check for each version listed.
		for version, macro, displayName in vsVersionMacros:
			if macro in os.environ:
				path = os.path.abspath(os.path.join(os.environ[macro], "..", ".."))

				installDataList.append(_InstallDataPre2017(version, displayName, path))

		return installDataList


	def GetEnvironment(self, archInfo):
		msvcRootPath = os.path.join(self.path, "VC")
		batchFilePath = os.path.join(msvcRootPath, "vcvarsall.bat")
		vcvarsArch = archInfo.vcvarsArch
		storeArg = ""
		winSdkArg = ""

		if self.version == "14":
			# Only Visual Studio 2015 supports the specifying the Windows SDK version and the "store" argument.
			winSdkArg = archInfo.winSdkVersion or ""

			if archInfo.universalApp:
				storeArg = "store"

		elif self.version != "12":
			# Visual Studio versions prior to 2013 did not have x64-specific tools for x86 and arm.
			vcvarsArch = {
				"amd64_x86": "x86",
				"amd64_arm": "arm",
			}.get(vcvarsArch, vcvarsArch)

		cmd = [
			batchFilePath,
			vcvarsArch,
			winSdkArg,
			storeArg,
			"&",
			"set",
		]

		_, output, _ = commands.Run([x for x in cmd if x], stdout=_noLogOnRun, stderr=_noLogOnRun)

		# Strip out the \r characters.
		output = output.replace("\r", "")

		assert not output.startswith("!ERROR!"), output.split("\n", 1)[0]

		return Vcvarsall.Create(output)


@MetaClass(ABCMeta)
class MsvcToolBase(Tool):
	"""
	Parent class for all msvc tools.

	:param projectSettings: A read-only scoped view into the project settings dictionary
	:type projectSettings: toolchain.ReadOnlySettingsView
	"""
	def __init__(self, projectSettings):
		Tool.__init__(self, projectSettings)

		self._vsVersion = projectSettings.get("vsVersion", None)
		self._winSdkVersion = projectSettings.get("winSdkVersion", None)
		self._msvcSubsystem = projectSettings.get("msvcSubsystem", None)
		self._msvcSubsystemVersion = projectSettings.get("msvcSubsystemVersion", None)

		self._vcvarsall = None
		self._selectedInstall = None
		self._allInstalls = []
		self._enableUwp = False


	@property
	def vsVersion(self):
		"""
		:return: Returns the Visual Studio version number.
		:rtype: str
		"""
		return self._vsVersion


	@property
	def winSdkVersion(self):
		"""
		:return: Returns the Windows SDK version number.
		:rtype: str
		"""
		return self._winSdkVersion

	@property
	def msvcSubsystem(self):
		"""
		:return: Returns the MSVC linker subsystem argument.
		:rtype: str
		"""
		return self._msvcSubsystem


	@property
	def msvcSubsystemVersion(self):
		"""
		:return: Returns the version number to use with the subsystem argument.
		:rtype: tuple[int, int]
		"""
		return self._msvcSubsystemVersion


	@property
	def vcvarsall(self):
		"""
		:return: Returns the Vcvarsall instance.
		:rtype: :class:`csbuild.tools.common.msvc_tool_base.Vcvarsall`
		"""
		return self._vcvarsall


	@staticmethod
	@TypeChecked(version=str)
	def SetVisualStudioVersion(version):
		"""
		Set the version of Visual Studio to use.

		:param version: Visual studio version
			"10" => Visual Studio 2010
			"11" => Visual Studio 2012
			"12" => Visual Studio 2013
			"14" => Visual Studio 2015
			"15" => Visual Studio 2017
			"16" => Visual Studio 2019
		:type version: str
		"""
		csbuild.currentPlan.SetValue("vsVersion", version)


	@staticmethod
	@TypeChecked(version=str)
	def SetWindowsSdkVersion(version):
		"""
		Set the Windows SDK version to build against (only applies to Visual Studio "14.0" and up).

		:param version: Windows SDK version (e.g., "8.1", "10.0.15063.0", etc)
		:type version: str
		"""
		csbuild.currentPlan.SetValue("winSdkVersion", version)


	@staticmethod
	@TypeChecked(subsystem=str)
	def SetMsvcSubsystem(subsystem):
		"""
		Set the MSVC linker subsystem argument.

		:param subsystem: MSVC linker subsystem argument.
		:type subsystem: str
		"""
		csbuild.currentPlan.SetValue("msvcSubsystem", subsystem)


	@staticmethod
	@TypeChecked(major=int, minor=int)
	def SetMsvcSubsystemVersion(major, minor):
		"""
		Set the version number to use with the subsystem argument.

		:param major: Subsystem major version.
		:type major: int

		:param minor: Subsystem minor version.
		:type minor: int
		"""
		if isinstance(major, int) and isinstance(minor, int):
			csbuild.currentPlan.SetValue("msvcSubsystemVersion", (major, minor))


	def SetupForProject(self, project):
		Tool.SetupForProject(self, project)
		currentArch = csbuild.GetSystemArchitecture()
		supportedSystemArchs = {
			"x86",
			"x64",
			"arm",
		}

		# Msvc can only be run from a certain set of supported architectures.
		assert currentArch in supportedSystemArchs, \
			'Invalid system architecture "{}"; msvc tools can only be run on the following architectures: {}'.format(currentArch, supportedSystemArchs)

		# The argument values here are directly used by vcvarsall.bat prior to Visual Studio 2017,
		# however we still use them internally for mapping the environment data for the selected
		# version of Visual Studio and determining valid build targets.
		args = {
			"x64": {
				"x64": "amd64",
				"x86": "amd64_x86",
				"arm": "amd64_arm",
			},
			"x86": {
				"x64": "x86_amd64",
				"x86": "x86",
				"arm": "x86_arm",
			},
			"arm": {
				"x64": None,
				"x86": None,
				"arm": "arm",
			},
		}

		vcvarsArch = args[currentArch][project.architectureName]

		assert vcvarsArch is not None, "Building for {} on {} is unsupported.".format(project.architectureName, currentArch)

		# Only run vcvarsall.bat if we haven't already for the selected architecture.
		if vcvarsArch not in Vcvarsall.Instances:
			archInfo = _ArchitectureInfo(currentArch, project.architectureName, vcvarsArch, self._winSdkVersion, self._enableUwp)

			self._findInstallations()
			self._setupEnvironment(archInfo)

		# Retrieve the memoized data.
		self._vcvarsall = Vcvarsall.Instances[vcvarsArch]


	def _findInstallations(self):
		if not self._allInstalls:
			post2017Installs = _InstallDataPost2017.FindInstallations()
			pre2017Installs = _InstallDataPre2017.FindInstallations()

			# The installs should be sorted newest to oldest, so make sure the
			# post-2017 installs come before the pre-2017 installs.
			self._allInstalls = post2017Installs + pre2017Installs


	def _setupEnvironment(self, archInfo):
		vcvarsall = None

		if not self._selectedInstall:
			installsToCheck = []

			for installData in self._allInstalls:
				log.Info("Found installation for {}".format(installData.displayName))

				if self._vsVersion:
					# Only consider installs matching the version provided by the user.
					if str(installData.version) == self._vsVersion:
						installsToCheck.append(installData)
				else:
					# No version provided by the user, so consider all installs.
					installsToCheck.append(installData)

			# Make sure we actually have something to check.
			assert installsToCheck, \
				"No installations of Visual Studio were detected{}.".format(
					" matching version {}".format(self._vsVersion) if self._vsVersion else ""
				)

			# Use the first install that provides valid environment data.
			for installData in installsToCheck:
				vcvarsall = installData.GetEnvironment(archInfo)

				if vcvarsall:
					self._selectedInstall = installData
					log.Build(
						"Building for {}{}".format(
							self._selectedInstall.displayName,
							" using Windows SDK {}".format(vcvarsall.winSdkVersion) if vcvarsall.winSdkVersion else ""
						)
					)
					break

		else:
			# A version of Visual Studio has already been selected, so get its environment data for the current architecture.
			vcvarsall = self._selectedInstall.GetEnvironment(archInfo)

		# Make sure the environment data is valid.
		assert vcvarsall, \
			"Failed to get environment data for {} (version {}).".format(
				self._selectedInstall.displayName,
				self._selectedInstall.version
			)

		Vcvarsall.Instances[archInfo.vcvarsArch] = vcvarsall
