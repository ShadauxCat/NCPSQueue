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
.. module:: commands
	:synopsis: Utility functions for running commands across multiple threads with real-time output processing
		and semi-real-time synchronized output printing

.. moduleauthor:: Jaedyn K. Draper
"""

from __future__ import unicode_literals, division, print_function

import sys
import subprocess
import threading

from . import shared_globals, log, perf_timer
from ._utils import PlatformUnicode, queue
from ._utils.decorators import TypeChecked

if sys.version_info[0] >= 3:
	from collections.abc import Callable
else:
	from collections import Callable # pylint: disable=deprecated-class

if sys.version_info >= (3,3,0):
	from shlex import quote
else:
	from pipes import quote # pylint: disable=deprecated-module

queueOfLogQueues = queue.Queue()
stopEvent = object()

def PrintStaggeredRealTimeOutput():
	"""
	Handle output put into the queue of queues
	Grab the first queue from the outer queue, then process all output from that queue
	until told to stop before moving on to the next queue. Each process that emits output creates
	its own queue; this ensures output from a single process is printed as soon as it's available,
	but output from multiple processes is not interleaved.
	"""
	while True:
		innerQueue = queueOfLogQueues.GetBlocking()
		if innerQueue is stopEvent:
			break
		while True:
			msg = innerQueue.GetBlocking()
			if msg is stopEvent:
				break
			msg[0](msg[1])

class _sharedStreamProcessingData(object):
	def __init__(self):
		self.queue = None
		self.lock = threading.Lock()

def LogNonInterleavedOutput(logFunction, shared, msg):
	"""
	Handle output from a process by putting it into the process-specific queue,
	which is itself placed into the queue of queues lazily if it's not already there.

	:param logFunction: Function to actually print the log message
	:type logFunction: Callable
	:param shared: shared data passed by Run
	:type shared: _sharedStreamProcessingData
	:param msg: A single line of output
	:type msg: str
	"""
	#Double-check lock pattern
	if shared.queue is None:
		with shared.lock:
			if shared.queue is None:
				shared.queue = queue.Queue()
				queueOfLogQueues.Put(shared.queue)
	shared.queue.Put((logFunction, msg))

def DefaultStdoutHandler(shared, msg):
	"""
	Default handler for process stdout, logs with log.Stdout
	:param shared: shared data passed by Run
	:type shared: _sharedStreamProcessingData
	:param msg: A single line of output
	:type msg: str
	"""
	LogNonInterleavedOutput(log.Stdout, shared, msg)

def DefaultStderrHandler(shared, msg):
	"""
	Default handler for process stderr, logs with log.Stderr
	:param shared: shared data passed by Run
	:type shared: _sharedStreamProcessingData
	:param msg: A single line of output
	:type msg: str
	"""
	LogNonInterleavedOutput(log.Stderr, shared, msg)

@TypeChecked(cmd=list, stdout=(Callable, type(None)), stderr=(Callable, type(None)))
def Run(cmd, stdout=DefaultStdoutHandler, stderr=DefaultStderrHandler, **kwargs):
	"""
	Run a process, collecting its output in realtime. Each line of output will be passed
	to the appropriate callback (stdout or stderr) one line at a time - the callback will be
	called once for each line. This function will block until the command exits.

	:param cmd: The command to run as a list of arguments, with the first parameter being the executable
	:type cmd: list
	:param stdout: Callback that will be called for each line of stdout at the moment it's emitted.
	:type stdout: Callable, None
	:param stderr: Callback that will be called for each line of stderr at the moment it's emitted.
	:type stderr: Callable, None
	:param kwargs: Additional arguments to be passed to subprocess.Popen(). See subprocess documentation
	:type kwargs: any
	:return: Tuple of return code, stdout as a single block string, and stderr as a single block string
	:rtype: tuple[int, str, str]
	"""
	with perf_timer.PerfTimer("Commands"):
		if shared_globals.showCommands:
			log.Command(" ".join(quote(s) for s in cmd))

		output = []
		errors = []
		shared = _sharedStreamProcessingData()

		def _streamOutput(pipe, outlist, callback):
			while True:
				try:
					line = PlatformUnicode(pipe.readline())
				except IOError:
					continue
				# Empty string means pipe was closed, possibly due to process exit, and we can leave the loop.
				# A blank line output by the pipe would be returned as "\n"
				if not line:
					break
				#Callback excludes newline
				if callback is not None:
					callback(shared, line.rstrip("\n\r"))
				outlist.append(line)

		proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, **kwargs)

		outputThread = threading.Thread(target=_streamOutput, args=(proc.stdout, output, stdout))
		errorThread = threading.Thread(target=_streamOutput, args=(proc.stderr, errors, stderr))

		outputThread.start()
		errorThread.start()

		outputThread.join()
		errorThread.join()

		proc.wait()

		proc.stdout.close()
		proc.stderr.close()

		if shared.queue is not None:
			shared.queue.Put(stopEvent)

		return proc.returncode, "".join(output), "".join(errors)
