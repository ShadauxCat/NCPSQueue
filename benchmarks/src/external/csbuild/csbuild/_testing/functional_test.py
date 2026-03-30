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
.. module:: functional_test
	:synopsis: A base class for functional tests, which will execute makefiles

.. moduleauthor:: Jaedyn K. Draper
"""

from __future__ import unicode_literals, division, print_function

import os
import sys
import threading
import shutil
import platform
import re

from .testcase import TestCase
from .. import log, commands
from .._utils import PlatformString, queue
from .._utils.string_abc import String

if platform.system() == "Windows":
	# pylint: disable=import-error
	import ctypes
	from ctypes import wintypes
	# Create ctypes wrapper for Win32 functions we need, with correct argument/return types
	_CreateMutex = ctypes.windll.kernel32.CreateMutexA
	_CreateMutex.argtypes = [wintypes.LPCVOID, wintypes.BOOL, wintypes.LPCSTR]
	_CreateMutex.restype = wintypes.HANDLE

	_WaitForSingleObject = ctypes.windll.kernel32.WaitForSingleObject
	_WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
	_WaitForSingleObject.restype = wintypes.DWORD

	_ReleaseMutex = ctypes.windll.kernel32.ReleaseMutex
	_ReleaseMutex.argtypes = [wintypes.HANDLE]
	_ReleaseMutex.restype = wintypes.BOOL

	_CloseHandle = ctypes.windll.kernel32.CloseHandle
	_CloseHandle.argtypes = [wintypes.HANDLE]
	_CloseHandle.restype = wintypes.BOOL

	class _namedMutex(object):
		# pylint: disable=invalid-name
		"""Represents a named synchronization primitive - a named mutex in windows, a file lock in linux"""
		def __init__(self, name):
			# Backslashes not ok. Forward slashes are fine.
			self.name = "csbuild/"+name.replace("\\", "/")
			if sys.version_info[0] >= 3:
				self.name = self.name.encode("UTF-8")
			ret = _CreateMutex(None, False, self.name)
			if not ret:
				raise ctypes.WinError()
			self.handle = ret

		def acquire(self):
			"""Acquire the lock"""
			timeout = 0xFFFFFFFF
			ret = _WaitForSingleObject(self.handle, timeout)
			if ret not in (0, 0x80, 0x102):
				# Waiting failed
				raise ctypes.WinError()

		def release(self):
			"""Release the lock"""
			ret = _ReleaseMutex(self.handle)
			if not ret:
				raise ctypes.WinError()

		def close(self):
			"""Close the lock"""
			ret = _CloseHandle(self.handle)
			if not ret:
				raise ctypes.WinError()

		def __enter__(self):
			self.acquire()

		def __exit__(self, excType, excVal, tb):
			self.release()
			return False
else:
	import fcntl # pylint: disable=import-error
	import tempfile

	class _namedMutex(object):
		# pylint: disable=invalid-name
		"""Represents a named synchronization primitive - a named mutex in windows, a file lock in linux"""
		def __init__(self, name):
			self.name = os.path.join(tempfile.gettempdir(), name)
			dirname = os.path.dirname(self.name)
			if not os.access(dirname, os.F_OK):
				os.makedirs(dirname)
			self.handle = open(self.name, 'w')

		def acquire(self):
			"""Acquire the lock"""
			fcntl.flock(self.handle, fcntl.LOCK_EX)

		def release(self):
			"""Release the lock"""
			fcntl.flock(self.handle, fcntl.LOCK_UN)

		def close(self):
			"""Close the lock"""
			self.handle.close()

		def __enter__(self):
			self.acquire()

		def __exit__(self, excType, excVal, tb):
			self.release()
			return False

def ListFiles(startpath):
	"""
	List the files in a directory in a nice tree structure
	:param startpath: Directory
	:type startpath: str
	:return: String representation of the directory structure
	:rtype: str
	"""
	ret = ""
	for root, _, files in os.walk(startpath):
		level = root.replace(startpath, '').count(os.sep)
		indent = ' ' * 4 * (level)
		ret += '{}{}/\n'.format(indent, os.path.basename(root))
		subindent = ' ' * 4 * (level + 1)
		for f in files:
			ret += '{}{}\n'.format(subindent, f)
	return ret

class FunctionalTest(TestCase):
	"""
	Base class for running functional tests that invoke an actual makefile.
	"""
	def setUp(self, outDir="out", intermediateDir="intermediate", cleanAtEnd=True, cleanArgs=None): #pylint: disable=arguments-differ
		self._prevdir = os.getcwd()

		if os.getenv(PlatformString("CSBUILD_RUNNING_THROUGH_PYTHON_UNITTEST")) != PlatformString("1"):
			module = __import__(self.__class__.__module__)
			path = os.path.dirname(module.__file__)
		else:
			path = os.path.dirname(self.__class__.__module__.replace('.', os.path.sep))

		self.mtx = _namedMutex(os.path.join(path, "lock"))
		self.mtx.acquire()

		if PlatformString("CSBUILD_NO_AUTO_RUN") in os.environ:
			self._oldenviron = os.environ[PlatformString("CSBUILD_NO_AUTO_RUN")]
			del os.environ[PlatformString("CSBUILD_NO_AUTO_RUN")]
		else:
			self._oldenviron = None

		if not os.path.exists(path):
			path = os.path.join("functional_tests", path)
		os.chdir(path)

		self.outDir = outDir
		self.intermediateDir = intermediateDir
		self.cleanAtEnd = cleanAtEnd

		self.cleanArgs = cleanArgs

		# Make sure we start in a good state
		if os.access(outDir, os.F_OK):
			shutil.rmtree(outDir)
		if os.access(intermediateDir, os.F_OK):
			shutil.rmtree(intermediateDir)
		if os.access(".csbuild", os.F_OK):
			shutil.rmtree(".csbuild")

	def tearDown(self):
		try:
			if self.cleanAtEnd:
				if self.cleanArgs is not None:
					self.RunMake("--clean", *self.cleanArgs)
				else:
					self.RunMake("--clean")
				if os.access(self.outDir, os.F_OK):
					self.fail("Out dir not removed by clean:\n{}".format(ListFiles(self.outDir)))
				if os.access(self.intermediateDir, os.F_OK):
					self.fail("Intermediate dir not removed by clean:\n{}".format(ListFiles(self.intermediateDir)))
		finally:
			os.chdir(self._prevdir)
			if self._oldenviron is not None:
				os.environ[PlatformString("CSBUILD_NO_AUTO_RUN")] = self._oldenviron
			self.mtx.release()
			self.mtx.close()

	def RunMake(self, *args):
		"""
		Run the test's local makefile with the given args. The makefile must be in the same directory and named make.py
		:param args: Arguments to pass
		:type args: str
		:return: Tuple of returncode, stdout and stderr output from the process
		:rtype: tuple[int, str, str]
		"""
		commands.queueOfLogQueues = queue.Queue()
		outputThread = threading.Thread(target=commands.PrintStaggeredRealTimeOutput)
		outputThread.start()

		callbackQueue = queue.Queue()
		log.SetCallbackQueue(callbackQueue)

		class _shared(object):
			ret = (0, "", "")

		def _runCommand():
			cmd = [sys.executable, os.path.abspath("make.py")]
			cmd.extend(args)
			cmd.append("--force-progress-bar=off")

			def _handleStdout(shared, msg):
				commands.DefaultStdoutHandler(shared, "            {}".format(msg))

			def _handleStderr(shared, msg):
				commands.DefaultStderrHandler(shared, "            {}".format(msg))

			_shared.ret = commands.Run(cmd, stdout=_handleStdout, stderr=_handleStderr, cwd=os.getcwd(), env=os.environ)
			callbackQueue.Put(commands.stopEvent)

		commandThread = threading.Thread(target=_runCommand)
		commandThread.start()
		while True:
			callback = callbackQueue.GetBlocking()

			if callback is commands.stopEvent:
				break
			callback()

		commands.queueOfLogQueues.Put(commands.stopEvent)
		outputThread.join()
		log.SetCallbackQueue(None)

		commandThread.join()

		ansiEscape = re.compile(r'\x1b[^m]*m')
		returncode, output, errors = _shared.ret
		output = ansiEscape.sub("", output)
		errors = ansiEscape.sub("", errors)
		return returncode, output, errors

	# pylint: disable=invalid-name
	def assertMakeSucceeds(self, *args):
		"""
		Assert that running a makefile succeeds
		:param args: Arguments to pass
		:type args: str
		:return: Tuple of returncode, stdout and stderr output from the process
		:rtype: tuple[int, str, str]
		"""
		returncode, output, errors = self.RunMake(*args)
		self.assertEqual(returncode, 0)
		return returncode, output, errors

	def assertMakeRaises(self, error, *args):
		"""
		Assert that running a makefile fails with the given exception
		:param args: Arguments to pass
		:type args: str
		:param error: Error or exception to search for in the logs
		:type error: Exception or str
		:return: Tuple of returncode, stdout and stderr output from the process
		:rtype: tuple[int, str, str]
		"""
		returncode, output, errors = self.RunMake(*args)
		self.assertNotEqual(returncode, 0)
		if not isinstance(error, String):
			error = error.__name__
		self.assertIn(error, errors)
		return returncode, output, errors

	def assertMakeFails(self, error, *args):
		"""
		Assert that running a makefile fails with the given csbuild error
		:param args: Arguments to pass
		:type args: str
		:param error: Error regular expression to search for in the logs
		:type error: str
		:return: Tuple of returncode, stdout and stderr output from the process
		:rtype: tuple[int, str, str]
		"""
		returncode, output, errors = self.RunMake(*args)
		self.assertNotEqual(returncode, 0)
		error = re.compile(error)
		outMatch = error.search(output)
		errMatch = error.search(errors)
		self.assertTrue(outMatch is not None or errMatch is not None)
		return returncode, output, errors

	def assertFileExists(self, filename):
		"""
		Assert that an expected file exists
		:param filename: file to check
		:type filename: str
		"""
		self.assertTrue(os.access(filename, os.F_OK), "No such file: {}".format(filename))

	def assertFileDoesNotExist(self, filename):
		"""
		Assert that an expected file doesn't exists
		:param filename: file to check
		:type filename: str
		"""
		self.assertFalse(os.access(filename, os.F_OK), "File exists: {}".format(filename))

	def assertFileIsExecutable(self, filename):
		"""
		Assert that an expected file is executable
		:param filename: file to check
		:type filename: str
		"""
		self.assertTrue(os.access(filename, os.X_OK), "No such executable file: {}".format(filename))

	# pylint: disable=invalid-name
	def assertFileContents(self, filename, expectedContents):
		"""
		Assert that an expected file exists and its contents are as expected
		:param filename: file to check
		:type filename: str
		:param expectedContents: Contents to check against
		:type expectedContents: str
		"""
		self.assertFileExists(filename)
		with open(filename, "r") as f:
			foundContents = f.read()
			self.assertEqual(expectedContents, foundContents, "File {} did not contain expected contents (Expected {}, got {})".format(filename, expectedContents, foundContents))
