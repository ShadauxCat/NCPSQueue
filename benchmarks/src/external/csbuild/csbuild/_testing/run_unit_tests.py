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
.. module:: run_unit_tests
	:synopsis: Import this file and call RunTests() to run csbuild's unit tests.
		Ensure cwd is one directory above the csbuild package. Do not execute directly, it will fail.
"""

from __future__ import unicode_literals, division, print_function

import sys
import unittest
import fnmatch
import os

from .. import log
from .._utils import shared_globals, terminfo, module_importer
from .._testing import testcase


def RunTests(include, exclude):
	"""
	Run all unit tests.
	Must be executed with current working directory being a directory that contains the csbuild package.

	:param include: Filters to be the only things built
	:type include: list[str]
	:param exclude: Filters to not build
	:type exclude: list[str]
	:return: 0 if successful, 1 if not
	:rtype: int
	"""
	shared_globals.colorSupported = terminfo.TermInfo.SupportsColor()
	shared_globals.showCommands = True
	tests = unittest.defaultTestLoader.discover("csbuild", "*.py", ".")
	for testdir in os.listdir("functional_tests"):
		log.Test("Loading functional tests from {}", testdir)
		if os.path.isdir(os.path.join("functional_tests", testdir)):
			modulepath = os.path.join("functional_tests", testdir, "tests.py")
			if os.access(modulepath, os.F_OK):
				log.Test("Loading {}", modulepath)
				tests.addTest(unittest.defaultTestLoader.loadTestsFromModule(module_importer.load_source("{}_TESTS".format(testdir), modulepath)))
	testRunner = testcase.TestRunner(xmlfile="result.xml", stream=sys.stdout, verbosity=0)

	# Handle filtering:
	# 1) If include has any contents, remove any tests that don't match it
	# 2) Remove any tests that do match the exclude filter
	# 3) Finally, reorder the pylint test to be last in line because it is slow.
	pylinttest = None
	for test in tests:
		# pylint: disable=protected-access
		for test2 in test._tests:
			delIndexes = []
			# pylint: disable=protected-access
			try:
				for idx, test3 in enumerate(test2._tests):
					# pylint: disable=protected-access
					baseId = test3.id().rsplit('.', 2)[1]
					simpleTestId = "{}.{}".format(baseId, test3._testMethodName)
					match = True
					if include:
						match = False
						for inc in include:
							if fnmatch.fnmatch(simpleTestId, inc):
								match = True
						if not match:
							log.Test("Excluding test {} due to no include match", simpleTestId)
							delIndexes.append(idx)
							continue
					for exc in exclude:
						match = True
						if fnmatch.fnmatch(simpleTestId, exc):
							log.Test("Excluding test {} due to exclude match", simpleTestId)
							delIndexes.append(idx)
							match = False
							break

					if not match:
						continue

					if baseId == "TestPylint":
						assert pylinttest is None
						pylinttest = test3
						delIndexes.append(idx)
			except AttributeError:
				continue

			for idx in reversed(delIndexes):
				# pylint: disable=protected-access
				del test2._tests[idx]

	if pylinttest is not None:
		tests.addTest(pylinttest)

	result = testRunner.run(tests)
	return 0 if result.wasSuccessful() else 1
