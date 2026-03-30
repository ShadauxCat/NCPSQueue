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
.. package:: _utils
	:synopsis: misc internal utility modules

.. moduleauthor:: Jaedyn K. Draper
"""

from __future__ import unicode_literals, division, print_function

import math
import subprocess
import sys

if sys.version_info[0] >= 3:
	BytesType = bytes
	StrType = str

	def PlatformString(inputStr):
		"""
		In the presence of unicode_literals, get an object that is type str in both python2 and python3.
		:return: str representation of inputStr
		:rtype: str
		"""
		if isinstance(inputStr, str):
			return inputStr
		return inputStr.decode("UTF-8")

	def PlatformUnicode(inputStr):
		"""
		In the presence of unicode_literals, get an object that is type unicode in python2 and str in python3.
		:return: unicode representation of inputStr
		:rtype: str
		"""
		return PlatformString(inputStr)

	def PlatformBytes(inputStr):
		"""
		In the presence of unicode_literals, get an object that is type str in python2 and bytes in python3.
		:return: bytes representation of inputStr
		:rtype: bytes
		"""
		if isinstance(inputStr, bytes):
			return inputStr
		return inputStr.encode("UTF-8")
else:
	BytesType = str
	StrType = unicode # pylint: disable=undefined-variable

	def PlatformString(inputStr):
		"""
		In the presence of unicode_literals, get an object that is type str in both python2 and python3.
		:return: str representation of inputStr
		:rtype: str
		"""
		if isinstance(inputStr, str):
			return inputStr
		return inputStr.encode("UTF-8")

	def PlatformUnicode(inputStr):
		"""
		In the presence of unicode_literals, get an object that is type unicode in python2 and str in python3.
		:return: unicode representation of inputStr
		:rtype: unicode
		"""
		if isinstance(inputStr, unicode): # pylint: disable=undefined-variable
			return inputStr
		return inputStr.decode("UTF-8")

	def PlatformBytes(inputStr):
		"""
		In the presence of unicode_literals, get an object that is type str in python2 and bytes in python3.
		:return: bytes representation of inputStr
		:rtype: str
		"""
		return PlatformString(inputStr)

def FormatTime(totaltime, withMillis=True):
	"""
	Format a duration of time into minutes:seconds (i.e., 2:55)
	:param totaltime: duration of time
	:type totaltime: float
	:param withMillis: Include milliseconds in output
	:type withMillis: bool
	:return: formatted string
	:rtype: str
	"""
	totalmin = math.floor(totaltime / 60)
	totalsec = math.floor(totaltime % 60)
	if withMillis:
		msec = math.floor((totaltime - math.floor(totaltime))*10000)
		return "{}:{:02}.{:04}".format(int(totalmin), int(totalsec), int(msec))
	return "{}:{:02}".format(int(totalmin), int(totalsec))


class MultiBreak(Exception):
	"""
	Simple exception type to quickly break out of deeply nested loops.
	"""
	pass


def GetCommandLineString():
	"""
	Get the command line arguments used to invoke csbuild.

	:return: Command line arguments as a string.
	:rtype: str
	"""
	return subprocess.list2cmdline(sys.argv[1:])
