# Copyright (C) 2013 Jaedyn K. Draper
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
.. module:: compiler_flags
	:synopsis: Abstract base class for tools requiring compiler flags.

.. moduleauthor:: Zoe Bare
"""

# Required to keep lint happy.
from __future__ import unicode_literals, division, print_function

from abc import ABCMeta

from ..._utils.decorators import MetaClass
from ...toolchain import Tool

@MetaClass(ABCMeta)
class CppCompilerFlags(Tool):
	"""
	Helper class to add arbitrary flags to a cpp compiler tool.

	:param projectSettings: A read-only scoped view into the project settings dictionary.
	:type projectSettings: toolchain.ReadOnlySettingsView
	"""
	def __init__(self, projectSettings):
		Tool.__init__(self, projectSettings)
		self._cFlags = []
		self._cxxFlags = []

	def AddCFlags(self, *flags):
		"""
		Add C flags to the compiler (only applies to C files).

		:param flags: Flags to pass to the compiler.
		:type flags: any
		"""
		self._cFlags += list(flags)

	def AddCxxFlags(self, *flags):
		"""
		Add CXX flags to the compiler (only applies to C++ files).

		:param flags: Flags to pass to the compiler.
		:type flags: any
		"""
		self._cxxFlags += list(flags)
