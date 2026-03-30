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
.. module:: ordered_set
	:synopsis: Provides a set implementation that keeps a strong order
"""

from __future__ import unicode_literals, division, print_function

import collections
from .._testing import testcase


class OrderedSet(object):
	"""
	An ordered set that keeps a strong order - all items inserted into the set remain in the set in the order they were inserted
	Much like (and in fact, implemented in terms of) collections.OrderedDict

	Other than that, semantics are identical to set. For details on this class's functions, see pylib docs for set.

	:param iterable: An iterable to insert elements into the set
	:type iterable: anything iterable
	"""
	# pylint: disable=invalid-name,missing-docstring
	def __init__(self, iterable=None):
		self.map = collections.OrderedDict()
		if iterable is not None:
			self.map.update([( x, None ) for x in iterable])

	def __len__(self):
		return len(self.map)

	def __contains__(self, key):
		return key in self.map

	def union(self, other):
		ret = OrderedSet(self.map.keys())
		ret.update(other)
		return ret

	def intersection(self, other):
		ret = OrderedSet(self.map.keys())
		ret.intersection_update(other)
		return ret

	def difference(self, other):
		ret = OrderedSet(self.map.keys())
		ret.difference_update(other)
		return ret

	def symmetric_difference(self, other):
		ret = OrderedSet(self.map.keys())
		ret.symmetric_difference_update(other)
		return ret

	def __and__(self, other):
		return self.intersection(other)

	def __or__(self, other):
		return self.union(other)

	def __sub__(self, other):
		return self.difference(other)

	def __xor__(self, other):
		return self.symmetric_difference(other)

	def __iter__(self):
		for key in self.map.keys():
			yield key

	def __reversed__(self):
		for key in reversed(list(self.map.keys())):
			yield key

	def __repr__(self):
		return "{{{}}}".format(", ".join([repr(key) for key in self.map.keys()]))

	def update(self, iterable):
		self.map.update([( x, None ) for x in iterable])

	def intersection_update(self, iterable):
		for key in list(self.map.keys()):
			if key not in iterable:
				del self.map[key]

	def difference_update(self, iterable):
		for key in iterable:
			if key in self.map:
				del self.map[key]

	def symmetric_difference_update(self, iterable):
		for key in iterable:
			if key in self.map:
				del self.map[key]
			else:
				self.map[key] = None

	def add(self, key):
		self.map[key] = None

	def remove(self, key):
		del self.map[key]

	def discard(self, key):
		try:
			del self.map[key]
		except:
			pass

	def pop(self):
		key = list(self.map.keys())[0]
		val = self.map[key]
		del self.map[key]
		return val

	def clear(self):
		self.map = collections.OrderedDict()


class TestOrderedSet(testcase.TestCase):
	"""Test the ordered set"""

	# pylint: disable=invalid-name
	def setUp(self):
		""" Set up the test """
		self.testset = OrderedSet([1,2])
		self.testset.add(3)
		self.testset.add(4)

	def testLen(self):
		"""Test len"""
		self.assertEqual(4, len(self.testset))

	def testContains(self):
		"""test contains"""
		self.assertIn(1, self.testset)
		self.assertIn(2, self.testset)
		self.assertIn(3, self.testset)
		self.assertIn(4, self.testset)
		self.assertNotIn(5, self.testset)

	def testUnion(self):
		"""test union"""
		otherset = OrderedSet([6,5,4,3])
		unionset = self.testset.union(otherset)
		self.assertEqual(6, len(unionset))
		self.assertEqual(list(unionset), [1,2,3,4,6,5])

	def testIntersection(self):
		"""test intersection"""
		otherset = OrderedSet([6,5,4,3])
		interset = self.testset.intersection(otherset)
		self.assertEqual(2, len(interset))
		self.assertEqual(list(interset), [3,4])

	def testDifference(self):
		"""test difference"""
		otherset = OrderedSet([6,5,4,3])
		diffset = self.testset.difference(otherset)
		self.assertEqual(2, len(diffset))
		self.assertEqual(list(diffset), [1,2])

	def testSymmetricDifference(self):
		"""test symmetric difference"""
		otherset = OrderedSet([6,5,4,3])
		diffset = self.testset.symmetric_difference(otherset)
		self.assertEqual(4, len(diffset))
		self.assertEqual(list(diffset), [1,2,6,5])

	def testAnd(self):
		"""test &"""
		otherset = OrderedSet([6,5,4,3])
		interset = self.testset  & otherset
		self.assertEqual(2, len(interset))
		self.assertEqual(list(interset), [3,4])

	def testOr(self):
		"""test |"""
		otherset = OrderedSet([6,5,4,3])
		unionset = self.testset | otherset
		self.assertEqual(6, len(unionset))
		self.assertEqual(list(unionset), [1,2,3,4,6,5])

	def testSub(self):
		"""test -"""
		otherset = OrderedSet([6,5,4,3])
		diffset = self.testset - otherset
		self.assertEqual(2, len(diffset))
		self.assertEqual(list(diffset), [1,2])

	def testXor(self):
		"""test ^"""
		otherset = OrderedSet([6,5,4,3])
		diffset = self.testset ^ otherset
		self.assertEqual(4, len(diffset))
		self.assertEqual(list(diffset), [1,2,6,5])

	def testIter(self):
		"""test iteration"""
		testList = [1,2,3,4]
		i = 0

		for item in self.testset:
			self.assertEqual(testList[i], item)
			i += 1

	def testReversed(self):
		"""test reverse"""
		self.assertEqual([4,3,2,1], list(reversed(self.testset)))

	def testUpdate(self):
		"""test update"""
		otherset = OrderedSet([6,5,4,3])
		self.testset.update(otherset)
		self.assertEqual(6, len(self.testset))
		self.assertEqual(list(self.testset), [1,2,3,4,6,5])

	def testIntersectionUpdate(self):
		"""test intersection update"""
		otherset = OrderedSet([6,5,4,3])
		self.testset.intersection_update(otherset)
		self.assertEqual(2, len(self.testset))
		self.assertEqual(list(self.testset), [3,4])

	def testDifferenceUpdate(self):
		"""test difference update"""
		otherset = OrderedSet([6,5,4,3])
		self.testset.difference_update(otherset)
		self.assertEqual(2, len(self.testset))
		self.assertEqual(list(self.testset), [1,2])

	def testSymmetricDifferenceUpdate(self):
		"""test symmetric difference update"""
		otherset = OrderedSet([6,5,4,3])
		self.testset.symmetric_difference_update(otherset)
		self.assertEqual(4, len(self.testset))
		self.assertEqual(list(self.testset), [1,2,6,5])

	def testAdd(self):
		"""test add"""
		self.testset.add(5)
		self.testset.add(0)
		self.assertEqual(6, len(self.testset))
		self.assertEqual(list(self.testset), [1,2,3,4,5,0])

	def testRemove(self):
		"""test remove"""
		self.testset.remove(2)
		self.assertEqual(3, len(self.testset))
		self.assertEqual(list(self.testset), [1,3,4])

	def testDiscard(self):
		"""test discard"""
		self.testset.discard(2)
		self.testset.discard(0)
		self.assertEqual(3, len(self.testset))
		self.assertEqual(list(self.testset), [1,3,4])

	def testPop(self):
		"""test pop"""
		self.testset.pop()
		self.assertEqual(3, len(self.testset))
		self.assertEqual(list(self.testset), [2,3,4])

	def testClear(self):
		"""test clear"""
		self.testset.clear()
		self.assertEqual(0, len(self.testset))
		self.assertEqual(list(self.testset), [])
