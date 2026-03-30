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
	:synopsis: Test for MultiContexts

.. moduleauthor:: Jaedyn K. Draper
"""

from __future__ import unicode_literals, division, print_function

from csbuild._testing.functional_test import FunctionalTest

class MultiContextTest(FunctionalTest):
	"""Multi context test"""
	# pylint: disable=invalid-name
	def runTest(self, projectName):
		"""Multi context test"""
		self.assertMakeSucceeds("--ao", "--aa", "--at", "--project", projectName)

		for i in range(1, 11):
			# debug/foo - both create this output scheme
			self.assertFileContents("./intermediate/FirstThree/debug/foo/AddDoubles/{}.second".format(i), str(i*2))
			self.assertFileContents("./intermediate/FirstThree/debug/foo/AddDoubles2/{}.second".format(i), str(i*2))
			self.assertFileContents("./intermediate/FirstThree/debug/foo/AddDoubles3/{}.second".format(i), str(i*2))
			self.assertFileContents("./intermediate/FirstThree/debug/foo/AddDoubles4/{}.second".format(i), str(i*2))

			# debug/bar - debug creates this output scheme
			self.assertFileContents("./intermediate/FirstThree/debug/bar/AddDoubles/{}.second".format(i), str(i*2))
			self.assertFileContents("./intermediate/FirstThree/debug/bar/AddDoubles2/{}.second".format(i), str(i*2))
			self.assertFileContents("./intermediate/FirstThree/debug/bar/AddDoubles3/{}.second".format(i), str(i*2))
			self.assertFileContents("./intermediate/FirstThree/debug/bar/AddDoubles4/{}.second".format(i), str(i*2))

			# release/foo - foo creates this output scheme
			self.assertFileContents("./intermediate/FirstThree/release/foo/AddDoubles/{}.second".format(i), str(i*2))
			self.assertFileContents("./intermediate/FirstThree/release/foo/AddDoubles2/{}.second".format(i), str(i*2))
			self.assertFileContents("./intermediate/FirstThree/release/foo/AddDoubles3/{}.second".format(i), str(i*2))
			self.assertFileContents("./intermediate/FirstThree/release/foo/AddDoubles4/{}.second".format(i), str(i*2))

			# release/bar - FirstThree toolchain group creates this output scheme, fourth toolchain will be default
			self.assertFileContents("./intermediate/FirstThree/release/bar/AddDoubles/{}.second".format(i), str(i*2))
			self.assertFileContents("./intermediate/FirstThree/release/bar/AddDoubles2/{}.second".format(i), str(i*2))
			self.assertFileContents("./intermediate/FirstThree/release/bar/AddDoubles3/{}.second".format(i), str(i*2))
			self.assertFileContents("./intermediate/{}.second".format(i), str(i*2))

		#debug/foo - foo forces fooFoo.third output name, LastThree toolchain group creates output directory scheme
		self.assertFileContents("./out/fooFoo.third", "110")
		self.assertFileContents("./out/LastThree/debug/foo/AddDoubles2/fooFoo.third", "110")
		self.assertFileContents("./out/LastThree/debug/foo/AddDoubles3/fooFoo.third", "110")
		self.assertFileContents("./out/LastThree/debug/foo/AddDoubles4/fooFoo.third", "110")

		#debug/bar - AddDoubles forces barFoo.third output name, bar creates output directory scheme
		self.assertFileContents("./out/LastThree/debug/bar/AddDoubles/barFoo.third", "110")
		self.assertFileContents("./out/LastThree/debug/bar/AddDoubles2/Foo.third", "110")
		self.assertFileContents("./out/LastThree/debug/bar/AddDoubles3/Foo.third", "110")
		self.assertFileContents("./out/LastThree/debug/bar/AddDoubles4/Foo.third", "110")

		#release/foo - release creates output directory scheme, foo forces fooFoo.third output name
		self.assertFileContents("./out/LastThree/release/foo/AddDoubles/fooFoo.third", "110")
		self.assertFileContents("./out/LastThree/release/foo/AddDoubles2/fooFoo.third", "110")
		self.assertFileContents("./out/LastThree/release/foo/AddDoubles3/fooFoo.third", "110")
		self.assertFileContents("./out/LastThree/release/foo/AddDoubles4/fooFoo.third", "110")

		#release/bar - release creates output directory scheme, AddDoubles forces barFoo.third output name
		self.assertFileContents("./out/LastThree/release/bar/AddDoubles/barFoo.third", "110")
		self.assertFileContents("./out/LastThree/release/bar/AddDoubles2/Foo.third", "110")
		self.assertFileContents("./out/LastThree/release/bar/AddDoubles3/Foo.third", "110")
		self.assertFileContents("./out/LastThree/release/bar/AddDoubles4/Foo.third", "110")

		self.cleanArgs = ["--ao", "--aa", "--at"]


	def testWithSyntax(self):
		"""Run the test using the 'with' syntax"""
		self.runTest("TestProject")


	def testChaining(self):
		"""Run the test using chained context managers"""
		self.runTest("TestProjectChained")
