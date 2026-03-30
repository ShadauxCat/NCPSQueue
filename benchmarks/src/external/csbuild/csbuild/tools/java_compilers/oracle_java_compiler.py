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
.. module:: oracle_java_compiler
	:synopsis: Oracle-compatible Java compiler tool.

.. moduleauthor:: Zoe Bare
"""

from __future__ import unicode_literals, division, print_function

import platform
import os

from .java_compiler_base import JavaCompilerBase

def _ignore(_):
	pass

class OracleJavaCompiler(JavaCompilerBase):
	"""
	Oracle-compatible Java compiler implementation.
	"""

	def __init__(self, projectSettings):
		JavaCompilerBase.__init__(self, projectSettings)

		self._javaCompilerPath = os.path.join(self._javaBinPath, "javac{}".format(".exe" if platform.system() == "Windows" else ""))
		assert os.access(self._javaCompilerPath, os.X_OK), "Oracle Java compiler not found at path: {}".format(self._javaCompilerPath)


	####################################################################################################################
	### Methods implemented from base classes
	####################################################################################################################

	def _getOutputFiles(self, project, inputFiles, classRootPath):
		_ignore(project)
		_ignore(inputFiles)

		outputFiles = set()

		# Find each .class file in the intermediate directory.
		for root, _, files in os.walk(classRootPath):
			for filePath in files:
				outputFiles.add(os.path.join(root, filePath))

		return tuple(sorted(outputFiles))

	def _getCommand(self, project, inputFiles, classRootPath):
		cmd = [self._javaCompilerPath] \
			+ self._getClassPathArgs() \
			+ self._getSourcePathArgs() \
			+ self._getOutputPathArgs(classRootPath) \
			+ self._getInputFileArgs(inputFiles)

		return [arg for arg in cmd if arg]


	####################################################################################################################
	### Internal methods
	####################################################################################################################

	def _getClassPathArgs(self):
		if self._classPaths:
			arg = ";".join(self._classPaths)
			return [
				"-classpath",
				arg,
			]
		return []

	def _getSourcePathArgs(self):
		if self._srcPaths:
			arg = ";".join(self._srcPaths)
			return [
				"-sourcepath",
				arg,
			]
		return []

	def _getOutputPathArgs(self, classRootPath):
		return [
			"-d",
			classRootPath,
		]

	def _getInputFileArgs(self, inputFiles):
		return [f.filename for f in inputFiles]
