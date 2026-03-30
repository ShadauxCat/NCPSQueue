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
.. module:: response_file
	:synopsis: Helper class for creating a tool response file.

.. moduleauthor:: Zoe Bare
"""

from __future__ import unicode_literals, division, print_function

from . import PlatformBytes

import os
import platform
import threading

class ResponseFile(object):
	"""
	Response file helper class.

	:param project: Project used with the response file.
	:type project: :class:`csbuild._build.project.Project`

	:param name: Basename of the response file.
	:type name: str

	:param cmd: List of command arguments to write into the response file.
	:type cmd: list[str]
	"""
	_lock = threading.Lock()

	def __init__(self, project, name, cmd):
		dirPath = os.path.join(project.csbuildDir, "cmd", project.outputName, project.toolchainName, project.architectureName, project.targetName)
		fileMode = 438 # Octal 0666
		flags = os.O_WRONLY | os.O_CREAT | os.O_TRUNC

		# The O_NOINHERIT constant only exists on Windows, so we can't do this in the pythonic way.
		if platform.system() == "Windows":
			flags |= os.O_NOINHERIT # pylint:disable=no-member

		# Create the output directory.
		if not os.access(dirPath, os.F_OK):
			# TODO: Investigate ways to handle this in a lock-free manner.
			with ResponseFile._lock: # pylint:disable=not-context-manager
				if not os.access(dirPath, os.F_OK):
					os.makedirs(dirPath)

		self._filePath = os.path.join(dirPath, name)
		self._commandList = [
			"\"{}\"".format(arg)
				if " " in arg and "\"" not in arg
					else arg
			for arg in cmd if arg
		]

		f = os.open(self._filePath, flags, fileMode)

		os.write(f, PlatformBytes("\n".join([arg.replace("\\", r"\\") for arg in self._commandList])))
		os.fsync(f)
		os.close(f)

	@property
	def filePath(self):
		"""
		Get the path to the response file.
		:return: Response file path.
		:rtype: str
		"""
		return self._filePath

	@property
	def commandList(self):
		"""
		Get the original list of list of commands.
		:return: Original command list.
		:rtype: list[str]
		"""
		return self._commandList

	def AsString(self):
		"""
		Get the full string of the command arguments.
		:return: Original command list as string.
		:rtype: str
		"""
		return " ".join(self._commandList)
