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
.. module:: thread_pool
	:synopsis: Thread pool and task manager class for performing parallel operations
			with callbacks on the main thread when they are complete

.. moduleauthor:: Jaedyn K. Draper
"""

from __future__ import unicode_literals, division, print_function

import functools
import sys
import threading
import inspect

from .. import log, perf_timer
from .._testing import testcase
from . import queue
from .decorators import TypeChecked
from .reraise import Reraise

if sys.version_info[0] >= 3:
	from collections.abc import Callable
else:
	from collections import Callable # pylint: disable=deprecated-class
	# pylint: disable=import-error

class ThreadedTaskException(Exception):
	"""
	Wraps another exception, allowing the other exception to be caught and handled, then rethrown.
	"""
	def __init__(self, exceptionObject, tb):
		Exception.__init__(self)
		self.exception = exceptionObject
		self.traceback = tb

	def __repr__(self):
		return "ThreadedTaskException: (" + type(self.exception).__name__ + ": " + repr(self.exception) + ")"

	def __str__(self):
		return "(" + type(self.exception).__name__ + ": " + str(self.exception) + ")"

	def Reraise(self):
		"""
		Reraise the wrapped exception so that
		 a new set of catch statements can be prepared
		"""
		Reraise(self.exception, self.traceback)


class ThreadPool(object):
	"""
	Thread Pool and Task Management class
	Allows tasks to be inserted into a queue in a thread-safe way from any thread
	The first available thread will then handle that task

	:param numThreads: Number of threads in the pool - must be positive
	:type numThreads: int
	:param callbackQueue: Queue to be used to pass completion callbacks back to the main thread
	:type callbackQueue: queue.Queue
	:param stopOnException: Stop processing tasks once any thread has received an exception.
	:type stopOnException: bool
	"""
	exitEvent = object()

	@TypeChecked(numThreads=int, callbackQueue=queue.Queue, stopOnException=bool)
	def __init__(self, numThreads, callbackQueue, stopOnException=True):

		assert numThreads > 0

		self.queue = queue.Queue()
		self.threads = [threading.Thread(target=self._threadRunner) for _ in range(numThreads)]
		self.callbackQueue = callbackQueue
		self.stopOnException = stopOnException
		self.excInfo = None
		self.abort = threading.Event()
		"""@type: queue.Queue"""

	def Start(self):
		"""
		Start all threads in the pool and begin executing tasks
		"""
		_ = [t.start() for t in self.threads]

	@TypeChecked(task=(Callable, tuple, type(None)), callback=(Callable, tuple, type(None)))
	def AddTask(self, task, callback):
		"""
		Add a task into the queue to be executed on the first available thread.
		This is safe to call from any thread, including threads currently executing tasks.

		:param task: Task to be executed on another thread - either a callable or a tuple of callable + args
		:type task: (Callable, *args)
		:param callback: Callback to be placed into the callback queue when this task is complete - either a callable or a tuple of callable + args
		:type callback: (Callable, *args)
		"""

		if isinstance(task, tuple):
			task = functools.partial(task[0], *(task[1:]))

		if isinstance(callback, tuple):
			callback = functools.partial(callback[0], *(callback[1:]))

		self.queue.Put((task, callback))

	def Stop(self):
		"""
		Stop and join all threads. All tasks currently in the queue will finish execution before it stops.
		"""

		for _ in range(len(self.threads)):
			self.queue.Put(ThreadPool.exitEvent)
		_ = [t.join() for t in self.threads]
		self.callbackQueue.Put(ThreadPool.exitEvent)

	def Abort(self):
		"""
		Abort execution, joining all threads without finishing the tasks in the queue.
		Anything currently executing will finish, but no new tasks will be started.
		This function will join all threads and return once all in-progress tasks are finished and all threads have stopped.
		"""
		self.abort.set()
		for _ in range(len(self.threads)):
			self.queue.Put(ThreadPool.exitEvent)
		_ = [t.join() for t in self.threads]
		self.callbackQueue.Put(ThreadPool.exitEvent)

	def _rethrowException(self, excInfo):
		Reraise(ThreadedTaskException(excInfo[1], excInfo[2]), excInfo[2])

	def _threadRunner(self):
		while True:
			with perf_timer.PerfTimer("Worker thread idle"):
				task = self.queue.GetBlocking()

			ret = None
			if task is ThreadPool.exitEvent:
				return
			if self.abort.is_set():
				return
			if self.stopOnException and self.excInfo is not None:
				return

			try:
				if task[0]:
					ret = task[0]()
			except:
				self.excInfo = sys.exc_info()

				self.callbackQueue.Put(functools.partial(self._rethrowException, sys.exc_info()))

				if self.stopOnException:
					self.callbackQueue.Put(self.Stop)
					return

			if task[1]:
				# Has to be nested because we have to rebind task[1] to a name in a different scope
				# Otherwise by the time this runs, task has probably changed to another value and we get invalid results
				def _makeCallback(callback, ret):
					def _callback():
						if isinstance(callback, functools.partial):
							try:
								argspec = inspect.getfullargspec(callback)
							except AttributeError:
								argspec = inspect.getargspec(callback.func) # pylint: disable=deprecated-method
							if argspec[1]:
								nargs = -1
							else:
								nargs = len(argspec[0]) - len(callback.func.args)
						else:
							try:
								argspec = inspect.getfullargspec(callback)
							except AttributeError:
								argspec = inspect.getargspec(callback) # pylint: disable=deprecated-method
							if argspec[1]:
								nargs = -1
							else:
								nargs = len(argspec[0])

						if isinstance(ret, tuple):
							if nargs == -1 or nargs == len(argspec[0]):
								callback(*ret)
								return
						if nargs == 1:
							callback(ret)
							return
						if nargs == 0:
							callback()
							return
						raise TypeError("Could not find a way to call {} with parameters {}".format(callback, ret))
					return _callback

				self.callbackQueue.Put(_makeCallback(task[1], ret))

### Unit Tests ###

class TestThreadPool(testcase.TestCase):
	"""Test the thread pool"""

	# pylint: disable=invalid-name
	def testThreadPool(self):
		"""Test that the thread pool works in the general case"""
		import time
		import random

		callbackQueue = queue.Queue()
		log.SetCallbackQueue(callbackQueue)
		pool = ThreadPool(4, callbackQueue)
		pool.Start()

		class _sharedLocals(object):
			count = 0
			iter = 0
			callbackCount = 0

		expectedCount = 0
		lock = threading.Lock()

		def _callback():
			_sharedLocals.callbackCount += 1
			if _sharedLocals.callbackCount % 100 == 0:
				log.Info("{} callbacks completed.", _sharedLocals.callbackCount)
			if _sharedLocals.callbackCount == 400:
				pool.Stop()

		def _incrementCount2(i):
			time.sleep(random.uniform(0.001, 0.0125))

			#pylint: disable=not-context-manager
			with lock:
				_sharedLocals.count += i
				_sharedLocals.iter += 1
				if _sharedLocals.iter % 25 == 0:
					log.Info("{} iterations completed.", _sharedLocals.iter)

		def _incrementCount(i):
			time.sleep(random.uniform(0.001, 0.0125))

			#pylint: disable=not-context-manager
			with lock:
				_sharedLocals.count += i
				_sharedLocals.iter += 1
				if _sharedLocals.iter % 25 == 0:
					log.Info("{} iterations completed.", _sharedLocals.iter)
			pool.AddTask((_incrementCount2, i+1), _callback)

		for i in range(200):
			pool.AddTask((_incrementCount, i), _callback)
			expectedCount += i
			expectedCount += i + 1

		while True:
			cb = callbackQueue.GetBlocking()
			if cb is ThreadPool.exitEvent:
				break
			cb()

		self.assertEqual(_sharedLocals.count, expectedCount)
		log.SetCallbackQueue(None)

	def testExceptionRethrown(self):
		"""Test that when an exception is thrown on a thread, all threads stop and that exception's rethrown on the main thread"""

		callbackQueue = queue.Queue()
		log.SetCallbackQueue(callbackQueue)
		pool = ThreadPool(4, callbackQueue)

		def _throwException():
			raise RuntimeError("Exception!")

		pool.AddTask(_throwException, None)
		pool.Start()

		caughtException = False
		while True:
			cb = callbackQueue.GetBlocking()

			if cb is ThreadPool.exitEvent:
				break

			try:
				cb()
			except ThreadedTaskException as e:
				self.assertTrue(isinstance(e.exception, RuntimeError))
				caughtException = True
				import traceback
				exc = traceback.format_exc()
				self.assertIn("_threadRunner", exc)
				self.assertIn("_throwException", exc)
			else:
				self.assertTrue(caughtException, "Exception was not thrown")

	def testReturnValues(self):
		"""Test that a callback can take a parameter and be told about the return value from the called function"""
		callbackQueue = queue.Queue()
		log.SetCallbackQueue(callbackQueue)
		pool = ThreadPool(4, callbackQueue)

		def _getTwo():
			return 2

		def _callbackTakesArg(self, a):
			self.assertEqual(2, a)

		def _callbackNoArg():
			pool.Stop()

		pool.AddTask(_getTwo, lambda x: _callbackTakesArg(self, x))
		pool.AddTask(_getTwo, _callbackNoArg)
		pool.Start()

		while True:
			cb = callbackQueue.GetBlocking()

			if cb is ThreadPool.exitEvent:
				break
			cb()
