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
	:synopsis: Test that null input tools work

.. moduleauthor:: Jaedyn K. Draper
"""

from __future__ import unicode_literals, division, print_function

from csbuild._testing.functional_test import FunctionalTest

class NullInputToolTest(FunctionalTest):
	"""Test of null input tools"""
	# pylint: disable=invalid-name
	def testNullInputToolsWork(self):
		"""Test that null input tools basically work"""
		self.assertMakeSucceeds("--toolchain", "NullInput")
		for i in range(1, 11):
			self.assertFileContents("./intermediate/{}.second".format(i), str(i*2))
		self.assertFileContents("./out/Foo.third", "110")

	def testNullInputToolsWorkWithDependencies(self):
		"""Test that null input tools basically work"""
		self.assertMakeSucceeds("--toolchain", "NullInputWithDepends")
		for i in range(1, 10):
			self.assertFileContents("./intermediate/{}.second".format(i), str(i*2))
		self.assertFileContents("./out/Foo.third", "90")
		self.cleanArgs = ["--toolchain", "NullInputWithDepends"]
