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
	:synopsis: Basic test of assembler tools

.. moduleauthor:: Jaedyn K. Draper
"""

from __future__ import unicode_literals, division, print_function

from csbuild._testing.functional_test import FunctionalTest

import os
import unittest

@unittest.skipUnless("ANDROID_NDK_ROOT" in os.environ and "ANDROID_HOME" in os.environ, "ANDROID_NDK_ROOT and/or ANDROID_HOME not defined")
class AndroidTest(FunctionalTest):
	"""Android functional test"""

	# pylint: disable=invalid-name
	def setUp(self): # pylint: disable=arguments-differ
		self.outputFile = "out/hello_world.so"
		outDir = "out"
		FunctionalTest.setUp(self, outDir=outDir)

	def testClangX86CompileSucceeds(self):
		"""Test that the project succesfully compiles"""
		testArgs = ["--project=hello_world", "--arch=x86", "--toolchain=android-clang"]
		self.cleanArgs = testArgs
		self.assertMakeSucceeds("-v", "--show-commands", *testArgs)

		self.assertTrue(os.access(self.outputFile, os.F_OK))

	def testClangX64CompileSucceeds(self):
		"""Test that the project succesfully compiles"""
		testArgs = ["--project=hello_world", "--arch=x64", "--toolchain=android-clang"]
		self.cleanArgs = testArgs
		self.assertMakeSucceeds("-v", "--show-commands", *testArgs)

		self.assertTrue(os.access(self.outputFile, os.F_OK))

	def testClangArmCompileSucceeds(self):
		"""Test that the project succesfully compiles"""
		testArgs = ["--project=hello_world", "--arch=arm", "--toolchain=android-clang"]
		self.cleanArgs = testArgs
		self.assertMakeSucceeds("-v", "--show-commands", *testArgs)

		self.assertTrue(os.access(self.outputFile, os.F_OK))

	def testClangArm64CompileSucceeds(self):
		"""Test that the project succesfully compiles"""
		testArgs = ["--project=hello_world", "--arch=arm64", "--toolchain=android-clang"]
		self.cleanArgs = testArgs
		self.assertMakeSucceeds("-v", "--show-commands", *testArgs)

		self.assertTrue(os.access(self.outputFile, os.F_OK))
