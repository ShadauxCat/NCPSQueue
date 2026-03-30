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
.. module:: gcc_linker
	:synopsis: gcc linker tool for C++, d, asm, etc

.. moduleauthor:: Jaedyn K. Draper
"""

from __future__ import unicode_literals, division, print_function

import os
import platform
import re

import csbuild

from .linker_base import LinkerBase
from ... import commands, log
from ..._utils import ordered_set, response_file, shared_globals

def _ignore(_):
	pass

class GccLinker(LinkerBase):
	"""
	GCC linker tool for c++, d, asm, etc
	"""
	supportedArchitectures = {"x86", "x64", "arm", "arm64"}

	inputGroups = {".o"}
	outputFiles = {"", ".a", ".so"}
	crossProjectDependencies = {".a", ".so"}

	_failRegex = re.compile(R"ld: cannot find -l(.*)")


	####################################################################################################################
	### Methods implemented from base classes
	####################################################################################################################

	def _getOutputFiles(self, project):
		return tuple({ os.path.join(project.outputDir, project.outputName + self._getOutputExtension(project.projectType)) })

	def _getCommand(self, project, inputFiles):
		if project.projectType == csbuild.ProjectType.StaticLibrary:
			cmdExe = self._getArchiverName()
			cmd = ["rcs"] \
				+ self._getOutputFileArgs(project) \
				+ self._getInputFileArgs(inputFiles)
			useResponseFile = self._useResponseFileWithArchiver()
		else:
			cmdExe = self._getBinaryLinkerName()
			cmd = self._getDefaultArgs(project) \
				+ self._getCustomArgs() \
				+ self._getArchitectureArgs(project) \
				+ self._getSystemArgs(project) \
				+ self._getOutputFileArgs(project) \
				+ self._getInputFileArgs(inputFiles) \
				+ self._getLibraryPathArgs(project) \
				+ self._getRpathArgs(project) \
				+ self._getStartGroupArgs() \
				+ self._getLibraryArgs() \
				+ self._getEndGroupArgs()
			useResponseFile = self._useResponseFileWithArchiver()

		if useResponseFile:
			responseFile = response_file.ResponseFile(project, "linker-{}".format(project.outputName), cmd)

			if shared_globals.showCommands:
				log.Command("ResponseFile: {}\n\t{}".format(responseFile.filePath, responseFile.AsString()))

			cmd = [cmdExe, "@{}".format(responseFile.filePath)]

		else:
			cmd = [cmdExe] + cmd
			cmd = [arg for arg in cmd if arg]

		return cmd

	def _findLibraries(self, project, libs):
		ret = {}

		shortLibs = ordered_set.OrderedSet(libs)
		longLibs = []

		for lib in libs:
			if os.access(lib, os.F_OK) and not os.path.isdir(lib):
				abspath = os.path.abspath(lib)
				ret[lib] = abspath
				shortLibs.remove(lib)

			elif os.path.splitext(lib)[1]:
				shortLibs.remove(lib)
				longLibs.append(lib)

		if platform.system() == "Windows":
			nullOut = os.path.join(project.csbuildDir, "null")
		else:
			nullOut = "/dev/null"

		if shortLibs:
			# In most cases this should be finished in exactly two attempts.
			# However, in some rare cases, ld will get to a successful lib after hitting a failure and just give up.
			# -lpthread is one such case, and in that case we have to do this more than twice.
			# However, the vast majority of cases should require only two calls (and only one if everything is -lfoo format)
			# and the vast majority of the cases that require a third pass will not require a fourth... but, everything
			# is possible! Still better than doing a pass per file like we used to.
			while True:
				cmd = [self._getLdName(), "--verbose", "-M", "-o", nullOut] + \
					  ["-L"+path for path in self._getLibrarySearchDirectories()] + \
					  ["-l"+lib for lib in shortLibs] + \
					  ["-l:"+lib for lib in longLibs]
				returncode, out, err = commands.Run(cmd, None, None)
				if returncode != 0:
					lines = err.splitlines()
					moved = False
					for line in lines:
						match = GccLinker._failRegex.match(line)
						if match:
							lib = match.group(1)
							if lib not in shortLibs:
								for errorLine in lines:
									log.Error(errorLine)
								return None
							shortLibs.remove(lib)
							longLibs.append(lib)
							moved = True

					if not moved:
						for line in lines:
							log.Error(line)
						return None

					continue
				break

			matches = []

			try:
				# All bfd linkers should have the link maps showing where libraries load from.  Most linkers will be
				# bfd-based, so first assume that is the output we have and try to parse it.
				loading = False
				inGroup = False
				for line in out.splitlines():
					if line.startswith("LOAD"):
						if inGroup:
							continue
						loading = True
						matches.append(line[5:])
					elif line == "START GROUP":
						inGroup = True
					elif line == "END GROUP":
						inGroup = False
					elif loading:
						break

				assert len(matches) == len(shortLibs) + len(longLibs)
				assert len(matches) + len(ret) == len(libs)

			except AssertionError:
				# Fallback to doing the traditional regex check when the link map check failes.
				# All bfd- and gold-compatible linkers should have this.
				succeedRegex = re.compile("(?:.*ld(?:.exe)?): Attempt to open (.*) succeeded")
				for line in err.splitlines():
					match = succeedRegex.match(line)
					if match:
						matches.append(match.group(1))

				assert len(matches) == len(shortLibs) + len(longLibs)
				assert len(matches) + len(ret) == len(libs)

			for i, lib in enumerate(shortLibs):
				ret[lib] = matches[i]
			for i, lib in enumerate(longLibs):
				ret[lib] = matches[i+len(shortLibs)]
			for lib in libs:
				log.Info("Found library '{}' at {}", lib, ret[lib])

		return ret

	def _getOutputExtension(self, projectType):
		outputExt = {
			csbuild.ProjectType.Application: "",
			csbuild.ProjectType.SharedLibrary: ".so",
			csbuild.ProjectType.StaticLibrary: ".a",
		}.get(projectType, None)

		return outputExt


	####################################################################################################################
	### Internal methods
	####################################################################################################################

	def _getLdName(self):
		return "ld"

	def _getBinaryLinkerName(self):
		return "g++"

	def _getArchiverName(self):
		return "ar"

	def _useResponseFileWithLinker(self):
		return True

	def _useResponseFileWithArchiver(self):
		return True

	def _getDefaultArgs(self, project):
		args = []
		if project.projectType == csbuild.ProjectType.SharedLibrary:
			args.extend([
				"-shared",
				"-fPIC",
			])
		return args

	def _getCustomArgs(self):
		return self._linkerFlags

	def _getOutputFileArgs(self, project):
		outFile = self._getOutputFiles(project)[0]
		if project.projectType == csbuild.ProjectType.StaticLibrary:
			return [outFile]
		return ["-o", outFile]

	def _getInputFileArgs(self, inputFiles):
		return [f.filename for f in inputFiles]

	def _getLibraryPathArgs(self, project):
		_ignore(project)
		args = ["-L{}".format(os.path.dirname(libFile)) for libFile in self._actualLibraryLocations.values()]
		return args

	def _rpathStartsWithVariable(self, rpath):
		return rpath.startswith("$")

	def _getRpathOriginVariable(self):
		return "$ORIGIN"

	def _resolveRpath(self, outDir, rpath):
		if not rpath or rpath.startswith("/usr/lib") or rpath.startswith("/usr/local/lib"):
			return None

		rpath = os.path.normpath(rpath)

		# Do not change any rpath that begins with a variable.
		if not self._rpathStartsWithVariable(rpath):
			absPath = os.path.abspath(rpath)

			# If the RPATH is in the output directory, we can ignore it.
			if absPath == outDir:
				return None

			relPath = os.path.relpath(absPath, outDir)

			# We join the path with the origin variable if it can be formed relative to the output directory.
			if absPath != relPath:
				origin = self._getRpathOriginVariable()
				rpath = os.path.join(origin, relPath)

		return rpath

	def _getRpathArgs(self, project):
		if project.projectType != csbuild.ProjectType.Application:
			return []

		args = [
			"-Wl,--enable-new-dtags",
			"-Wl,-R,{}".format(self._getRpathOriginVariable()),
		]

		rpaths = set()
		outDir = os.path.dirname(self._getOutputFiles(project)[0])

		if project.autoResolveRpaths:
			# Add RPATH arguments for each linked library path.
			for lib in self._actualLibraryLocations.values():
				libDir = os.path.dirname(lib)
				rpath = self._resolveRpath(outDir, libDir)

				if rpath:
					rpaths.add(rpath)

		# Add RPATH arguments for each path specified in the makefile.
		for path in self._rpathDirectories:
			path = self._resolveRpath(outDir, path)

			if path:
				rpaths.add(path)

		# Add each RPATH to the argument list.
		for path in sorted(rpaths):
			args.append("-Wl,-R,{}".format(path))

		return args

	def _getLibraryArgs(self):
		return ["-l:{}".format(os.path.basename(lib)) for lib in self._actualLibraryLocations.values()]

	def _getStartGroupArgs(self):
		return ["-Wl,--no-as-needed", "-Wl,--start-group"]

	def _getEndGroupArgs(self):
		return ["-Wl,--end-group"]

	def _getArchitectureArgs(self, project):
		args = {
			"x86": ["-m32"],
			"x64": ["-m64"],
		}.get(project.architectureName, [])
		return args

	def _getSystemArgs(self, project):
		_ignore(project)
		return []

	def _getLibrarySearchDirectories(self):
		return self._libraryDirectories
