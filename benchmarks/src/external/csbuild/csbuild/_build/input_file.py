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
.. module:: input_file
	:synopsis: Information about a file used as a tool input

.. moduleauthor:: Jaedyn K. Draper
"""

from __future__ import unicode_literals, division, print_function

import os
import hashlib
import sys

from .._utils.decorators import TypeChecked
from .._utils import PlatformBytes
from .._utils import PlatformString

if sys.version_info[0] >= 3:
	_typeType = type
	_classType = type
else:
	import types
	# pylint: disable=invalid-name
	_typeType = types.TypeType
	_classType = types.ClassType

class InputFile(object):
	"""
	Represents an input file along with its tool history.
	Stores both the full set of tools used to create the file,
	as well as a link to the previous input source that created it

	:param filename: The filename
	:type filename: str, bytes

	:param sourceInputs: The previous sinput in the chain (if None, this represents the first input)
	:type sourceInputs: ordered_set.OrderedSet[InputFile]

	:param upToDate: whether or not the file was up to date (i.e., no build was performed)
	:type upToDate: bool
	"""
	def __init__(self, filename, sourceInputs=None, upToDate=False):
		self._filename = os.path.abspath(PlatformString(filename))
		self._sourceInputs = sourceInputs
		self._toolsUsed = set()
		self._upToDate = upToDate
		self._uniqueDirectoryId = None
		if sourceInputs is not None:
			if isinstance(sourceInputs, InputFile):
				# pylint: disable=protected-access
				self._toolsUsed |= sourceInputs._toolsUsed
			else:
				for sourceInput in sourceInputs:
					# pylint: disable=protected-access
					self._toolsUsed |= sourceInput._toolsUsed

	def __repr__(self):
		mainFileDir = os.path.dirname(sys.modules["__main__"].__file__)
		try:
			return os.path.relpath(self._filename, mainFileDir).replace("\\", "/")
		except:
			return self._filename

	@TypeChecked(tool=(_classType, _typeType))
	def AddUsedTool(self, tool):
		"""
		Add a tool to the set of tools that have been used on this file

		:param tool: The used tool
		:type tool: type
		"""
		self._toolsUsed.add(tool)

	@TypeChecked(tool=(_classType, _typeType), _return=bool)
	def WasToolUsed(self, tool):
		"""
		Check if a tool was used in the process of creating this file (or any file used in the input chain that led to it)

		:param tool: The tool to check
		:type tool: type
		:return: True if the tool was used, False otherwise
		:rtype: bool
		"""
		return tool in self._toolsUsed

	@property
	def filename(self):
		"""
		Get the absolute path to the file

		:return: Absolute path to the file
		:rtype: str
		"""
		return self._filename

	@property
	def sourceInputs(self):
		"""
		Get the InputFile that was used to create this file, if any

		:return: The InputFile that was used to create this file
		:rtype: list[InputFile] or None
		"""
		return self._sourceInputs

	@property
	def upToDate(self):
		"""
		Get whether or not the file was already up to date. If true, no build was performed.

		:return: Whether or not the file was up to date
		:rtype: bool
		"""
		return self._upToDate

	@property
	def toolsUsed(self):
		"""
		Get the list of tools used to make this input.

		:return: list of used tools
		:rtype: set
		"""
		return self._toolsUsed

	@property
	def uniqueDirectoryId(self):
		"""
		Get the unique identifier for the directory containing the file.

		:return: Directory unique identifier.
		:rtype: str
		"""
		if self._uniqueDirectoryId is None:
			self._uniqueDirectoryId = hashlib.md5(PlatformBytes(os.path.dirname(self.filename))).hexdigest()
		return self._uniqueDirectoryId
