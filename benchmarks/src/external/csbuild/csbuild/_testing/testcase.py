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
.. module:: testcase
	:synopsis: Thin wrapper around python unittest that adds some extra information (mostly logging in setUp)

.. moduleauthor:: Jaedyn K. Draper
"""

from __future__ import unicode_literals, division, print_function

import unittest
import sys
import time
import os

from xml.etree import ElementTree
from xml.dom import minidom


initialized = False


def _init():
	"""Initialize some test environment data"""
	global initialized
	if not initialized:
		from .._utils import shared_globals, terminfo

		initialized = True
		shared_globals.startTime = time.time()

		shared_globals.colorSupported = terminfo.TermInfo.SupportsColor()
		shared_globals.showCommands = True


class _TestContainer(object):
	def __init__(self, className):
		self.className = className
		self.successCount = 0
		self.failureCount = 0


class TestCase(unittest.TestCase):
	"""
	Thin wrapper around python unittest to provide more details on test progress
	"""
	_runTestCases = set()
	_currentTestCase = None # type: _TestContainer
	_totalSuccess = 0
	_totalFail = 0
	_failedTestNames = []

	def __init__(self, methodName):
		super(TestCase, self).__init__(methodName)
		self.success = True
		_init()

	def run(self, result=None):
		"""
		Runs the test suite.

		:param result: optional test result
		:type result: unittest.TestResult
		"""
		from .. import log
		if self.__class__.__name__ not in TestCase._runTestCases:
			TestCase.PrintSingleResult()
			TestCase._runTestCases.add(self.__class__.__name__)
			TestCase._currentTestCase = _TestContainer(self.__class__.__name__)
			log.Test("RUNNING TEST SUITE: <&CYAN>{}</&>", self.__class__.__name__)

		log.Test("   Running test:	 {}.<&CYAN>{}</&> ...", self.__class__.__name__, self._testMethodName)
		unittest.TestCase.run(self, result)
		if self.success:
			log.Test("	  ... <&DGREEN>[</&><&GREEN>Success!</&><&DGREEN>]")
			TestCase._currentTestCase.successCount += 1
			TestCase._totalSuccess += 1
		else:
			log.Test("	  ... <&DRED>[</&><&RED>Failed!</&><&DRED>]")
			TestCase._currentTestCase.failureCount += 1
			TestCase._totalFail += 1
			TestCase._failedTestNames.append("{}.<&CYAN>{}</&>".format(self.__class__.__name__, self._testMethodName))

	def TestName(self):
		"""Get the test method name for this test"""
		return self._testMethodName

	def TestDoc(self):
		"""Get the docstring attached to this test"""
		return self._testMethodDoc

	@staticmethod
	def PrintSingleResult():
		"""
		Print the result of the last test suite, if any have been run
		"""
		from .. import log
		if TestCase._currentTestCase is not None:
			txt = "{} <&GREEN>{}</&> test{} succeeded".format(
				TestCase._currentTestCase.className,
				TestCase._currentTestCase.successCount,
				"s" if TestCase._currentTestCase.successCount != 1 else ""
			)
			if TestCase._currentTestCase.failureCount > 0:
				txt += ", <&RED>{}</&> failed".format(TestCase._currentTestCase.failureCount)
			else:
				txt += "!"
			txt += "\n----------------------------------------------------------------------"
			log.Test(txt)

	@staticmethod
	def PrintOverallResult():
		"""
		Print the overall result of the entire unit test run
		"""
		from .. import log
		txt = "Unit test results: <&GREEN>{}</&> test{} succeeded".format(
			TestCase._totalSuccess,
			"s" if TestCase._totalSuccess != 1 else ""
		)
		if TestCase._totalFail > 0:
			txt += ", <&RED>{}</&> failed".format(TestCase._totalFail)
		else:
			txt += "!"
		if TestCase._totalFail > 0:
			txt += "\nFailed tests:"
			for failedTest in TestCase._failedTestNames:
				txt += "\n\t" + failedTest
		log.Test(txt)


class TestResult(unittest.TextTestResult):
	"""
	Thin wrapper of unittest.TextTestResult to print out a little more info at the start and end of a test run

	:param xmlfile: File to store the result xml data in
	:type xmlfile:
	For the other parameters, see unittest.TextTestResult
	"""
	def __init__(self, stream, descriptions, verbosity, xmlfile=None):
		super(TestResult, self).__init__(stream, descriptions, verbosity)
		self.testList = {}
		self.timer = 0
		self.xmlfile = xmlfile

	def startTestRun(self):
		"""
		Start running the test suite
		"""
		sys.stdout.write("----------------------------------------------------------------------\n")

	def stopTestRun(self):
		"""
		Stop running the test suite
		"""
		TestCase.PrintSingleResult()
		TestCase.PrintOverallResult()
		failureDict = dict(self.failures)
		errorDict = dict(self.errors)
		skipDict = dict(self.skipped)
		root = ElementTree.Element("testsuites")
		add = ElementTree.SubElement

		suites = {}

		for test, testTime in self.testList.items():
			if test.__class__.__name__ not in suites:
				suites[test.__class__.__name__] = {}
			suites[test.__class__.__name__][test] = testTime

		for suiteName, tests in suites.items():
			suiteTime = 0
			for _, testTime in tests.items():
				suiteTime += testTime

			suite = add(
				root,
				"testsuite",
				name = suiteName,
				tests=str(len(self.testList)),
				errors=str(len(errorDict)),
				failures=str(len(failureDict)),
				skipped=str(len(skipDict)),
				time="{:.3f}".format(suiteTime)
			)

			for test, testTime in tests.items():
				case = add(suite, "testcase", classname="{}.{}".format(suiteName, test.TestName()), name=str(test.TestDoc()), time="{:.3f}".format(testTime))
				if test in failureDict:
					add(case, "failure").text = failureDict[test]
				if test in errorDict:
					add(case, "error").text = errorDict[test]
				if test in skipDict:
					add(case, "skipped").text = skipDict[test]
		with open(self.xmlfile, "w") as f:
			f.write(minidom.parseString(ElementTree.tostring(root)).toprettyxml("\t", "\n"))
			f.flush()
			os.fsync(f.fileno())

	def startTest(self, test):
		"""
		Start a single test

		:param test: The test to start
		:type test: TestCase
		"""
		super(TestResult, self).startTest(test)
		if test.__class__.__name__ != "ModuleImportFailure":
			self.timer = time.time()

	def stopTest(self, test):
		"""
		Stop a single test

		:param test: The test to stop
		:type test: TestCase
		"""
		super(TestResult, self).stopTest(test)
		# Python 3.5 changed from ModuleImportFailure to _FailedTest...
		if test.__class__.__name__ not in { "_FailedTest", "ModuleImportFailure" }:
			self.testList[test] = time.time() - self.timer

	def addError(self, test, err):
		# pylint: disable=protected-access

		# Some syntax changes between python 2 and python 3 require us to make separate modules.
		# But the unittest system doesn't know about that and will try to import them. If it does it'll give us
		# this ModuleImportFailure. We have to detect this and selectively ignore it for those specific modules.
		# But ONLY for those modules.

		# Python 3.5 changed from ModuleImportFailure to _FailedTest...
		from .. import log

		super(TestResult, self).addError(test, err)
		log.Error(self.errors[-1][1])
		test.success = False

	def addFailure(self, test, err):
		# pylint: disable=protected-access

		# See comment in addError above
		from .. import log

		super(TestResult, self).addFailure(test, err)
		log.Error(self.failures[-1][1])
		test.success = False

	def printErrors(self):
		"""
		Print errors. (Or in this case, don't. We did it earlier.)
		"""
		pass


class TestRunner(unittest.TextTestRunner):
	"""
	Thin wrapper around TextTestRunner to allow passing an xml file to the result

	:param xmlfile: File to store the result xml data in
	:type xmlfile: str
	For the other parameters, see unittest.TextTestRunner
	"""
	resultclass = TestResult

	def __init__(self, xmlfile, *args, **kwargs):
		super(TestRunner, self).__init__(*args, **kwargs)
		self.xmlfile=xmlfile

	def _makeResult(self):
		return self.resultclass(self.stream, self.descriptions, self.verbosity, self.xmlfile)
