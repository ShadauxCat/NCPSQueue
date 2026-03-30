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
	:synopsis: Test to make sure that invalid toolchain/architecture/platform/target combinations all function as expected

.. moduleauthor:: Jaedyn K. Draper
"""

from __future__ import unicode_literals, division, print_function

from csbuild._testing.functional_test import FunctionalTest
from csbuild import log
import platform
import os

class ToolchainArchitectureTest(FunctionalTest):
	"""Test combinations of toolchains, architectures, platforms, and targets"""
	# pylint: disable=invalid-name
	def setUp(self): # pylint: disable=arguments-differ
		FunctionalTest.setUp(self, cleanAtEnd=False)

	def tearDown(self):
		if os.path.exists("out"):
			for filename in os.listdir("out"):
				os.remove(os.path.join("out", filename))
			os.rmdir("out")
		FunctionalTest.tearDown(self)

	def testValidCombinations(self):
		"""Test various combinations, they should all succeed"""
		for toolchain in ["A", "B", "C", "D", platform.system()]:
			for target in ["A", "B", "special"]:
				for architecture in ["A", "B", "C", "D", "E"]:
					if architecture == "E" and toolchain != "D":
						continue

					self.assertMakeSucceeds("--toolchain", toolchain, "--target", target, "--architecture", architecture, "-v")
					log.Test("Created {}", os.listdir("out"))

					if target != "special":
						self.assertTrue(os.path.exists("out/foo.{}.{}.{}".format(architecture, target, toolchain)))
						os.remove("out/foo.{}.{}.{}".format(architecture, target, toolchain))

						if architecture in ["A", "B", "C"]:
							self.assertTrue(os.path.exists("out/arch.{}.{}.{}".format(architecture, target, toolchain)))
							os.remove("out/arch.{}.{}.{}".format(architecture, target, toolchain))
							self.assertTrue(os.path.exists("out/arch2.{}.{}.{}".format(architecture, target, toolchain)))
							os.remove("out/arch2.{}.{}.{}".format(architecture, target, toolchain))

						if target == "A":
							self.assertTrue(os.path.exists("out/target.{}.{}.{}".format(architecture, target, toolchain)))
							os.remove("out/target.{}.{}.{}".format(architecture, target, toolchain))
							self.assertTrue(os.path.exists("out/target2.{}.{}.{}".format(architecture, target, toolchain)))
							os.remove("out/target2.{}.{}.{}".format(architecture, target, toolchain))

						self.assertTrue(os.path.exists("out/unspecial.{}.{}.{}".format(architecture, target, toolchain)))
						os.remove("out/unspecial.{}.{}.{}".format(architecture, target, toolchain))

						if toolchain in ["B", "C", "D"]:
							self.assertTrue(os.path.exists("out/toolchain.{}.{}.{}".format(architecture, target, toolchain)))
							os.remove("out/toolchain.{}.{}.{}".format(architecture, target, toolchain))
							self.assertTrue(os.path.exists("out/toolchain2.{}.{}.{}".format(architecture, target, toolchain)))
							os.remove("out/toolchain2.{}.{}.{}".format(architecture, target, toolchain))

						self.assertTrue(os.path.exists("out/{}.{}.{}.{}".format(platform.system(), architecture, target, toolchain)))
						os.remove("out/{}.{}.{}.{}".format(platform.system(), architecture, target, toolchain))
						self.assertTrue(os.path.exists("out/{}2.{}.{}.{}".format(platform.system(), architecture, target, toolchain)))
						os.remove("out/{}2.{}.{}.{}".format(platform.system(), architecture, target, toolchain))

					else:
						self.assertTrue(os.path.exists("out/special.{}.{}.{}".format(architecture, target, toolchain)))
						os.remove("out/special.{}.{}.{}".format(architecture, target, toolchain))
						self.assertTrue(os.path.exists("out/special2.{}.{}.{}".format(architecture, target, toolchain)))
						os.remove("out/special2.{}.{}.{}".format(architecture, target, toolchain))

					self.assertFalse(os.listdir("out"), "Out directory still contains {}".format(os.listdir("out")))

					self.assertMakeSucceeds("--toolchain", toolchain, "--target", target, "--architecture", architecture, "--clean")

	def testInvalidCombination(self):
		"""Test an invalid combination to make sure csbuild doesn't try to build when there are no valid projects for the given combination"""
		self.assertMakeFails(
			"No projects were found supporting the requested architecture, toolchain, target, and platform combination",
			"--toolchain", "A", "--target", "B", "--architecture", "E"
		)
