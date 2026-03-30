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
.. package:: assemblers
	:synopsis: Built-in assembler tools

.. moduleauthor:: Zoe Bare
"""

from __future__ import unicode_literals, division, print_function

import os
import re

from ... import log, perf_timer
from ..._utils import shared_globals
from ...toolchain import CompileChecker

_includeRegex = re.compile(R'^\s*#\s*include\s+"(\S+)"', re.M)

class AsmCompileChecker(CompileChecker):
	"""
	CompileChecker for assembly files that knows how to get assembly file dependency lists.
	"""
	def __init__(self, assembler):
		CompileChecker.__init__(self)
		self._assembler = assembler

	def GetDependencies(self, buildProject, inputFile):
		"""
		Get a list of dependencies for a file.

		:param buildProject: Project encapsulating the files being built
		:type buildProject: csbuild._build.project.Project
		:param inputFile: The file to check
		:type inputFile: str
		:return: Set of files to depend on
		:rtype: set[str]
		"""
		with perf_timer.PerfTimer("Assembly header dependency resolution"):
			log.Info("Checking header dependencies for {}", inputFile)

			cache = shared_globals.settings.Get("asmHeaderCache", {})
			mtime = os.path.getmtime(inputFile)
			if inputFile in cache:
				if mtime <= cache[inputFile]["mtime"]:
					return cache[inputFile]["result"]

			with open(inputFile, "rb") as f:
				contents = f.read()
				contents = contents.decode("utf-8", "replace")

			ret = set()

			includeDirs = [os.path.dirname(inputFile)] + list(buildProject.toolchain.Tool(self._assembler).GetIncludeDirectories())
			for header in _includeRegex.findall(contents):
				for includeDir in includeDirs:
					maybeHeaderLoc = os.path.join(includeDir, header)
					if os.access(maybeHeaderLoc, os.F_OK) and not os.path.isdir(maybeHeaderLoc):
						ret.add(os.path.normpath(maybeHeaderLoc))
			cache[inputFile] = {"mtime": mtime, "result": ret}
			return ret
