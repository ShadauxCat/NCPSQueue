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
.. module:: run_pylint
	:synopsis: Local pylint install, pretty much does exactly what the main pylint file does, but doing the same thing here
			and invoking this file directly ensures we run with the right python version (2 or 3) so we can test both
"""

from __future__ import unicode_literals, division, print_function

if __name__ == "__main__":
	import os
	import sys
	from pylint import run_pylint

	# Copied from csbuild._utils because we can't import that before we set environ, and we need this to do that
	if sys.version_info[0] >= 3:
		def PlatformString(inputStr):
			"""In the presence of unicode_literals, get an object that is type str in both python2 and python3."""
			if isinstance(inputStr, str):
				return inputStr
			return inputStr.decode("UTF-8")
	else:
		def PlatformString(inputStr):
			"""In the presence of unicode_literals, get an object that is type str in both python2 and python3."""
			if isinstance(inputStr, str):
				return inputStr
			return inputStr.encode("UTF-8")

	os.environ[PlatformString("CSBUILD_NO_AUTO_RUN")] = PlatformString("1")
	run_pylint()
