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
	:synopsis: Basic test of C++ tools

.. moduleauthor:: Jaedyn K. Draper
"""

from __future__ import unicode_literals, division, print_function

import unittest

from csbuild._testing.functional_test import FunctionalTest
from csbuild._utils import PlatformBytes

import os
import platform
import re
import subprocess

class CppFeaturesTest(FunctionalTest):
	"""C++ features test"""

	ExplicitDefineIsPresent = "Explicit define is present"
	ImplicitDefineIsPresent = "Implicit define is present"
	NoExplicitDefine = "No explicit define"
	NoImplicitDefine = "No implicit define"

	# pylint: disable=invalid-name
	def setUp(self): # pylint: disable=arguments-differ
		if platform.system() == "Windows":
			self.outputFile = "out/hello_world.exe"
		else:
			self.outputFile = "out/hello_world"
		FunctionalTest.setUp(self)

	def testSetCcLanguageStandard(self):
		"""Test that the correct compiler options are being set."""
		self.cleanArgs = ["--project=cc_standard"]
		_, out, _ = self.assertMakeSucceeds("--show-commands", "--project=cc_standard")

		# MSVC doesn't have a setting for the C language standard.
		if platform.system() != "Windows":
			self.assertIsNot(re.compile(R"-std=c11\s", re.M).search(out), None)

		self.assertTrue(os.access(self.outputFile, os.F_OK))
		out = subprocess.check_output([self.outputFile])

		self.assertEqual(out, PlatformBytes("Hello, world!"))

	def testSetCxxLanguageStandard(self):
		"""Test that the correct compiler options are being set."""
		self.cleanArgs = ["--project=cxx_standard"]
		_, out, _ = self.assertMakeSucceeds("--show-commands", "--project=cxx_standard")

		if platform.system() == "Windows":
			self.assertIsNot(re.compile(R"/std:c\+\+14\s", re.M).search(out), None)
		else:
			self.assertIsNot(re.compile(R"-std=c\+\+14\s", re.M).search(out), None)

		self.assertTrue(os.access(self.outputFile, os.F_OK))
		out = subprocess.check_output([self.outputFile])

		self.assertEqual(out, PlatformBytes("Hello, world!"))

	@unittest.skipUnless(platform.system() == "Windows", "Incremental linking is only available on the MSVC linker")
	def testIncrementalLink(self):
		"""Test that incremental linking is enabled and generating an ILK file."""
		self.cleanArgs = ["--project=incremental_linking", "-o=msvc"]
		_, out, _ = self.assertMakeSucceeds("--show-commands", "--project=incremental_linking", "-o=msvc")

		ilkFilePath = "{}.ilk".format(os.path.splitext(self.outputFile)[0])

		self.assertIsNot(re.compile(R"/INCREMENTAL\s", re.M).search(out), None)
		self.assertIsNot(re.compile(R"/ILK:", re.M).search(out), None)

		self.assertFileExists(self.outputFile)
		self.assertFileExists(ilkFilePath)

		out = subprocess.check_output([self.outputFile])

		self.assertEqual(out, PlatformBytes("Hello, world!"))

	def testDisableSymbolsDisableOptDynamicReleaseRuntime(self):
		"""Test that the correct compiler options are being set."""
		self.cleanArgs = ["--project=hello_world", "--target=nosymbols_noopt_dynamic_release"]
		_, out, _ = self.assertMakeSucceeds("--show-commands", "--project=hello_world", "--target=nosymbols_noopt_dynamic_release")

		if platform.system() == "Windows":
			self.assertIs(re.compile(R"/Z7\s|/Zi\s|/ZI\s", re.M).search(out), None)
			self.assertIsNot(re.compile(R"/Od\s", re.M).search(out), None)
			self.assertIsNot(re.compile(R"/MD\s", re.M).search(out), None)
			self.assertIsNot(re.compile(R"/DIMPLICIT_DEFINE\s", re.M).search(out), None)
		else:
			self.assertIs(re.compile(R"-g\s", re.M).search(out), None)
			self.assertIsNot(re.compile(R"-O0\s", re.M).search(out), None)

		self.assertTrue(os.access(self.outputFile, os.F_OK))
		out = subprocess.check_output([self.outputFile])

		self.assertEqual(out, PlatformBytes("{} - {}".format(CppFeaturesTest.NoExplicitDefine, CppFeaturesTest.ImplicitDefineIsPresent)))

	def testEmbeddedSymbolsSizeOptStaticReleaseRuntime(self):
		"""Test that the correct compiler options are being set."""
		self.cleanArgs = ["--project=hello_world", "--target=embeddedsymbols_sizeopt_static_release"]
		_, out, _ = self.assertMakeSucceeds("--show-commands", "--project=hello_world", "--target=embeddedsymbols_sizeopt_static_release")

		if platform.system() == "Windows":
			self.assertIsNot(re.compile(R"/Z7\s", re.M).search(out), None)
			self.assertIsNot(re.compile(R"/O1\s", re.M).search(out), None)
			self.assertIsNot(re.compile(R"/MT\s", re.M).search(out), None)
			self.assertIsNot(re.compile(R"/DIMPLICIT_DEFINE\s", re.M).search(out), None)
			self.assertIsNot(re.compile(R"/DEXPLICIT_DEFINE\s", re.M).search(out), None)
		else:
			self.assertIsNot(re.compile(R"-g\s", re.M).search(out), None)
			self.assertIsNot(re.compile(R"-Os\s", re.M).search(out), None)

		self.assertTrue(os.access(self.outputFile, os.F_OK))
		out = subprocess.check_output([self.outputFile])

		self.assertEqual(out, PlatformBytes("{} - {}".format(CppFeaturesTest.ExplicitDefineIsPresent, CppFeaturesTest.ImplicitDefineIsPresent)))

	def testExternalSymbolsSpeedOptDynamicDebugRuntime(self):
		"""Test that the correct compiler options are being set."""
		self.cleanArgs = ["--project=hello_world", "--target=externalsymbols_speedopt_dynamic_debug"]
		_, out, _ = self.assertMakeSucceeds("--show-commands", "--project=hello_world", "--target=externalsymbols_speedopt_dynamic_debug")

		if platform.system() == "Windows":
			self.assertIsNot(re.compile(R"/Zi\s", re.M).search(out), None)
			self.assertIsNot(re.compile(R"/O2\s", re.M).search(out), None)
			self.assertIsNot(re.compile(R"/MDd\s", re.M).search(out), None)
			self.assertIsNot(re.compile(R"/DIMPLICIT_DEFINE\s", re.M).search(out), None)
			self.assertIsNot(re.compile(R"/UIMPLICIT_DEFINE\s", re.M).search(out), None)
		elif platform.system() == "Linux":
			self.assertIsNot(re.compile(R"-g\s", re.M).search(out), None)
			self.assertIsNot(re.compile(R"-O2\s", re.M).search(out), None)

		self.assertTrue(os.access(self.outputFile, os.F_OK))
		out = subprocess.check_output([self.outputFile])

		self.assertEqual(out, PlatformBytes("{} - {}".format(CppFeaturesTest.NoExplicitDefine, CppFeaturesTest.NoImplicitDefine)))

	def testExternalPlusSymbolsMaxOptStaticDebugRuntime(self):
		"""Test that the correct compiler options are being set."""
		self.cleanArgs = ["--project=hello_world", "--target=externalplussymbols_maxopt_static_debug"]
		_, out, _ = self.assertMakeSucceeds("--show-commands", "--project=hello_world", "--target=externalplussymbols_maxopt_static_debug")

		if platform.system() == "Windows":
			self.assertIsNot(re.compile(R"/ZI\s", re.M).search(out), None)
			self.assertIsNot(re.compile(R"/Ox\s", re.M).search(out), None)
			self.assertIsNot(re.compile(R"/MTd\s", re.M).search(out), None)
			self.assertIsNot(re.compile(R"/DIMPLICIT_DEFINE\s", re.M).search(out), None)
			self.assertIsNot(re.compile(R"/DEXPLICIT_DEFINE\s", re.M).search(out), None)
			self.assertIsNot(re.compile(R"/UIMPLICIT_DEFINE\s", re.M).search(out), None)
		elif platform.system() == "Linux":
			self.assertIsNot(re.compile(R"-g\s", re.M).search(out), None)
			self.assertIsNot(re.compile(R"-O3\s", re.M).search(out), None)

		self.assertTrue(os.access(self.outputFile, os.F_OK))
		out = subprocess.check_output([self.outputFile])

		self.assertEqual(out, PlatformBytes("{} - {}".format(CppFeaturesTest.ExplicitDefineIsPresent, CppFeaturesTest.NoImplicitDefine)))

	def testCustomOptions(self):
		"""Test that the correct compiler options are being set."""
		self.cleanArgs = ["--project=hello_world", "--target=custom_options"]
		_, out, err = self.assertMakeSucceeds("--show-commands", "--project=hello_world", "--target=custom_options")

		if platform.system() == "Windows":
			self.assertIsNot(re.compile(R"/W4\s", re.M).search(out), None)
			self.assertIsNot(re.compile(R"/STACK:1048576\s", re.M).search(out), None)
			self.assertIn("warning C4101: 'unused': unreferenced local variable", out)
		else:
			self.assertIsNot(re.compile(R"-Wunused-variable\s", re.M).search(out), None)
			self.assertIsNot(re.compile(R"-shared-libgcc\s", re.M).search(out), None)
			self.assertIsNot(re.compile(R"warning: unused variable .unused. \[-Wunused-variable\]").search(err), None)
