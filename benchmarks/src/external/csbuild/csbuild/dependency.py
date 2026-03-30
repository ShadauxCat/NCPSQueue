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
.. module:: dependency
	:synopsis: Utility class for the project dependency specification.

.. moduleauthor:: Zoe Bare
"""

from __future__ import unicode_literals, division, print_function

from ._utils.decorators import TypeChecked
from ._utils.string_abc import String

class Dependency(object):
	"""
	Project dependency specification with configurable properties to make it conditionally referenced at build time.

	:param name: Name of the dependency
	:type name: String

	:param includeToolchains: Explicit toolchains that will include this dependency; an empty set or `None` implies all toolchains.
	:type includeToolchains: set[str or bytes] or list[str or bytes] or tuple[str or bytes] or str or bytes or None

	:param includeArchitectures: Explicit architectures that will include this dependency; an empty set or `None` implies all architectures.
	:type includeArchitectures: set[str or bytes] or list[str or bytes] or tuple[str or bytes] or str or bytes or None

	:param includeTargets: Explicit build targets that will include this dependency; an empty set or `None` implies all build targets.
	:type includeTargets: set[str or bytes] or list[str or bytes] or tuple[str or bytes] or str or bytes or None

	:param excludeToolchains: Explicit toolchains that will exclude this dependency.
	:type excludeToolchains: set[str or bytes] or list[str or bytes] or tuple[str or bytes] or str or bytes or None

	:param excludeArchitectures: Explicit architectures that will exclude this dependency.
	:type excludeArchitectures: set[str or bytes] or list[str or bytes] or tuple[str or bytes] or str or bytes or None

	:param excludeTargets: Explicit build targets that will exclude this dependency.
	:type excludeTargets: set[str or bytes] or list[str or bytes] or tuple[str or bytes] or str or bytes or None
	"""
	@TypeChecked(
		name=str,
	 	includeToolchains=(set, list, tuple, String, type(None)),
		includeArchitectures=(set, list, tuple, String, type(None)),
		includeTargets=(set, list, tuple, String, type(None)),
		excludeToolchains=(set, list, tuple, String, type(None)),
		excludeArchitectures=(set, list, tuple, String, type(None)),
		excludeTargets=(set, list, tuple, String, type(None)))
	def __init__(self,
			name,
			includeToolchains=None,
			includeArchitectures=None,
			includeTargets=None,
			excludeToolchains=None,
			excludeArchitectures=None,
			excludeTargets=None):
		self._name = name
		self._includeToolchains = self._convertArgumentToSet(includeToolchains)
		self._includeArchitectures = self._convertArgumentToSet(includeArchitectures)
		self._includeTargets = self._convertArgumentToSet(includeTargets)
		self._excludeToolchains = self._convertArgumentToSet(excludeToolchains)
		self._excludeArchitectures = self._convertArgumentToSet(excludeArchitectures)
		self._excludeTargets = self._convertArgumentToSet(excludeTargets)

	@staticmethod
	def _convertArgumentToSet(arg):
		if arg is None or not arg:
			return set()
		if isinstance(arg, set):
			return arg
		if isinstance(arg, (list, tuple)):
			return set(arg)
		if isinstance(arg, String):
			return { arg }

		raise TypeError("Argument has unexpected type: {}".format(arg))

	def __repr__(self):
		return self._name

	@property
	def name(self): # pylint: disable=missing-function-docstring
		return self._name

	@TypeChecked(toolchainName=String, architectureName=String, targetName=String)
	def ShouldIncludeInBuild(self, toolchainName, architectureName, targetName):
		"""
		Determine if a given build configuration is allowed for this dependency.

		:param toolchainName: Configuration toolchain name.
		:type toolchainName: str or bytes

		:param architectureName: Configuration architecture name.
		:type architectureName: str or bytes

		:param targetName: Configuration build target name.
		:type targetName: str or bytes
		"""
		allowed = (not self._includeToolchains or toolchainName in self._includeToolchains) \
			and (not self._includeArchitectures or architectureName in self._includeArchitectures) \
			and (not self._includeTargets or targetName in self._includeTargets) \
			and toolchainName not in self._excludeToolchains \
			and architectureName not in self._excludeArchitectures \
			and targetName not in self._excludeTargets

		return allowed
