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
.. module:: android_clang_linker
	:synopsis: Android clang linker tool.

.. moduleauthor:: Zoe Bare
"""

from __future__ import unicode_literals, division, print_function

from .android_gcc_linker import AndroidGccLinker

class AndroidClangLinker(AndroidGccLinker):
	"""
	Clang linker implementation
	"""

	####################################################################################################################
	### Methods implemented from base classes
	####################################################################################################################

	def _getBinaryLinkerName(self):
		return self._androidInfo.clangPath

	def _getDefaultArgs(self, project):
		args = AndroidGccLinker._getDefaultArgs(self, project)
		return args + [
			"-gcc-toolchain",
			self._androidInfo.gccToolchainRootPath,
		]

	def _getArchitectureArgs(self, project):
		targetName = self._getTargetTripleName(project.architectureName)
		return ["-target", targetName]
