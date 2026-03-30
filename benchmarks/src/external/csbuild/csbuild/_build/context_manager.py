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
.. module:: context_manager
	:synopsis: base context manager class

.. moduleauthor:: Jaedyn K. Draper
"""

from __future__ import unicode_literals, division, print_function

import csbuild
import sys
import types

if sys.version_info[0] >= 3:
	_typeType = type
	_classType = type
else:
	# pylint: disable=invalid-name
	_typeType = types.TypeType
	_classType = types.ClassType

class NestedContext(object):
	"""
	Represents a nested context, allowing context managers to be chained, a la csbuild.Toolchain("foo").Architecture("bar")

	:param cls: The ContextManager being nested
	:type cls: ContextManager
	:param currentContext: The ContextManager it's being nested into
	:type currentContext: ContextManager
	"""
	def __init__(self, cls, currentContext):
		self.cls = cls
		self.ctx = currentContext

	def __call__(self, *args, **kwargs):
		ret = self.cls(*args, **kwargs)
		# pylint: disable=protected-access
		ret._parentContext = self.ctx
		return ret

class MultiDataContext(object):
	"""Contains multiple pieces of data returned from a function - typically a list of functions to call."""
	def __init__(self, contexts):
		object.__setattr__(self, "inself", True)
		self._contexts = contexts
		self._previousResolver = None
		object.__setattr__(self, "inself", False)

	@property
	def contexts(self):
		"""Get access to the contexts used for this manager"""
		return self._contexts

	def __enter__(self):
		"""
		Enter the context, making the listed contexts active
		"""
		object.__setattr__(self, "inself", True)

		# pylint: disable=protected-access
		self._previousResolver = csbuild._resolver
		csbuild._resolver = self

		object.__setattr__(self, "inself", False)

	def __exit__(self, excType, excValue, traceback):
		"""
		Leave the context

		:param excType: type of exception thrown in the context (ignored)
		:type excType: type
		:param excValue: value of thrown exception (ignored)
		:type excValue: any
		:param traceback: traceback attached to the thrown exception (ignored)
		:type traceback: traceback
		:return: Always false
		:rtype: bool
		"""
		# pylint: disable=protected-access
		csbuild._resolver = self._previousResolver
		return False

	def __getattribute__(self, name):
		if object.__getattribute__(self, "inself"):
			return object.__getattribute__(self, name)

		contexts = object.__getattribute__(self, "_contexts")

		funcs = []
		for context in contexts:
			if hasattr(context, name):
				funcs.append(getattr(context, name))

		if funcs:
			def _wrapDataMethods(*args, **kwargs):
				rets = []
				with self:
					for func in funcs:
						rets.append(func(*args, **kwargs))
				return MultiDataContext(rets)

			return _wrapDataMethods

		return object.__getattribute__(self, name)

class ContextManager(object):
	"""
	Base type for a context manager, used to set context for project plan settings
	:param contexts: list of contexts to activate within this manager's scope
	:type contexts: tuple(tuple(str, tuple(str, bytes)))
	:param methodResolvers: List of objects on which to look for additional methods for, i.e., csbuild.Toolchain("tc").ToolchainSpecificFunction()
	:type methodResolvers: list(objects)
	"""

	methodResolvers = []

	def __init__(self, contexts, methodResolvers=None):
		object.__setattr__(self, "inself", True)
		self._contexts = contexts
		self._methodResolvers = methodResolvers
		self._previousResolver = None
		self._parentContext = None
		self._inContext = False
		object.__setattr__(self, "inself", False)

	@property
	def contexts(self):
		"""Get access to the contexts used for this manager"""
		return self._contexts

	@property
	def resolvers(self):
		"""Get access to the resolvers used for this manager"""
		return self._methodResolvers

	def __enter__(self):
		"""
		Enter the context, making the listed contexts active
		"""
		object.__setattr__(self, "inself", True)
		if self._parentContext is not None:
			object.__getattribute__(self._parentContext, "__enter__")()
		if self._contexts is not None:
			csbuild.currentPlan.EnterContext(*self._contexts)

		if self._methodResolvers:
			ContextManager.methodResolvers.append(self._methodResolvers)

			# pylint: disable=protected-access
			self._previousResolver = csbuild._resolver
			csbuild._resolver = self

		self._inContext = True

		object.__setattr__(self, "inself", False)

	def __exit__(self, excType, excValue, traceback):
		"""
		Leave the context

		:param excType: type of exception thrown in the context (ignored)
		:type excType: type
		:param excValue: value of thrown exception (ignored)
		:type excValue: any
		:param traceback: traceback attached to the thrown exception (ignored)
		:type traceback: traceback
		:return: Always false
		:rtype: bool
		"""
		object.__setattr__(self, "inself", True)

		if self._methodResolvers:
			# pylint: disable=protected-access
			csbuild._resolver = self._previousResolver
			ContextManager.methodResolvers.pop()

		if self._contexts is not None:
			csbuild.currentPlan.LeaveContext()

		if self._parentContext is not None:
			object.__getattribute__(self._parentContext, "__exit__")(excType, excValue, traceback)

		self._inContext = False

		object.__setattr__(self, "inself", False)
		return False

	def __getattribute__(self, name):
		if object.__getattribute__(self, "inself"):
			return object.__getattribute__(self, name)

		if object.__getattribute__(self, '_inContext') is False:
			with self:
				return getattr(self, name)

		if ContextManager.methodResolvers:
			funcs = set()

			for resolverList in ContextManager.methodResolvers:
				for resolver in resolverList:
					if hasattr(resolver, name):
						funcs.add(getattr(resolver, name))

			if funcs:
				def _wrapResolverMethods(*args, **kwargs):
					rets = []
					for func in funcs:
						rets.append(func(*args, **kwargs))
					if len(rets) == 1:
						return rets[0]
					if len(rets) > 1:
						return MultiDataContext(rets)
					return None

				return _wrapResolverMethods

		# pylint: disable=protected-access
		if hasattr(csbuild, name):
			obj = getattr(csbuild, name)
			if isinstance(obj, types.FunctionType):
				def _wrapCsbuildMethod(*args, **kwargs):
					with self:
						obj(*args, **kwargs)

				return _wrapCsbuildMethod

			if isinstance(obj, (_classType, _typeType)) and issubclass(obj, ContextManager):
				return NestedContext(obj, self)
			return obj

		return object.__getattribute__(self, name)
