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
.. module:: android_gcc_assembler
	:synopsis: Android GCC assember tool

.. moduleauthor:: Zoe Bare
"""

from __future__ import unicode_literals, division, print_function

from ..common.android_tool_base import AndroidToolBase

from .gcc_assembler import GccAssembler

class AndroidGccAssembler(GccAssembler, AndroidToolBase):
	"""
	Android GCC assembler implementation
	"""
	supportedArchitectures = AndroidToolBase.supportedArchitectures

	def __init__(self, projectSettings):
		GccAssembler.__init__(self, projectSettings)
		AndroidToolBase.__init__(self, projectSettings)


	####################################################################################################################
	### Methods implemented from base classes
	####################################################################################################################

	def SetupForProject(self, project):
		"""
		Run project setup, if any, before building the project, but after all dependencies have been resolved.

		:param project: project being set up
		:type project: csbuild._build.project.Project
		"""
		GccAssembler.SetupForProject(self, project)
		AndroidToolBase.SetupForProject(self, project)

	def _getComplierName(self):
		return self._androidInfo.gccPath

	def _getArchitectureArgs(self, project):
		# The architecture is implied from the executable being run.
		return []
