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
.. module:: terminfo
	:synopsis: Terminal info - detects number of columns, color support, etc
		and provides helper utilities

.. moduleauthor:: Jaedyn K. Draper
"""

from __future__ import unicode_literals, division, print_function

import platform
import sys

if platform.system() == "Windows":
	import ctypes
	import struct
else:
	import curses


class TermColor(object):
	"""
	Abstracts color in a cross-platform way. Values and types will differ based on platform.
	"""
	# pylint: disable=invalid-name
	if platform.system() == "Windows":
		DGREY = 0 | 8
		RED = 4 | 8
		GREEN = 2 | 8
		YELLOW = 2 | 4 | 8
		BLUE = 1 | 8
		MAGENTA = 1 | 4 | 8
		CYAN = 1 | 2 | 8
		WHITE = 1 | 2 | 4 | 8
		BLACK = 0
		DRED = 4
		DGREEN = 2
		DYELLOW = 2 | 4
		DBLUE = 1
		DMAGENTA = 1 | 4
		DCYAN = 1 | 2
		LGREY = 1 | 2 | 4
	else:
		DGREY = "1;30"
		RED = "1;31"
		GREEN = "1;32"
		YELLOW = "1;33"
		BLUE = "1;34"
		MAGENTA = "1;35"
		CYAN = "1;36"
		WHITE = "1;37"
		BLACK = "22;30"
		DRED = "22;31"
		DGREEN = "22;32"
		DYELLOW = "22;33"
		DBLUE = "22;34"
		DMAGENTA = "22;35"
		DCYAN = "22;36"
		LGREY = "22;37"


class TermInfo(object):
	"""
	Provides access to cross-platform methods of getting terminal info and interacting with
	colored output.
	"""

	@staticmethod
	def ResetColor():
		"""
		Reset the color of the terminal to its default value
		"""
		if platform.system() == "Windows":
			ctypes.windll.kernel32.SetConsoleTextAttribute(ctypes.windll.kernel32.GetStdHandle(-11), TermInfo._reset)
		else:
			sys.stdout.write("\033[0m")


	@staticmethod
	def SetColor(color):
		"""
		Set the color of the terminal

		:param color: The desired color
		:type color: TermColor value
		"""
		if platform.system() == "Windows":
			ctypes.windll.kernel32.SetConsoleTextAttribute(ctypes.windll.kernel32.GetStdHandle(-11), color)
		else:
			sys.stdout.write("\033[{}m".format(color))


	@staticmethod
	def GetNumColumns():
		"""
		Retrieve the current column count for this terminal

		:return: Number of columns
		:rtype: int
		"""
		if platform.system() == "Windows":
			csbi = ctypes.create_string_buffer(22)
			res = ctypes.windll.kernel32.GetConsoleScreenBufferInfo(ctypes.windll.kernel32.GetStdHandle(-11), csbi)
			if res:
				(_, _, _, _, _, left, _, right, _, _, _) = struct.unpack("hhhhHhhhhhh", csbi.raw)
				return right - left
			return 0
		if TermInfo._cursesValid:
			return curses.tigetnum('cols')
		return 0


	@staticmethod
	def SupportsColor():
		"""
		Check whether the active terminal supports colors.

		:return: Whether or not color is supported
		:rtype: bool
		"""
		if platform.system() == "Windows":
			return TermInfo._colorSupported
		if TermInfo._cursesValid:
			return curses.tigetnum("colors") >= 8
		return False


	@staticmethod
	def GetDefaultColor():
		"""
		Get the default color for this terminal

		:return: The default color
		:rtype: TermColor value
		"""
		if platform.system() == "Windows":
			csbi = ctypes.create_string_buffer(22)

			# -11 = STD_OUTPUT_HANDLE
			res = ctypes.windll.kernel32.GetConsoleScreenBufferInfo(ctypes.windll.kernel32.GetStdHandle(-11), csbi)
			assert res

			_, _, _, _, wattr, _, _, _, _, _, _ = struct.unpack("hhhhHhhhhhh", csbi.raw)
			return wattr

		return "0"


	if platform.system() == "Windows":
		try:
			# WTF? Apparently static methods don't become callable till the class body ends...
			_reset = GetDefaultColor.__func__()

		except:
			_colorSupported = False
		else:
			_colorSupported = True
	else:
		try:
			curses.setupterm()
			_cursesValid = True
		except:
			_cursesValid = False
