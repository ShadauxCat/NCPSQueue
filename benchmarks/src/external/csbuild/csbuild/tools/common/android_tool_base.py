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
.. module:: android_tool_base
	:synopsis: Abstract base class for Android tools.

.. moduleauthor:: Zoe Bare
"""

from __future__ import unicode_literals, division, print_function

import csbuild
import glob
import os
import platform

from abc import ABCMeta

from ..._utils.decorators import MetaClass
from ...toolchain import Tool

@MetaClass(ABCMeta)
class AndroidStlLibType(object):
	"""
	Enum values for selecting the type of STL library linked into Android projects.
	"""
	Gnu = "gnu-libstdc++"
	LibCpp = "libc++"
	StlPort = "stlport"

class AndroidInfo(object):
	"""
	Collection of paths for a specific version of Android and architecture.

	:param gccToolchainRootPath: Full path the root directory containing the gcc toolchain.
	:type gccToolchainRootPath: str

	:param gccPath: Full path to the gcc executable.
	:type gccPath: str

	:param gppPath: Full path to the g++ executable.
	:type gppPath: str

	:param asPath: Full path to the as executable.
	:type asPath: str

	:param ldPath: Full path to the ld executable.
	:type ldPath: str

	:param arPath: Full path to the ar executable.
	:type arPath: str

	:param clangPath: Full path to the clang executable.
	:type clangPath: str

	:param clangppPath: Full path to the clang++ executable.
	:type clangppPath: str

	:param zipAlignPath: Full path to the zipAlign executable.
	:type zipAlignPath: str

	:param sysRootPath: Full path to the Android system root.
	:type sysRootPath: str

	:param systemLibPath: Full path to the Android system libraries.
	:type systemLibPath: str

	:param systemIncludePaths: List of full paths to the Android system headers.
	:type systemIncludePaths: list[str]

	:param nativeAppGluPath: Full path to the Android native glue source and header files.
	:type nativeAppGluPath: str

	:param stlLibName: Basename of the STL library to link against.
	:type stlLibName: str

	:param stlLibPath: Full path to the STL libraries.
	:type stlLibPath: str

	:param stlIncludePaths: List of full paths to the STL headers.
	:type stlIncludePaths: list[str]
	"""
	Instances = {}

	def __init__(
		self,
		gccToolchainRootPath,
		gccPath,
		gppPath,
		asPath,
		ldPath,
		arPath,
		clangPath,
		clangppPath,
		zipAlignPath,
		sysRootPath,
		systemLibPath,
		systemIncludePaths,
		nativeAppGluPath,
		stlLibName,
		stlLibPath,
		stlIncludePaths,
	):
		self.gccToolchainRootPath = gccToolchainRootPath
		self.gccPath = gccPath
		self.gppPath = gppPath
		self.asPath = asPath
		self.ldPath = ldPath
		self.arPath = arPath
		self.clangPath = clangPath
		self.clangppPath = clangppPath
		self.zipAlignPath = zipAlignPath
		self.sysRootPath = sysRootPath
		self.systemLibPath = systemLibPath
		self.systemIncludePaths = [path for path in systemIncludePaths if path]
		self.nativeAppGluPath = nativeAppGluPath
		self.stlLibName = stlLibName
		self.stlLibPath = stlLibPath
		self.stlIncludePaths = [path for path in stlIncludePaths if path]


@MetaClass(ABCMeta)
class AndroidToolBase(Tool):
	"""
	Parent class for all tools targetting Android platforms.

	:param projectSettings: A read-only scoped view into the project settings dictionary
	:type projectSettings: toolchain.ReadOnlySettingsView
	"""
	supportedArchitectures = { "x86", "x64", "arm", "arm64", "mips", "mips64" }

	def __init__(self, projectSettings):
		Tool.__init__(self, projectSettings)

		self._androidNdkRootPath = projectSettings.get("androidNdkRootPath", "")
		self._androidSdkRootPath = projectSettings.get("androidSdkRootPath", "")
		self._androidManifestFilePath = projectSettings.get("androidManifestFilePath", "")
		self._androidTargetSdkVersion = projectSettings.get("androidTargetSdkVersion", None)
		self._androidStlLibType = projectSettings.get("androidStlLibType", None)
		self._androidNativeAppGlue = projectSettings.get("androidNativeAppGlue", False)

		# If no NDK root path is specified, try to get it from the environment.
		if not self._androidNdkRootPath and "ANDROID_NDK_ROOT" in os.environ:
			self._androidNdkRootPath = os.environ["ANDROID_NDK_ROOT"]

		# If no SDK root path is specified, try to get it from the environment.
		if not self._androidSdkRootPath and "ANDROID_HOME" in os.environ:
			self._androidSdkRootPath = os.environ["ANDROID_HOME"]

		assert self._androidNdkRootPath, "No Android NDK root path provided"
		assert self._androidSdkRootPath, "No Android SDK root path provided"
		assert self._androidTargetSdkVersion, "No Android target SDK version provided"

		assert os.access(self._androidNdkRootPath, os.F_OK), "Android NDK root path does not exist: {}".format(self._androidNdkRootPath)
		assert os.access(self._androidSdkRootPath, os.F_OK), "Android SDK root path does not exist: {}".format(self._androidSdkRootPath)

		self._androidInfo = None

	####################################################################################################################
	### Private methods
	####################################################################################################################

	def _getInfo(self, arch):
		key = (self._androidNdkRootPath, self._androidSdkRootPath, arch)

		if key not in AndroidInfo.Instances:
			def _getToolchainPrefix():
				# Search for a toolchain by architecture.
				toolchainArchPrefix = {
					"x86": "x86",
					"x64": "x86_64",
					"arm": "arm",
					"arm64": "aarch64",
					"mips": "mipsel",
					"mips64": "mips64el",
				}.get(arch, "")
				assert toolchainArchPrefix, "Android architecture not supported: {}".format(arch)
				return toolchainArchPrefix

			def _getStlArchName():
				stlArchName = {
					"x86": "x86",
					"x64": "x86_64",
					"arm": "armeabi-v7a",
					"arm64": "arm64-v8a",
					"mips": "mips",
					"mips64": "mips64",
				}.get(arch, "")
				assert stlArchName, "Android architecture not supported: {}".format(arch)
				return stlArchName

			def _getIncludeArchName():
				# Search for a toolchain by architecture.
				includeArchName = {
					"x86": "i686-linux-android",
					"x64": "x86_64-linux-android",
					"arm": "arm-linux-androideabi",
					"arm64": "aarch64-linux-android",
					"mips": "mipsel-linux-android",
					"mips64": "mips64el-linux-android",
				}.get(arch, "")
				assert includeArchName, "Android architecture not supported: {}".format(arch)
				return includeArchName

			# Certain architectures must use the "lib64" directory instead of "lib".
			useLib64 = {
				"x64": True,
				"mips64": True,
			}.get(arch, False)

			platformName = platform.system().lower()
			exeExtension = ".exe" if platform.system() == "Windows" else ""
			toolchainPrefix = _getToolchainPrefix()
			rootToolchainPath = os.path.join(self._androidNdkRootPath, "toolchains")
			archToolchainRootPath = glob.glob(os.path.join(rootToolchainPath, "{}-*".format(toolchainPrefix)))
			llvmToolchainRootPath = glob.glob(os.path.join(rootToolchainPath, "llvm", "prebuilt", "{}-*".format(platformName)))
			stlArchName = _getStlArchName()
			stlRootPath = os.path.join(self._androidNdkRootPath, "sources", "cxx-stl")
			sysRootPath = os.path.join(self._androidNdkRootPath, "platforms", "android-{}".format(self._androidTargetSdkVersion), self._getPlatformArchName(arch))
			sysRootLibPath = os.path.join(sysRootPath, "usr", "lib64" if useLib64 else "lib")
			sysRootBaseIncludePath = os.path.join(self._androidNdkRootPath, "sysroot", "usr", "include")
			sysRootArchIncludePath = os.path.join(sysRootBaseIncludePath, _getIncludeArchName())
			androidSourcesRootPath = os.path.join(self._androidNdkRootPath, "sources", "android")
			androidSupportIncludePath = os.path.join(androidSourcesRootPath, "support", "include")
			nativeAppGluePath = os.path.join(androidSourcesRootPath, "native_app_glue")

			assert archToolchainRootPath, "No Android toolchain installed for architecture: {}".format(arch)
			assert llvmToolchainRootPath, "No Android LLVM toolchain installed for platform: {}".format(platformName)
			assert os.access(sysRootPath, os.F_OK), "No Android sysroot found at path: {}".format(sysRootPath)

			archToolchainRootPath = archToolchainRootPath[0]

			gccVersionStartIndex = archToolchainRootPath.rfind("-")
			assert gccVersionStartIndex > 0, "Android GCC version not parsable from path: {}".format(archToolchainRootPath)

			# Save the gcc version since we'll need it for getting the libstdc++ paths.
			gccVersion = archToolchainRootPath[gccVersionStartIndex + 1:]

			archToolchainRootPath = glob.glob(os.path.join(archToolchainRootPath, "prebuilt", "{}-*".format(platformName)))
			assert archToolchainRootPath, "No Android \"{}\" toolchain installed for platform: {}".format(toolchainPrefix, platformName)

			archToolchainRootPath = archToolchainRootPath[0]
			llvmToolchainRootPath = llvmToolchainRootPath[0]

			archToolchainIncludePath = glob.glob(os.path.join(archToolchainRootPath, "lib", "gcc", "*", "*", "include"))
			archToolchainIncludePath = archToolchainIncludePath[0] if archToolchainIncludePath else ""

			archToolchainBinPath = os.path.join(archToolchainRootPath, "bin")
			llvmToolchainBinPath = os.path.join(llvmToolchainRootPath, "bin")

			# Get the compiler and linker paths.
			gccPath = glob.glob(os.path.join(archToolchainBinPath, "*-gcc{}".format(exeExtension)))
			gppPath = glob.glob(os.path.join(archToolchainBinPath, "*-g++{}".format(exeExtension)))
			asPath = glob.glob(os.path.join(archToolchainBinPath, "*-as{}".format(exeExtension)))
			ldPath = glob.glob(os.path.join(archToolchainBinPath, "*-ld{}".format(exeExtension)))
			arPath = glob.glob(os.path.join(archToolchainBinPath, "*-ar{}".format(exeExtension)))
			clangPath = os.path.join(llvmToolchainBinPath, "clang{}".format(exeExtension))
			clangppPath = os.path.join(llvmToolchainBinPath, "clang++{}".format(exeExtension))

			# Do not assert on missing gcc or clang. GCC was deprecated and removed from later versions of the NDK
			# and clang wasn't added until several NDK version in. It will be best if we assert when trying to use
			# their respective toolchains.
			assert asPath, "No Android as executable found for architecture: {}".format(arch)
			assert ldPath, "No Android ld executable found for architecture: {}".format(arch)
			assert arPath, "No Android ar executable found for architecture: {}".format(arch)

			gccPath = gccPath[0] if gccPath else None
			gppPath = gppPath[0] if gppPath else None
			asPath = asPath[0]
			ldPath = ldPath[0]
			arPath = arPath[0]

			buildToolsPath = glob.glob(os.path.join(self._androidSdkRootPath, "build-tools", "*"))
			assert buildToolsPath, "No Android build tools are installed"

			# For now, it doesn't seem like we need a specific version, so just pick the first one.
			buildToolsPath = buildToolsPath[0]

			# Get the miscellaneous build tool paths.
			zipAlignPath = os.path.join(buildToolsPath, "zipalign{}".format(exeExtension))

			assert os.access(zipAlignPath, os.F_OK), "ZipAlign not found in Android build tools path: {}".format(buildToolsPath)

			# If an STL flavor has been specified, attempt to get its include & lib paths.
			if self._androidStlLibType:
				stlLibName = {
					AndroidStlLibType.Gnu: "libgnustl",
					AndroidStlLibType.LibCpp: "libc++",
					AndroidStlLibType.StlPort: "libstlport",
				}.get(self._androidStlLibType, None)
				assert stlLibName, "Invalid Android STL type: {}".format(self._androidStlLibType)

				stlLibDirName = {
					AndroidStlLibType.Gnu: "gnu-libstdc++",
					AndroidStlLibType.LibCpp: "llvm-libc++",
					AndroidStlLibType.StlPort: "stlport",
				}.get(self._androidStlLibType, None)
				assert stlLibName, "Invalid Android STL type: {}".format(self._androidStlLibType)

				stlRootPath = os.path.join(stlRootPath, stlLibDirName)

				# libstdc++ exists in a sub-directory indicating its version.
				if self._androidStlLibType == AndroidStlLibType.Gnu:
					stlRootPath = os.path.join(stlRootPath, gccVersion)

				assert os.access(stlRootPath, os.F_OK), "Android STL \"{}\" not found at path: {}".format(self._androidStlLibType, stlRootPath)

				stlLibPath = os.path.join(stlRootPath, "libs", stlArchName)
				stlIncludePaths = [
					os.path.join(stlRootPath, "include"),
				]

				# For some reason "gnu-libstdc++" thought it was a good idea to put includes under its library directory.
				if self._androidStlLibType == AndroidStlLibType.Gnu:
					stlIncludePaths.append(
						os.path.join(stlLibPath, "include"),
					)

			else:
				# No STL, just use dummy values.
				stlLibName = None
				stlLibPath = None
				stlIncludePaths = []

			AndroidInfo.Instances[key] = \
				AndroidInfo(
					archToolchainRootPath,
					gccPath,
					gppPath,
					asPath,
					ldPath,
					arPath,
					clangPath,
					clangppPath,
					zipAlignPath,
					sysRootPath,
					sysRootLibPath,
					[
						sysRootBaseIncludePath,
						sysRootArchIncludePath,
						archToolchainIncludePath,
						androidSupportIncludePath,
					],
					nativeAppGluePath,
					stlLibName,
					stlLibPath,
					stlIncludePaths,
				)

		return AndroidInfo.Instances[key]

	def _getPlatformArchName(self, arch):
		platformArchName = {
			"x86": "arch-x86",
			"x64": "arch-x86_64",
			"arm": "arch-arm",
			"arm64": "arch-arm64",
			"mips": "arch-mips",
			"mips64": "arch-mips64",
		}.get(arch, "")
		assert platformArchName, "Architecture platform name not found for: {}".format(arch)
		return platformArchName

	def _getBuildArchName(self, arch):
		# Only ARM needs a build architecture name.
		name = {
			"arm": "armv7-a",
			"arm64": "armv8-a",
		}.get(arch, "")
		return name

	def _getTargetTripleName(self, arch):
		targetTriple = {
			"x86": "i686-none-linux-android",
			"x64": "x86_64-none-linux-android",
			"arm": "armv7-none-linux-androideabi",
			"arm64": "aarch64-none-linux-android",
			"mips": "mipsel-none-linux-android",
			"mips64": "mips64el-none-linux-android",
		}.get(arch, "")
		assert targetTriple, "Architecture target triple not defined for: {}".format(arch)
		return targetTriple

	def _getDefaultLinkerArgs(self):
		return [
			"-Wl,--no-undefined",
			"-Wl,--no-allow-shlib-undefined",
			"-Wl,--unresolved-symbols=report-all",
			"-Wl,-z,noexecstack",
			"-Wl,-z,relro",
			"-Wl,-z,now",
		]

	def _getDefaultCompilerArgs(self):
		return [
			"-funwind-tables",
			"-fstack-protector",
			"-fno-omit-frame-pointer",
			"-fno-strict-aliasing",
			"-fno-short-enums",
			"-Wa,--noexecstack",
		]

	####################################################################################################################
	### Methods implemented from base classes
	####################################################################################################################

	def SetupForProject(self, project):
		"""
		Run project setup, if any, before building the project, but after all dependencies have been resolved.

		:param project: project being set up
		:type project: csbuild._build.project.Project
		"""
		Tool.SetupForProject(self, project)

		if not self._androidInfo:
			self._androidInfo = self._getInfo(project.architectureName)

	################################################################################
	### Static makefile methods
	################################################################################

	@staticmethod
	def SetAndroidNdkRootPath(path):
		"""
		Sets the path to the Android NDK home.

		:param path: Android NDK home path.
		:type path: str
		"""
		csbuild.currentPlan.SetValue("androidNdkRootPath", os.path.abspath(path) if path else None)

	@staticmethod
	def SetAndroidSdkRootPath(path):
		"""
		Sets the path to the Android SDK root.

		:param path: Android SDK root path.
		:type path: str
		"""
		csbuild.currentPlan.SetValue("androidSdkRootPath", os.path.abspath(path) if path else None)

	@staticmethod
	def SetAndroidManifestFilePath(path):
		"""
		Sets the path to the Android manifest file.

		:param path: Android manifest file path.
		:type path: str
		"""
		csbuild.currentPlan.SetValue("androidManifestFilePath", os.path.abspath(path))

	@staticmethod
	def SetAndroidTargetSdkVersion(version):
		"""
		Sets the Android target SDK version.

		:param version: Android target SDK version.
		:type version: int
		"""
		csbuild.currentPlan.SetValue("androidTargetSdkVersion", version)

	@staticmethod
	def SetAndroidStlLibType(lib):
		"""
		Sets the Android STL lib type.

		:param lib: Android STL lib type.
		:type lib: str
		"""
		csbuild.currentPlan.SetValue("androidStlLibType", lib)

	@staticmethod
	def SetAndroidNativeAppGlue(useDefaultAppGlue):
		"""
		Sets a boolean to use the default Android native app glue.

		:param useDefaultAppGlue: Use default Android native app glue?
		:type useDefaultAppGlue: bool
		"""
		csbuild.currentPlan.SetValue("androidNativeAppGlue", useDefaultAppGlue)
