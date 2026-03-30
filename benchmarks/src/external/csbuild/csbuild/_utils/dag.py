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
.. module:: dag
	:synopsis: class representing a directed acyclic graph

.. moduleauthor:: Jaedyn K. Draper
"""

from __future__ import unicode_literals, division, print_function

import sys

from collections import OrderedDict
from .._testing import testcase
from ..dependency import Dependency

class DAG(object):
	"""
	Directed acyclic graph class.

	:param keyFunc: Function to resolve an inserted object into a key. If not specified, the object itself is used.
	:type keyFunc: Callable
	"""
	def __init__(self, keyFunc=None):
		self._graph = OrderedDict()
		self._deferred = set()
		if keyFunc is None:
			keyFunc = lambda x: x
		self._keyFunc = keyFunc


	def Add(self, value, dependencies):
		"""
		Add an item into the graph

		:param value: The value to add
		:type value: any
		:param dependencies: List of keys that must precede this one in the graph
		:type dependencies: list[any]
		"""
		assert self._keyFunc(value) not in self._graph, "Duplicate item in dependency graph: {}".format(self._keyFunc(value))
		dependencies = [dep.name if isinstance(dep, Dependency) else dep for dep in dependencies]
		for dependency in dependencies:
			if dependency not in self._graph:
				self._deferred.add((value, tuple(dependencies)))
				return
		self._graph.update({self._keyFunc(value): value})
		while True:
			deletes = []
			for (otherValue, otherDependencies) in self._deferred:
				for dependency in otherDependencies:
					if dependency not in self._graph:
						break
				else:
					self._graph.update({self._keyFunc(otherValue):otherValue})
					deletes.append((otherValue, otherDependencies))
			if deletes:
				for delete in deletes:
					self._deferred.remove(delete)
			else:
				break


	def Valid(self):
		"""
		Check if the graph is valid

		:return: True if all dependencies have been resolved and none are circular, else False
		:rtype: bool
		"""
		return bool(not self._deferred)

	def __bool__(self):
		"""
		Check if the graph is valid

		:return: True if all dependencies have been resolved and none are circular, else False
		:rtype: bool
		"""
		return self.Valid()

	if sys.version_info[0] < 3:
		__nonzero__ = __bool__

	def __iter__(self):
		"""
		Iterate the items in the graph in an acceptable order such that dependencies are resolved before the things that
		depend on them.
		"""
		if not self.Valid():
			raise ValueError("Could not generate directed acyclic graph - unresolvable dependencies found in items: {}".format([self._keyFunc(x) for x, _ in self._deferred]))
		for val in self._graph.values():
			yield val

	def __len__(self):
		return len(self._graph) + len(self._deferred)

class TestDAG(testcase.TestCase):
	"""Test the DAG"""
	# pylint: disable=invalid-name

	def testDAG(self):
		"""Basic test - this should work"""
		dag = DAG()
		dag.Add(1, [2, 3, 4, 5])
		dag.Add(3, [4, 5])
		dag.Add(5, [])
		dag.Add(2, [3, 4, 5])
		dag.Add(4, [5])
		self.assertEqual(5, len(dag))
		l = list(dag)
		self.assertEqual(l, [5,4,3,2,1])

	def testCircularDependency(self):
		"""Circular dependency test, should fail"""
		dag = DAG()
		dag.Add(1, [2, 3, 4, 5])
		dag.Add(3, [4, 5])
		dag.Add(5, [1])
		dag.Add(2, [3, 4, 5])
		dag.Add(4, [5])
		self.assertFalse(dag.Valid())
		self.assertFalse(dag)
		self.assertEqual(5, len(dag))
		with self.assertRaises(ValueError):
			_ = list(dag)

	def testMissingDependency(self):
		"""Missing dependency test, should fail"""
		dag = DAG()
		dag.Add(1, [2, 3, 4, 5])
		dag.Add(3, [4, 5])
		dag.Add(5, [])
		dag.Add(2, [3, 4, 5])
		self.assertFalse(dag.Valid())
		self.assertFalse(dag)
		self.assertEqual(4, len(dag))
		with self.assertRaises(ValueError):
			_ = list(dag)

	def testKeyFunc(self):
		"""Test that the dag still works with a key function provided"""
		class _intWrap(object):
			def __init__(self, val):
				self.val = val

		dag = DAG(lambda a: a.val)
		dag.Add(_intWrap(1), [2, 3, 4, 5])
		dag.Add(_intWrap(3), [4, 5])
		dag.Add(_intWrap(5), [])
		dag.Add(_intWrap(2), [3, 4, 5])
		dag.Add(_intWrap(4), [5])
		self.assertEqual(5, len(dag))
		l = list(dag)
		self.assertEqual([a.val for a in l], [5,4,3,2,1])
