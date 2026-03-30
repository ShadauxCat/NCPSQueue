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
.. module:: clang_linker
	:synopsis: Clang linker tool.

.. moduleauthor:: Zoe Bare
"""

from __future__ import unicode_literals, division, print_function

from .gcc_linker import GccLinker
from ..common.clang_tool_base import ClangToolBase

class ClangLinker(ClangToolBase, GccLinker):
	"""
	Clang linker implementation
	"""

	def __init__(self, projectSettings):
		ClangToolBase.__init__(self, projectSettings)
		GccLinker.__init__(self, projectSettings)


	####################################################################################################################
	### Methods implemented from base classes
	####################################################################################################################

	def SetupForProject(self, project):
		ClangToolBase.SetupForProject(self, project)
		GccLinker.SetupForProject(self, project)

	def _getBinaryLinkerName(self):
		return "clang++"

	def _getArchitectureArgs(self, project):
		args = GccLinker._getArchitectureArgs(self, project)
		targetArgs = ClangToolBase._getArchitectureTargetArgs(self, project)

		args.extend(targetArgs)
		return args
