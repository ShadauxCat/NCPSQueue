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
from csbuild._utils import PlatformBytes

import os
import subprocess
import platform
import unittest

@unittest.skipUnless(platform.system() == "Darwin", "Objective-C tests may only run on macOS platforms")
class BasicObjCTest(FunctionalTest):
	"""Basic objective-c test"""

	# pylint: disable=invalid-name
	def setUp(self): # pylint: disable=arguments-differ
		self.outputFile = "out/hello_world"
		outDir = "out"
		FunctionalTest.setUp(self, outDir=outDir)

	def testCompileSucceeds(self):
		"""Test that the project succesfully compiles"""
		self.cleanArgs = ["--project=hello_world"]
		self.assertMakeSucceeds("-v", "--project=hello_world", "--show-commands")

		self.assertTrue(os.access(self.outputFile, os.F_OK))
		out = subprocess.check_output([self.outputFile])

		self.assertEqual(out, PlatformBytes("Hello, World!"))
