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
.. module:: system
	:synopsis: functions with functionality analogous to the sys module, but specialized for csbuild

.. moduleauthor:: Jaedyn K. Draper
"""

from __future__ import unicode_literals, division, print_function

import functools
import os
import platform
import traceback

from . import shared_globals, module_importer
from .. import commands, perf_timer, log

if platform.system() == "Windows":
	def SyncDir(_):
		"""
		Synchronize a directory to ensure its contents are visible to other applications.
		Does nothing on Windows.
		:param _: Directory name
		:type _: str
		"""
		pass
else:
	def SyncDir(dirname):
		"""
		Synchronize a directory to ensure its contents are visible to other applications.
		Does nothing on Windows.
		:param dirname: Directory name
		:type dirname: str
		"""
		dirfd = os.open(dirname, os.O_DIRECTORY)
		os.fsync(dirfd)
		os.close(dirfd)

def CleanUp():
	"""
	Clean up the various plates we're spinning so they don't crash to the ground or spin forever
	"""
	try:
		with perf_timer.PerfTimer("Cleanup"):

			if shared_globals.commandOutputThread is not None:
				commands.queueOfLogQueues.Put(commands.stopEvent)
				shared_globals.commandOutputThread.join()

		if shared_globals.runPerfReport:
			if shared_globals.runPerfReport != perf_timer.ReportMode.HTML:
				output = functools.partial(log.Custom, log.Color.WHITE, "PERF")
			else:
				output = None
			perf_timer.PerfTimer.PrintPerfReport(shared_globals.runPerfReport, output=output)

		log.StopLogThread()
	except:
		traceback.print_exc()
	finally:
		if not module_importer.lock_held():
			module_importer.acquire_lock()

	# TODO: Kill running subprocesses
	# TODO: Exit events for plugins and toolchains

def Exit(code = 0):
	"""
	Exit the build process early

	:param code: Exit code to exit with
	:type code: int
	"""
	CleanUp()
	# Die hard, we don't need python to clean up and we want to make sure this exits.
	# sys.exit just throws an exception that can be caught. No catching allowed.
	# pylint: disable=protected-access
	os._exit(code)
