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
.. module:: tests
	:synopsis: Test that output from multiple commands run at once is not interleaved

.. moduleauthor:: Jaedyn K. Draper
"""

from __future__ import unicode_literals, division, print_function

import sys
import threading

from csbuild._testing.functional_test import FunctionalTest
from csbuild import commands, log
from csbuild._utils import queue

# Pay no attention to the unit test behind the curtain.
# This test isn't really a functional test like the others.
# It's a unit test of commands.Run()
# However, given the way that needs to be tested, launching processes and checking output and return code,
# the test fits the functional test pattern better than the unit test pattern, so it's being shoehorned
# into a different place. Pay it no mind!
class NoInterleavedOutputTest(FunctionalTest):
	"""Ensure no interleaved output from commands"""
	# pylint: disable=invalid-name
	def setUp(self): #pylint: disable=arguments-differ
		self.lastValue = -1
		self.numTallies = 0
		self.callbackQueue = queue.Queue()

		#overriding stdout rather than specifying a callback
		#because callbacks are called in realtime, stdout printing is queued
		#this test is testing the latter, that the queueing works properly
		self.oldLogStdout = log.Stdout
		log.Stdout = self._stdoutOverride

		FunctionalTest.setUp(self, cleanAtEnd=False)

	def tearDown(self):
		log.Stdout = self.oldLogStdout
		FunctionalTest.tearDown(self)

	def _stdoutOverride(self, msg):
		self.oldLogStdout("            {}".format(msg))
		value = int(msg)
		self.numTallies += 1
		self.assertTrue(value == self.lastValue + 1 or (value == 0 and self.lastValue == 9))
		self.lastValue = value

	def RunMakeAndTally(self):
		"""
		Run the local makefile, tally the output to ensure it's not interleaved
		"""

		cmd = [sys.executable, "print_some_stuff.py"]

		returncode, _, _ = commands.Run(cmd)
		self.assertEqual(returncode, 0)
		self.callbackQueue.Put(commands.stopEvent)

	def test(self):
		"""Ensure no interleaved output from commands"""
		commands.queueOfLogQueues = queue.Queue()
		outputThread = threading.Thread(target=commands.PrintStaggeredRealTimeOutput)
		outputThread.start()

		threads = [threading.Thread(target=self.RunMakeAndTally) for _ in range(10)]

		log.SetCallbackQueue(self.callbackQueue)

		for thread in threads:
			thread.start()

		stopped = 0
		while True:
			callback = self.callbackQueue.GetBlocking()

			if callback is commands.stopEvent:
				stopped += 1
				if stopped == len(threads):
					break
				continue
			callback()

		for thread in threads:
			thread.join()

		commands.queueOfLogQueues.Put(commands.stopEvent)
		outputThread.join()

		log.SetCallbackQueue(None)
		self.assertEqual(self.lastValue, 9)
		self.assertEqual(self.numTallies, len(threads) * 10)
