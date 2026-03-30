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
.. module:: oracle_java_archiver
	:synopsis: Oracle-compatible Java archiver tool.

.. moduleauthor:: Zoe Bare
"""

from __future__ import unicode_literals, division, print_function

import platform
import os
import subprocess

from .java_archiver_base import JavaArchiverBase

class OracleJavaArchiver(JavaArchiverBase):
	"""
	Oracle-compatible Java archiver implementation.
	"""
	def __init__(self, projectSettings):
		JavaArchiverBase.__init__(self, projectSettings)

		self._javaArchiverPath = os.path.join(self._javaBinPath, "jar{}".format(".exe" if platform.system() == "Windows" else ""))

		try:
			subprocess.call([self._javaArchiverPath], stdout = subprocess.PIPE, stderr = subprocess.PIPE)
		except:
			raise IOError("Oracle Java archiver not found at path: {}".format(self._javaArchiverPath))


	####################################################################################################################
	### Methods implemented from base classes
	####################################################################################################################

	def _getOutputFiles(self, project):
		return tuple({ self._getOutputFilePath(project) })

	def _getCommand(self, project, inputFiles, classRootPath):
		cmd = [self._javaArchiverPath] \
			+ self._getSwitchArgs() \
			+ self._getOutputArgs(project) \
			+ self._getEntryPointClassArgs() \
			+ self._getInputArgs(classRootPath)

		return [arg for arg in cmd if arg]


	####################################################################################################################
	### Internal methods
	####################################################################################################################

	def _getOutputFilePath(self, project):
		return os.path.join(project.outputDir, "{}.jar".format(project.outputName))

	def _getOutputArgs(self, project):
		return [self._getOutputFilePath(project)]

	def _getSwitchArgs(self):
		return ["cf" + "e" if self._entryPointClass else ""]

	def _getEntryPointClassArgs(self):
		return [self._entryPointClass] if self._entryPointClass else []

	def _getInputArgs(self, classRootPath):
		rootItems = os.listdir(classRootPath)
		args = []

		# Pass in only the items in the class root directory since the Java archiver
		# will recursively find class files in directories.  This is important so the
		# layout of the files in the final archive have the correct directory structure.
		for item in rootItems:
			args.extend([
				"-C",
				classRootPath,
				item
			])

		return args
