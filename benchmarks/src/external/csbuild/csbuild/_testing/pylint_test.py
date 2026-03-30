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
.. module:: pylint_test
	:synopsis: Run pylint as part of the unit test framework
"""

from __future__ import unicode_literals, division, print_function

import multiprocessing
import os
import subprocess
import sys
import traceback
import threading
import re
import unittest

from . import testcase
from .. import log
from .._utils import thread_pool, PlatformString, queue, PlatformUnicode

class TestPylint(testcase.TestCase):
	"""Test to run pylint"""
	# pylint: disable=invalid-name
	@unittest.skipIf(sys.version_info.major < 3, "Pylint is no longer supported on Python 2")
	def testPyLint(self):
		"""Run pylint on the code and ensure it passes all pylint checks"""

		callbackQueue = queue.Queue()
		log.SetCallbackQueue(callbackQueue)
		pool = thread_pool.ThreadPool(multiprocessing.cpu_count(), callbackQueue, stopOnException=False)

		env = dict(os.environ)
		env[PlatformString('PYTHONPATH')] = os.pathsep.join(sys.path)

		fd = subprocess.Popen([sys.executable, "csbuild/_testing/run_pylint.py", "--version"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env)
		out, err = fd.communicate()
		if err:
			log.Error(err)
		if out:
			log.Info(out)

		failedLints = set()
		lock = threading.Lock()

		ansiEscape = re.compile(r'\x1b[^m]*m')
		def _parseAndRejigger(module, data):
			out = []
			data = PlatformUnicode(data)
			data = ansiEscape.sub('', data)
			for line in data.splitlines():
				match = re.match(R".:\s*(\d+),\s*\d+: (.+)", line)
				if not match:
					match = re.match(R".+:(\d+):\d+: (.+)", line)
				if match:
					out.append('  File "{}", line {}, in pylint\n    {}'.format(os.path.abspath(module), match.group(1), match.group(2)))
				else:
					# Recent versions of pylint annoyingly print these lines about the config file to stderr and while
					# there is an option internally to silence these messages, there is no switch available externally
					# for configuring it.  This means we need to check for those messages manually and discard them.
					if not line.startswith("Using config file ") and line != "No config file found, using default configuration":
						out.append(line)
			return "\n".join(out) + "\n" if out else ""

		def _runPylint(module):
			log.Info("Linting module {}", module)
			moduleFullPath = os.path.abspath(module)
			fd = subprocess.Popen([sys.executable, "csbuild/_testing/run_pylint.py", module], stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env)
			out, err = fd.communicate()
			if err:
				err = _parseAndRejigger(moduleFullPath, err)
				if err:
					log.Error("LINTING {}:\n\n{}", module, PlatformString(err))
			if out:
				out = _parseAndRejigger(moduleFullPath, out)
				if out:
					log.Error("LINTING {}:\n\n{}", module, PlatformString(out))
			if fd.returncode != 0:
				#pylint: disable=not-context-manager
				with lock:
					failedLints.add(module)
			self.assertEqual(0, fd.returncode)

		class _sharedLocals(object):
			count = 0
			done = 0

		def _checkDone():
			_sharedLocals.done += 1
			log.Info("-- Completed {} out of {} lintings", _sharedLocals.done, _sharedLocals.count)
			if _sharedLocals.count == _sharedLocals.done:
				pool.Stop()

		resultMTime = 0
		if os.access("failedLints.txt", os.F_OK):
			resultMTime = os.path.getmtime("failedLints.txt")

		failedLints = set()

		if os.access("failedLints.txt", os.F_OK):
			with open("failedLints.txt", "r") as f:
				failedLints = set(f.readlines())


		importRegex = re.compile(R"import (.*)")
		fromImportRegex = re.compile(R"from (.*) import (.*)")
		dotsRegex = re.compile(R"(\.+)(.*)")
		relintMemo = {}

		def _getModuleOrPackageInit(pkg):
			if os.access(pkg + ".py", os.F_OK):
				return pkg + ".py"

			if not os.access(pkg, os.F_OK):
				return None

			if os.path.isdir(pkg):
				pkg = os.path.join(pkg, "__init__.py")
				if not os.access(pkg, os.F_OK):
					return None
			return pkg

		# Ignore python virtual environments.
		fileDiscardRegex = re.compile(r"venv[\d\s\w]*[\\/]", 0)

		def _shouldRelint(filename):
			if fileDiscardRegex.match(filename):
				return False
			if filename in failedLints:
				return True
			if filename in relintMemo:
				shouldRelint = relintMemo[filename]
			else:
				shouldRelint = os.path.getmtime(filename) > resultMTime
				relintMemo[filename] = shouldRelint

			if shouldRelint:
				return True

			with open(filename, "r") as f:
				for line in f.readlines():
					line = line.strip()
					match = importRegex.match(line)
					pkg = None
					if match:
						replaced = match.group(1).replace(".", os.path.sep)
						pkg = _getModuleOrPackageInit(os.path.join(os.path.dirname(filename), replaced))

						if pkg is None:
							pkg = _getModuleOrPackageInit(replaced)
					else:
						match = fromImportRegex.match(line)
						if match:
							pkg = match.group(1)
							if pkg == "__future__":
								continue
							if pkg.startswith("csbuild"):
								pkg = pkg.replace(".", os.sep)
							elif pkg.startswith("."):
								dotmatch = dotsRegex.match(pkg)
								startDots = dotmatch.group(1)[1:]
								end = dotmatch.group(2).replace(".", os.sep)
								pkg = os.path.join(os.path.dirname(filename), startDots.replace(".", "../") + end)
							pkg = _getModuleOrPackageInit(os.path.normpath(pkg))

					if pkg is not None:
						if pkg in failedLints:
							return resultMTime + 1

						if pkg in relintMemo:
							shouldRelint = relintMemo[pkg]
						else:
							shouldRelint = _shouldRelint(pkg)
							relintMemo[pkg] = shouldRelint

						if shouldRelint:
							return True
			return False

		repoRootPath = os.getcwd()
		for root, _, files in os.walk(repoRootPath):
			root = os.path.relpath(root, repoRootPath)

			# Discard directories that begin with '.'
			if len(root) > 1 and root.startswith("."):
				continue

			for filename in files:
				# Discard files that begin with '.'
				if filename.startswith("."):
					continue

				if filename.endswith(".py"):
					finalfile = os.path.normpath(os.path.join(root, filename))

					if _shouldRelint(finalfile):
						_sharedLocals.count += 1
						pool.AddTask((_runPylint, finalfile), _checkDone)

		if _sharedLocals.count == 0:
			return

		failedLints = set()
		pool.Start()
		errors = False

		while True:
			cb = callbackQueue.GetBlocking()

			if cb is thread_pool.ThreadPool.exitEvent:
				break
			toReraise = None
			try:
				cb()
			except thread_pool.ThreadedTaskException as e:
				toReraise = e

			if toReraise:
				try:
					toReraise.Reraise()
				except AssertionError:
					pass
				except:
					log.Error(traceback.format_exc())
					errors = True

		log.SetCallbackQueue(None)

		with open("failedLints.txt", "w") as f:
			f.write("\n".join(failedLints))

		if failedLints:
			log.Error("The following modules failed to lint:")
			for module in failedLints:
				log.Error("    {}", module)
			self.fail("{} files failed to lint: {}".format(len(failedLints), failedLints))

		if errors:
			self.fail("Exceptions were thrown during the test")
