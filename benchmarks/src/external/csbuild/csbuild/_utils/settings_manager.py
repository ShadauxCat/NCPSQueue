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
.. module:: settings_manager
	:synopsis: Manages persistent settings for csbuild
"""

from __future__ import unicode_literals, division, print_function

import os
import shutil
import threading

import sys

from . import PlatformBytes

try:
	import cPickle as pickle
except ImportError:
	import pickle
from .. import perf_timer, log

_sentinel = object()

class SettingsManager(object):
	"""
	Settings manager class that manages persistent settings, storing and reading from disk on demand.

	:param settingsDir: Directory to store the data in
	:type settingsDir: str
	"""
	def __init__(self, settingsDir):
		self.settings = {}
		self.settingsDir = settingsDir
		if not os.access(settingsDir, os.F_OK):
			os.makedirs(settingsDir)
		self.lock = threading.Lock()

	def Save(self, key, value):
		"""
		Save a value, which will be pickled at protocol 2 so it's supported by all python versions.

		:param key: Key to store as. Must be a legitimate filename.
		:type key: str
		:param value: The value to store
		:type value: any
		"""
		with perf_timer.PerfTimer("SettingsManager save"):
			#pylint: disable=not-context-manager
			self.settings[key] = value

	def Persist(self):
		"""
		Write all settings back to disk
		"""
		for key, value in self.settings.items():
			dirFromKey = os.path.join(self.settingsDir, os.path.dirname(key))
			if not os.access(dirFromKey, os.F_OK):
				os.makedirs(dirFromKey)
			log.Info("Storing settings for {}", os.path.join(self.settingsDir, key))
			with open(os.path.join(self.settingsDir, key), "wb") as f:
				pickle.dump(value, f, 2)
				f.flush()

	def Clear(self):
		"""
		Remove all persisted settings
		"""
		shutil.rmtree(self.settingsDir)

	def Get(self, key, default=None):
		"""
		Get a value from the settings store

		:param key: Key to load. Must be a legitimate filename.
		:type key: str
		:param default: The default if no stored value exists
		:type default: any
		:return: The loaded value, or default if not found
		:rtype: any
		"""
		with perf_timer.PerfTimer("SettingsManager load"):
			# Double-check lock pattern
			ret = self.settings.get(key, _sentinel)
			if ret is _sentinel:
				# pylint: disable=not-context-manager
				with self.lock:
					ret = self.settings.get(key, _sentinel)
					if ret is _sentinel:
						pathFromKey = os.path.join(self.settingsDir, key)
						if not os.access(pathFromKey, os.F_OK):
							self.settings[key] = default
							return self.settings[key]

						with open(pathFromKey, "rb") as f:
							data = f.read()
							if sys.version_info[0] == 2:
								data = data.replace(PlatformBytes("cUserString"), PlatformBytes("ccollections"))
								data = data.replace(PlatformBytes("cUserList"), PlatformBytes("ccollections"))
							ret = pickle.loads(data)

						self.settings[key] = ret
			return ret

	def Delete(self, key):
		"""
		Delete a value from the settings store if it exists. Nop if it doesn't.

		:param key: Key to delete. Must be a legitimate filename.
		:type key: str
		"""
		#pylint: disable=not-context-manager
		with self.lock:
			self.settings.pop(key, None)
			pathFromKey = os.path.join(self.settingsDir, key)
			if os.access(pathFromKey, os.F_OK):
				os.remove(pathFromKey)
