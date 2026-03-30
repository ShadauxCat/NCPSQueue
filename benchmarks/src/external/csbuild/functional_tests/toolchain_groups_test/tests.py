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
	:synopsis: Test for toolchain groups

.. moduleauthor:: Jaedyn K. Draper
"""

from __future__ import unicode_literals, division, print_function

from csbuild._testing.functional_test import FunctionalTest

class ToolchainGroupsTest(FunctionalTest):
	"""Toolchain groups test"""
	# pylint: disable=invalid-name
	def runTest(self, projectName):
		"""Toolchain groups test"""
		self.assertMakeSucceeds("--ao", "-v", "--project", projectName)

		for i in range(1, 11):
			self.assertFileContents("./intermediate/FirstThree/AddDoubles/{}.second".format(i), str(i*2))
			self.assertFileContents("./intermediate/FirstThree/AddDoubles2/{}.second".format(i), str(i*2))
			self.assertFileContents("./intermediate/FirstThree/AddDoubles3/{}.second".format(i), str(i*2))
			self.assertFileContents("./intermediate/{}.second".format(i), str(i*2))

		self.assertFileContents("./out/Foo.third", "110")
		self.assertFileContents("./out/LastThree/AddDoubles2/MiddleFoo.third", "110")
		self.assertFileContents("./out/LastThree/AddDoubles3/MiddleFoo.third", "110")
		self.assertFileContents("./out/LastThree/AddDoubles4/Foo.third", "110")

		self.cleanArgs = ["--ao"]

	def testWithSyntax(self):
		"""Test using the with syntax"""
		self.runTest("TestProject")

	def testChained(self):
		"""Test using chained context managers"""
		self.runTest("TestProjectChained")
