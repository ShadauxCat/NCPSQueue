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
.. module:: recompile
	:synopsis: Utility functions for checking recompilability of a file or files
"""

from __future__ import unicode_literals, division, print_function

import os

from . import project
from .._utils import ordered_set, shared_globals, PlatformString
from ..toolchain import CompileChecker
from .._utils.decorators import TypeChecked
from .. import perf_timer, log

def CheckCompilabilityForFile(buildProject, checker, inputFile, valueMemo, allDeps):
	"""
	Check compatibility for a single file

	:param buildProject: Project being filtered
	:type buildProject: project.Project
	:param checker: Checker
	:type checker: CompileChecker
	:param inputFile: Input file to check
	:type inputFile: str
	:param valueMemo: memo to collect memoized values from
	:type valueMemo: dict
	:param allDeps: All processed dependencies for a given set of checked files used to avoid redundant processing when there are recursive includes.
	:type allDeps: set[str]
	:return: A value with a blocking Get() and not-blocking TryGet()
	:rtype: any
	"""
	if inputFile in valueMemo:
		return valueMemo[inputFile]

	with perf_timer.PerfTimer("Non-memoized compilability check"):
		values = [checker.GetRecompileValue(buildProject, inputFile)]

		deps = {os.path.abspath(PlatformString(f)) for f in checker.GetDependencies(buildProject, inputFile)}
		deps -= allDeps
		if not deps:
			return values[0]

		# When using cached dependencies, some files may no longer exist. Such cases should be seen by the user as
		# an error during compilation, not an obscure Python exception because we're trying to check its timestamp.
		deps = {f for f in deps if os.access(f, os.F_OK)}

		allDeps.update(deps)
		values.extend([CheckCompilabilityForFile(buildProject, checker, dep, valueMemo, allDeps) for dep in deps])

		value = checker.CondenseRecompileChecks(values)
		valueMemo[inputFile] = value
		return value

@TypeChecked(buildProject=project.Project, checker=CompileChecker, inputFiles=ordered_set.OrderedSet)
def ShouldRecompile(buildProject, checker, inputFiles):
	"""
	Determine whether or not a file or list of files should be recompiled.

	:param buildProject: Project being filtered
	:type buildProject: project.Project
	:param checker: Compile checker to check with
	:type checker: CompileChecker
	:param inputFiles: files to check
	:type inputFiles: ordered_set.OrderedSet[input_file.InputFile]
	:return: True if the list of inputs should be reprocessed, false otherwise
	:rtype: bool
	"""
	with perf_timer.PerfTimer("Filter for recompile"):
		if shared_globals.runMode == shared_globals.RunMode.GenerateSolution:
			# All files should be "compiled" when generating a solution.
			return True
		log.Info("Checking if we should compile {}", inputFiles)
		baseline = checker.GetRecompileBaseline(buildProject, inputFiles)
		if baseline is None:
			return True
		values = [CheckCompilabilityForFile(buildProject, checker, os.path.abspath(PlatformString(f.filename)), checker.memo, set()) for f in inputFiles]

		with perf_timer.PerfTimer("Cross-thread Final Resolution"):
			return checker.ShouldRecompile(checker.CondenseRecompileChecks(values), baseline)
