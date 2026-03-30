# Copyright (C) 2017 Jaedyn K. Draper
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
# pylint: skip-file
"""
.. module:: sitecustomize
	:synopsis: Hacky stuff for getting pycharm test runners to work

.. moduleauthor:: Jaedyn K. Draper
"""

from __future__ import unicode_literals, division, print_function

import os
import sys

# Copied from csbuild._utils because we can't import that before we set environ, and we need this to do that
if sys.version_info[0] >= 3:
	def PlatformString(inputStr):
		"""
		In the presence of unicode_literals, get an object that is type str in both python2 and python3.
		:return: str representation of inputStr
		:rtype: str
		"""
		if isinstance(inputStr, str):
			return inputStr
		return inputStr.decode("UTF-8")
else:
	def PlatformString(inputStr):
		"""
		In the presence of unicode_literals, get an object that is type str in both python2 and python3.
		:return: str representation of inputStr
		:rtype: str
		"""
		if isinstance(inputStr, str):
			return inputStr
		return inputStr.encode("UTF-8")

edit_done = False


def PathHook(_):
	"""
	Hacks around some stuff to make sure things are properly set up when running with jetbrains test runner
	instead of run_unit_tests.py
	"""
	global edit_done
	if edit_done:
		raise ImportError
	try:
		argv = sys.argv
	except AttributeError:
		pass
	else:
		edit_done = True
		isTestRunner = False
		if argv[0].endswith("pydevd.py"):
			for arg in argv:
				if arg.endswith('_jb_unittest_runner.py'):
					isTestRunner = True
					break
		elif argv[0].endswith('_jb_unittest_runner.py'):
			isTestRunner = True

		if isTestRunner:
			import signal

			def _exitsig(sig, _):
				from csbuild import log
				if sig == signal.SIGINT:
					log.Error("Keyboard interrupt received. Aborting test run.")
				else:
					log.Error("Received terminate signal. Aborting test run.")
				os._exit(sig)  # pylint: disable=protected-access

			signal.signal(signal.SIGINT, _exitsig)
			signal.signal(signal.SIGTERM, _exitsig)

			os.environ[PlatformString("CSBUILD_RUNNING_THROUGH_PYTHON_UNITTEST")] = PlatformString("1")
			os.environ[PlatformString("CSBUILD_NO_AUTO_RUN")] = PlatformString("1")
			sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
			os.environ[PlatformString("PYTHONPATH")] = os.pathsep.join(sys.path)
			os.chdir(os.path.dirname(os.path.abspath(__file__)))

	raise ImportError  # let the real import machinery do its work


sys.path_hooks[:0] = [PathHook]

def EnableResourceWarningStackTraces():
	"""
	Calling this function patches the open() function to collect tracebacks, which will get printed
	if a ResourceWarning is thrown.
	"""
	from io import FileIO as _FileIO
	import _pyio
	import builtins # pylint: disable=import-error
	import linecache
	import traceback
	import tracemalloc # pylint: disable=import-error
	import warnings

	def WarnUnclosed(obj, delta=1):
		"""Warns when unclosed files are detected"""
		delta += 1
		trace = tracemalloc.get_object_traceback(obj)
		if trace is None:
			return
		try:
			warnings.warn("unclosed %r" % obj, ResourceWarning, delta + 1) # pylint: disable=undefined-variable
			print("Allocation traceback (most recent first):")
			for frame in trace:
				print("  File %r, line %s" % (frame.filename, frame.lineno))
				line = linecache.getline(frame.filename, frame.lineno)
				line = line.strip()
				if line:
					print("    %s" % line)

			frame = sys._getframe(delta) # pylint: disable=protected-access
			trace = traceback.format_stack(frame)
			print("Destroy traceback (most recent last):")
			for line in trace:
				sys.stdout.write(line)
			sys.stdout.flush()
		finally:
			obj.close()


	class MyFileIO(_FileIO):
		"""Override for fileio that detects file leaks"""
		def __init__(self, *args, **kw):
			_FileIO.__init__(self, *args, **kw)
			trace = tracemalloc.get_object_traceback(self)
			if trace is None:
				raise RuntimeError("tracemalloc is disabled")

		def __del__(self):
			if not self.closed:
				WarnUnclosed(self)
			if hasattr(_FileIO, '__del__'):
				_FileIO.__del__(self)


	def PatchOpen():
		"""patch the open function to detect file leaks"""
		# Already patched
		if _pyio.FileIO is MyFileIO:
			return

		# _io.open() uses an hardcoded reference to _io.FileIO
		# use _pyio.open() which lookup for FilIO in _pyio namespace
		_pyio.FileIO = MyFileIO
		builtins.open = _pyio.open

	tracemalloc.start(25)
	PatchOpen()
