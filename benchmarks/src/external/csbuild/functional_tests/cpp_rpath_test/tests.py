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
	:synopsis: Testing explicit rpaths with C++ projects

.. moduleauthor:: Zoe Bare
"""

from __future__ import unicode_literals, division, print_function

from csbuild._testing.functional_test import FunctionalTest
from csbuild._utils import PlatformBytes

import os
import platform
import subprocess
import unittest

@unittest.skipIf(platform.system() == "Windows", "Rpath tests not supported on Windows")
class CppRpathTest(FunctionalTest):
	"""C++ rpath test"""

	# pylint: disable=invalid-name
	def setUp(self): # pylint: disable=arguments-differ
		self.outputFile = "out/hello_world"

		FunctionalTest.setUp(self, outDir="out")

	@unittest.skipIf(platform.system() == "Darwin", "GCC test is not supported on macOS")
	def testGccSucceeds(self):
		"""Test that the project succesfully compiles and runs with GCC"""
		self.cleanArgs = ["--at", "--toolchain=gcc", "--project=libhello", "--project=hello_world"]

		self.assertMakeSucceeds("-v", "--toolchain=gcc", "--project=libhello", "--show-commands")
		self.assertMakeSucceeds("-v", "--toolchain=gcc", "--project=hello_world", "--show-commands")

		self.assertTrue(os.access(self.outputFile, os.F_OK))
		out = subprocess.check_output([self.outputFile])

		self.assertEqual(out, PlatformBytes("Hello, World! Goodbye, World!"))

	def testClangSucceeds(self):
		"""Test that the project succesfully compiles and runs with Clang"""
		self.cleanArgs = ["--at", "--toolchain=clang", "--project=libhello", "--project=hello_world"]

		self.assertMakeSucceeds("-v", "--toolchain=clang", "--project=libhello", "--show-commands")
		self.assertMakeSucceeds("-v", "--toolchain=clang", "--project=hello_world", "--show-commands")

		self.assertTrue(os.access(self.outputFile, os.F_OK))
		out = subprocess.check_output([self.outputFile])

		self.assertEqual(out, PlatformBytes("Hello, World! Goodbye, World!"))
