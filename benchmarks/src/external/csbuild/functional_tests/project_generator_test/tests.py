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
.. module:: tests
	:synopsis: Basic test of tools to make sure simple tools chain together properly

.. moduleauthor:: Jaedyn K. Draper
"""

from __future__ import unicode_literals, division, print_function

import os
import shutil

from csbuild._testing.functional_test import FunctionalTest

class SolutionGenerationTest(FunctionalTest):
	"""Basic tool test"""
	def setUp(self): # pylint: disable=arguments-differ
		FunctionalTest.setUp(self, cleanAtEnd=False)

	def tearDown(self):
		shutil.rmtree("./Solutions")
		FunctionalTest.tearDown(self)

	# pylint: disable=invalid-name
	def testSolutionGenerationWorks(self):
		"""Basic solution generation test"""
		self.assertMakeSucceeds("-v", "--generate-solution", "DummyGenerator", "--all-targets")

		targets = ["debug", "fastdebug", "release"]

		self.assertFileExists("./Solutions/DummyGenerator/csbuild.sln")
		with open("./Solutions/DummyGenerator/csbuild.sln") as f:
			contents = f.read()

		for target in targets:
			expectedContents = os.path.abspath("./Solutions/DummyGenerator/Foo_{}.proj".format(target))
			self.assertIn(expectedContents, contents)

		for target in targets:
			projectFile = "./Solutions/DummyGenerator/Foo_{}.proj".format(target)
			self.assertFileExists(projectFile)
			with open(projectFile) as f:
				contents = f.read().splitlines()
			for i in range(1, 11):
				self.assertIn(os.path.abspath("./firsts/{}.first".format(i)), contents)

			self.assertFileDoesNotExist("./out/Foo.third")
			for i in range(1, 11):
				self.assertFileDoesNotExist("./intermediate/{}.second".format(i))

	def testCleanDoesntRemoveSolutionDir(self):
		"""Tests that cleaning doesn't delete solution files"""
		self.assertMakeSucceeds("-v", "--generate-solution", "DummyGenerator")
		self.assertMakeSucceeds("-v", "--clean")
		self.assertMakeSucceeds("-v", "--generate-solution", "DummyGenerator", "--clean")

		self.assertFileContents("./Solutions/DummyGenerator/csbuild.sln", os.path.abspath("./Solutions/DummyGenerator/Foo_release.proj"))

		self.assertFileExists("./Solutions/DummyGenerator/Foo_release.proj")
		with open("./Solutions/DummyGenerator/Foo_release.proj") as f:
			contents = f.read().splitlines()
		for i in range(1, 11):
			self.assertIn(os.path.abspath("./firsts/{}.first".format(i)), contents)

		self.assertFileDoesNotExist("./out/Foo.third")
		for i in range(1, 11):
			self.assertFileDoesNotExist("./intermediate/{}.second".format(i))
