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
.. module:: msvc_uwp_cpp_compiler
	:synopsis: MSVC compiler tool for C++ to build apps for the Universal Windows Platform

.. moduleauthor:: Zoe Bare
"""

from __future__ import unicode_literals, division, print_function

from .msvc_cpp_compiler import MsvcCppCompiler
from ..common.tool_traits import HasWinRtSupport

WinRtSupport = HasWinRtSupport.WinRtSupport

def _ignore(_):
	pass

class MsvcUwpCppCompiler(MsvcCppCompiler, HasWinRtSupport):
	"""
	MSVC UWP compiler tool implementation.
	"""

	def __init__(self, projectSettings):
		MsvcCppCompiler.__init__(self, projectSettings)
		HasWinRtSupport.__init__(self, projectSettings)

		# Enable UWP builds so the base tool setups up the toolchain backend properly.
		self._enableUwp = True


	####################################################################################################################
	### Methods implemented from base classes
	####################################################################################################################

	def _getUwpArgs(self, project, isCpp):
		winrtOption = {
			WinRtSupport.Enabled: "/ZW",
			WinRtSupport.EnabledNoStdLib: "/ZW:nostdlib",
		}.get(self._winrtSupport, None)

		if isCpp and winrtOption:
			return [
				winrtOption,
				"/EHsc",
			]

		return []
