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
	:synopsis: Basic test of macro formatting to ensure it works correctly, including userData formatting

.. moduleauthor:: Jaedyn K. Draper
"""

from __future__ import unicode_literals, division, print_function

import platform

from csbuild._testing.functional_test import FunctionalTest

class MacroFormattingtest(FunctionalTest):
	"""Macro formatting test"""
	def setUp(self):  #pylint: disable=arguments-differ
		FunctionalTest.setUp(self, outDir="./out/AddDoubles/{}/True".format(platform.system()))

	# pylint: disable=invalid-name
	def test(self):
		"""Macro formatting test"""
		self.assertMakeSucceeds()
		for i in range(1, 11):
			self.assertFileContents("./intermediate/{}.second".format(i), str(i*2))
		self.assertFileContents("{}/Foo.third".format(self.outDir), "110")
