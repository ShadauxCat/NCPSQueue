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
.. module:: log
	:synopsis: Thread-safe logging system

.. moduleauthor:: Jaedyn K. Draper
"""

from __future__ import unicode_literals, division, print_function

import sys
import threading
import re
import time
import math

from ._utils import terminfo, shared_globals, BytesType, StrType, queue, FormatTime, PlatformUnicode
from ._utils.shared_globals import Verbosity
from . import perf_timer

_logQueue = queue.Queue()
_stopEvent = object()
_callbackQueue = None
_logThread = threading.current_thread()
_barPresent = False
_lastPerc = 0.0
_sep = "<"
_fillChar = "\u2219"

Color = terminfo.TermColor

def _printProgressBar():
	with perf_timer.PerfTimer("printProgressBar"):
		global _barPresent
		global _lastPerc
		global _sep
		global _fillChar
		completeBuilds = shared_globals.completedBuilds
		totalBuilds = shared_globals.totalBuilds
		if shared_globals.columns != 0 and completeBuilds < totalBuilds:
			_barPresent = True
			textSize = 42

			perc = 1 if totalBuilds == 0 else float(completeBuilds)/float(totalBuilds)
			if perc == 0:
				_sep = "-"
			elif perc > _lastPerc:
				_sep = ">"
			elif perc < _lastPerc:
				_sep = "<"
			_lastPerc = perc

			incr = int(shared_globals.columns / 50)
			if totalBuilds <= incr:
				count = totalBuilds * 4
			elif totalBuilds <= incr * 2:
				count = incr * 4 + (totalBuilds-incr) * 3
			elif totalBuilds <= incr * 3:
				count = incr * 4 + incr * 3 + (totalBuilds-incr*2) * 2
			else:
				count = incr * 4 + incr * 3 + incr * 2 + (totalBuilds-incr*3)

			if count >= shared_globals.columns - textSize:
				count = shared_globals.columns - textSize - 1

			num = int( math.floor( perc * count ) )

			lside = num
			rside = count - num - 1

			total = lside + rside + textSize
			maxSpace = (shared_globals.columns-1) / 2
			spacePerSide = maxSpace - (total/2)

			if spacePerSide <= 1:
				lfill = ""
				rfill = ""
			else:
				lfill = _fillChar * int(math.ceil(spacePerSide))
				rfill = _fillChar * int(math.floor(spacePerSide))
				if lfill:
					lfill = lfill[:-1] + " "
				if rfill:
					rfill = " " + rfill[1:]

			if shared_globals.colorSupported:
				terminfo.TermInfo.SetColor(Color.WHITE)

			sys.stdout.write(" [")

			if shared_globals.colorSupported:
				sys.stdout.flush()
				terminfo.TermInfo.SetColor(Color.GREEN)

			sys.stdout.write("{: 4}".format(completeBuilds))

			if shared_globals.colorSupported:
				sys.stdout.flush()
				terminfo.TermInfo.ResetColor()

			sys.stdout.write(" tasks done ")

			if shared_globals.colorSupported:
				sys.stdout.flush()
				terminfo.TermInfo.SetColor(Color.WHITE)

			sys.stdout.write("] ")

			if shared_globals.colorSupported:
				sys.stdout.flush()
				terminfo.TermInfo.SetColor(Color.DGREY)
			try:
				sys.stdout.write(lfill)
			except UnicodeEncodeError:
				_fillChar = ":"
				_printProgressBar()
				return

			if shared_globals.colorSupported:
				sys.stdout.flush()
				terminfo.TermInfo.SetColor(Color.WHITE)

			sys.stdout.write("[")

			if shared_globals.colorSupported:
				sys.stdout.flush()
				terminfo.TermInfo.SetColor(Color.DGREEN)

			sys.stdout.write("=" * lside)

			if shared_globals.colorSupported:
				sys.stdout.flush()
				terminfo.TermInfo.ResetColor()

			if perc == 0:
				if shared_globals.colorSupported:
					sys.stdout.flush()
					terminfo.TermInfo.SetColor(Color.DYELLOW)

			sys.stdout.write(_sep)

			if shared_globals.colorSupported:
				sys.stdout.flush()
				terminfo.TermInfo.SetColor(Color.DYELLOW)

			sys.stdout.write("-" * rside)

			if shared_globals.colorSupported:
				sys.stdout.flush()
				terminfo.TermInfo.SetColor(Color.WHITE)

			sys.stdout.write("]")

			if shared_globals.colorSupported:
				sys.stdout.flush()
				terminfo.TermInfo.SetColor(Color.DGREY)
			sys.stdout.write(rfill)
			if shared_globals.colorSupported:
				sys.stdout.flush()
				terminfo.TermInfo.SetColor(Color.WHITE)

			sys.stdout.write(" [")

			if shared_globals.colorSupported:
				sys.stdout.flush()
				terminfo.TermInfo.SetColor(Color.YELLOW)

			sys.stdout.write("{: 4}".format(totalBuilds))

			if shared_globals.colorSupported:
				sys.stdout.flush()
				terminfo.TermInfo.ResetColor()

			sys.stdout.write(" discovered ")
			if shared_globals.colorSupported:
				sys.stdout.flush()
				terminfo.TermInfo.SetColor(Color.WHITE)
			sys.stdout.write("]")
			sys.stdout.flush()

			if shared_globals.colorSupported:
				terminfo.TermInfo.ResetColor()
		else:
			_barPresent = False

def _clearProgressBar():
	with perf_timer.PerfTimer("clearProgressBar"):
		global _barPresent
		if _barPresent:
			sys.stdout.write(shared_globals.clearBar)
			_barPresent = False

def UpdateProgressBar():
	"""Update the progress bar, foo"""
	with perf_timer.PerfTimer("updateProgressBar"):
		if threading.current_thread() != _logThread:
			_callbackQueue.Put(UpdateProgressBar)
		else:
			_clearProgressBar()
			_printProgressBar()

_twoTagMatch = re.compile(R"(<&\w*>)(.*?)(</&>|$)")
_tagNameMatch = re.compile(R"<&(\w*)>")

def _writeLog(color, level, msg, destination=sys.stdout):
	with perf_timer.PerfTimer("Logging"):
		_clearProgressBar()

		if shared_globals.colorSupported and color is not None:
			terminfo.TermInfo.SetColor(color)
			if level is not None:
				destination.write("{}: ".format(level))
			destination.flush()
			terminfo.TermInfo.ResetColor()

			if "</" in msg:
				with perf_timer.PerfTimer("Regex splitting"):
					split = _twoTagMatch.split(msg)
					for piece in split:
						match = _tagNameMatch.match(piece)
						if match:
							color = getattr(Color, match.group(1))
							terminfo.TermInfo.SetColor(color)
						elif piece == "</&>":
							terminfo.TermInfo.ResetColor()
						else:
							try:
								destination.write(piece)
							except UnicodeEncodeError:
								destination.write(piece.encode("ascii", "replace").decode("ascii", "replace"))
							destination.flush()
			else:
				try:
					destination.write(msg)
				except UnicodeEncodeError:
					destination.write(msg.encode("ascii", "replace").decode("ascii", "replace"))

			destination.write("\n")

			terminfo.TermInfo.ResetColor()
		else:
			if level is not None:
				destination.write("{}: ".format(level))

			if "</" in msg:
				with perf_timer.PerfTimer("Regex splitting"):
					split = _twoTagMatch.split(msg)
					for piece in split:
						match = _tagNameMatch.match(piece)
						if match or piece == "</&>":
							continue
						try:
							destination.write(piece)
						except UnicodeEncodeError:
							destination.write(piece.encode("ascii", "replace").decode("ascii", "replace"))
			else:
				try:
					destination.write(msg)
				except UnicodeEncodeError:
					destination.write(msg.encode("ascii", "replace").decode("ascii", "replace"))

			destination.write("\n")

		if shared_globals.logFile:
			shared_globals.logFile.write("{0}: {1}\n".format(level, msg))
		_printProgressBar()
		destination.flush()

def Pump():
	"""
	Print logs that have been inserted into the queue from another thread.
	Logs inserted on the main thread are printed immediately -
	in single-threaded contexts this function is irrelevant
	"""
	try:
		# Pump all logs till we get an Empty exception, then return
		while True:
			event = _logQueue.Get()
			_writeLog(*event)
	except IndexError:
		return

def SetCallbackQueue(callbackQueue):
	"""
	Set the callback queue for threaded logging - a Pump call will be added to the queue each time a log call is made.
	This will ensure that logs are printed as quickly as possible after being inserted into the queue.

	:param callbackQueue: A queue for executing Pump calls
	:type callbackQueue: queue.Queue
	"""
	global _callbackQueue
	_callbackQueue = callbackQueue

def StartLogThread():
	"""Start the log thread"""
	global _callbackQueue
	_callbackQueue = queue.Queue()
	global _logThread
	def _logThreadRunner():
		while True:
			task = _callbackQueue.GetBlocking()
			if task is _stopEvent:
				return
			task()
	_logThread = threading.Thread(target=_logThreadRunner)
	_logThread.start()

def StopLogThread():
	"""Stop the log thread if it's running. If not, this is a nop."""
	global _logThread
	if threading.current_thread() != _logThread:
		_callbackQueue.Put(_stopEvent)
		_logThread.join()
		_logThread = threading.current_thread()

def _logMsg(color, level, msg, quietThreshold):
	"""Print a message to stdout"""
	if shared_globals.verbosity < quietThreshold:
		if isinstance(msg, BytesType):
			msg = msg.decode("UTF-8")
		if threading.current_thread() == _logThread:
			_writeLog(color, level, msg)
		else:
			assert _callbackQueue is not None, "Threaded logging requires a callback queue (shared with ThreadPool)"
			_logQueue.Put((color, level, msg))
			_callbackQueue.Put(Pump)

def _logMsgToStderr(color, level, msg, quietThreshold):
	"""Print a message to stderr"""
	if shared_globals.verbosity < quietThreshold:
		if isinstance(msg, BytesType):
			msg = msg.decode("UTF-8")
		if threading.current_thread() == _logThread:
			_writeLog(color, level, msg, sys.stderr)
		else:
			assert _callbackQueue is not None, "Threaded logging requires a callback queue (shared with ThreadPool)"
			_logQueue.Put((color, level, msg, sys.stderr))
			_callbackQueue.Put(Pump)


def _formatMsg(msg, *args, **kwargs):
	showTime = kwargs.get("showTime")
	if showTime is True or showTime is None:
		curtime = time.time( ) - shared_globals.startTime
		msg = "{} ({})".format(PlatformUnicode(msg), FormatTime(curtime, False))
	if showTime is not None:
		del kwargs["showTime"]

	if not isinstance(msg, BytesType) and not isinstance(msg, StrType):
		return repr(msg)
	if args or kwargs:
		return msg.format(*args, **kwargs)
	return msg


def Error(msg, *args, **kwargs):
	"""
	Log an error message

	:param msg: Text to log
	:type msg: BytesType, StrType
	:param args: Args to str.format
	:type args: any
	:param kwargs: args to str.format
	:type kwargs: any
	"""
	msg = _formatMsg(msg, *args, **kwargs)
	_logMsg(Color.RED, "ERROR", msg, Verbosity.Mute)
	shared_globals.errors.append(msg)


def Warn(msg, *args, **kwargs):
	"""
	Log a warning

	:param msg: Text to log
	:type msg: BytesType, StrType
	:param args: Args to str.format
	:type args: any
	:param kwargs: args to str.format
	:type kwargs: any
	"""
	msg = _formatMsg(msg, *args, **kwargs)
	_logMsg(Color.YELLOW, "WARN", msg, Verbosity.Mute)
	shared_globals.warnings.append(msg)


def WarnNoPush(msg, *args, **kwargs):
	"""
	Log a warning, don't push it to the list of warnings to be echoed at the end of compilation.

	:param msg: Text to log
	:type msg: str
	:param args: Args to str.format
	:type args: any
	:param kwargs: args to str.format
	:type kwargs: any
	"""
	msg = _formatMsg(msg, *args, **kwargs)
	_logMsg(Color.YELLOW, "WARN", msg, Verbosity.Mute)


def Info(msg, *args, **kwargs):
	"""
	Log general info. This info only appears with -v specified.

	:param msg: Text to log
	:type msg: str
	:param args: Args to str.format
	:type args: any
	:param kwargs: args to str.format
	:type kwargs: any
	"""
	msg = _formatMsg(msg, *args, **kwargs)
	_logMsg(Color.CYAN, "INFO", msg, Verbosity.Normal)


def Build(msg, *args, **kwargs):
	"""
	Log info related to building

	:param msg: Text to log
	:type msg: str
	:param args: Args to str.format
	:type args: any
	:param kwargs: args to str.format
	:type kwargs: any
	"""
	msg = _formatMsg(msg, *args, **kwargs)
	_logMsg(Color.MAGENTA, "BUILD", msg, Verbosity.Quiet)


def Test(msg, *args, **kwargs):
	"""
	Log info related to testing - typically used by the unit test framework, but could be used
	by makefiles that run tests as part of a build

	:param msg: Text to log
	:type msg: str
	:param args: Args to str.format
	:type args: any
	:param kwargs: args to str.format
	:type kwargs: any
	"""
	msg = _formatMsg(msg, *args, **kwargs)
	_logMsg(Color.MAGENTA, "TEST", msg, Verbosity.Quiet)


def Linker(msg, *args, **kwargs):
	"""
	Log info related to linking

	:param msg: Text to log
	:type msg: str
	:param args: Args to str.format
	:type args: any
	:param kwargs: args to str.format
	:type kwargs: any
	"""
	msg = _formatMsg(msg, *args, **kwargs)
	_logMsg(Color.GREEN, "LINKER", msg, Verbosity.Quiet)


def Thread(msg, *args, **kwargs):
	"""
	Log info related to threads, particularly stalls caused by waiting on another thread to finish

	:param msg: Text to log
	:type msg: str
	:param args: Args to str.format
	:type args: any
	:param kwargs: args to str.format
	:type kwargs: any
	"""
	msg = _formatMsg(msg, *args, **kwargs)
	_logMsg(Color.BLUE, "THREAD", msg, Verbosity.Quiet)


def Install(msg, *args, **kwargs):
	"""
	Log info related to the installer

	:param msg: Text to log
	:type msg: str
	:param args: Args to str.format
	:type args: any
	:param kwargs: args to str.format
	:type kwargs: any
	"""
	msg = _formatMsg(msg, *args, **kwargs)
	_logMsg(Color.WHITE, "INSTALL", msg, Verbosity.Quiet)


def Command(msg, *args, **kwargs):
	"""
	Log info related to executing commands

	:param msg: Text to log
	:type msg: str
	:param args: Args to str.format
	:type args: any
	:param kwargs: args to str.format
	:type kwargs: any
	"""
	msg = _formatMsg(msg, *args, **kwargs)
	_logMsg(Color.YELLOW, "COMMAND", msg, Verbosity.Quiet)


def Custom(color, name, msg, *args, **kwargs):
	"""
	Log info related to some custom aspect of a build tool

	:param color: Color to log with, taken from csbuild.log.Color
	:type color: varies by platform. Options are documented in csbuild._utils.terminfo.TermColor, but exposed through log via log.Color
	:param name: Name of the log level (i.e., "BUILD", "INSTALL", etc)
	:type name: str
	:param msg: Text to log
	:type msg: str
	:param args: Args to str.format
	:type args: any
	:param kwargs: args to str.format
	:type kwargs: any
	"""
	msg = _formatMsg(msg, *args, **kwargs)
	_logMsg(color, name, msg, Verbosity.Quiet)

def Stdout(msg, *args, **kwargs):
	"""
	Log info related to the installer

	:param msg: Text to log
	:type msg: str
	:param args: Args to str.format
	:type args: any
	:param kwargs: args to str.format
	:type kwargs: any
	"""
	msg = _formatMsg(msg, showTime=False, *args, **kwargs)
	_logMsg(None, None, msg, Verbosity.Mute)

def Stderr(msg, *args, **kwargs):
	"""
	Log info related to the installer

	:param msg: Text to log
	:type msg: str
	:param args: Args to str.format
	:type args: any
	:param kwargs: args to str.format
	:type kwargs: any
	"""
	msg = _formatMsg(msg, showTime=False, *args, **kwargs)
	_logMsgToStderr(None, None, msg, Verbosity.Mute)
