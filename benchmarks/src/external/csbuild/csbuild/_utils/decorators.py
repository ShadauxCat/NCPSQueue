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
.. module:: decorators
	:synopsis: Helpful utility decorators

.. moduleauthor:: Jaedyn K. Draper
"""

from __future__ import unicode_literals, division, print_function

import sys
import warnings

from . import StrType
from .._testing import testcase
from .. import perf_timer

if sys.version_info[0] >= 3:
	_typeType = type
	_classType = type
else:
	import types
	# pylint: disable=invalid-name
	_typeType = types.TypeType
	_classType = types.ClassType

NOT_SET = object()

def TypeChecked(**argtypes):
	"""
	**Decorator**
	Checks argtypes passed to a function at runtime and throws an exception if an unexpected type is received.

	Example::

		@TypeChecked(var1=str, var2=int, var3=(int, float, str), _return=None)
		def Func(var1, var2, var3):
			# Do stuff!

	:param argtypes: Keyword argument list of argtypes. Keywords must match the decorated function's parameters.
				The special keyword *_return* designates the return type.
				Each parameter must either specify a type or a tuple of argtypes.
				To explicitly accept all argtypes, pass arg=object
	:return: a type-checked wrapper for the function
	:rtype: function
	"""
	with perf_timer.PerfTimer("TypeChecked decorator"):
		argtypes = dict(**argtypes)

		def _wrapOuter(oldFunc):
			""" Outer decorator wrapper - set up the inner decorator """
			with perf_timer.PerfTimer("TypeChecked outer wrap"):
				# co_varnames includes both parameters and locals - trim it to just parameters
				varNames = oldFunc.__code__.co_varnames[0:oldFunc.__code__.co_argcount]

				# Check that all the types provided are actual types and that none of them reference nonexistent parameters
				for name, typ in argtypes.items():
					if not isinstance(typ, (_typeType, _classType, tuple)):
						raise TypeError("Parameters to TypeChecked must be type, or tuple of argtypes - not {}".format(typ))

					if isinstance(typ, tuple):
						for subtype in typ:
							if not isinstance(subtype, (_typeType, _classType)):
								raise TypeError("Tuple parameters to TypeChecked must contain only argtypes - not {}".format(subtype))

					if name == "_return":
						continue
					if name not in varNames:
						raise TypeError("Function {} has no parameter named '{}'".format(oldFunc.__name__, name))

				# Check that all the function's parameters are represented - for type checking, this is just a warning if they're not
				for name in varNames:
					if name == "self":
						continue
					if name not in argtypes:
						warnings.warn("Function {}: Parameter '{}' has no type assigned (use 'object' to accept all argtypes)".format(oldFunc.__name__, name))

				oldFunc.__types__ = argtypes
				oldFunc.__varNames__ = varNames

				def _wrap(*args, **kwargs):
					"""
					Inner wrapper - this function actually replaces the decorated function and is called every tim
					the decorated function is called. It checks all the type arguments before calling the decorated
					function and raises an exception if they don't match.
					"""
					with perf_timer.PerfTimer("Type checking"):
						for i, name in enumerate(varNames):
							argtype = argtypes.get(name, NOT_SET)

							if argtype is NOT_SET:
								continue

							if i < len(args):
								elem = args[i]
							else:
								elem = kwargs.get(name, NOT_SET)

							if elem != NOT_SET:
								if not isinstance(elem, argtype):
									raise TypeError("Argument '{}' is type {}, expected {}".format(name, elem.__class__, argtype))

					result = oldFunc(*args, **kwargs)

					with perf_timer.PerfTimer("Type checking"):
						returntype = argtypes.get('_return', NOT_SET)
						if returntype != NOT_SET:
							if not isinstance(result, returntype):
								raise TypeError("Function {} returned invalid return type {}; expected {}".format(oldFunc.__name__, type(result), returntype))
						return result
				return _wrap
		return _wrapOuter


def Overload(**argtypes):
	"""
	**Decorator**
	Allows multiple definitions of the same function with different type signatures, and selects the best one
	at runtime based on the argtypes passed to it. All functions that are put up for selection MUST be decorated.

	Example::

		@Overload(var1=str, var2=int)
		def Func2(var1, var2):
			print("STRINT", var1, var2)

		@Overload(var1=int, var2=str)
		def Func2(var1, var2):
			print("INTSTR", var1, var2)

		Func2(1, "2")
		>> INTSTR 1 2
		Func2("1", 2)
		>> STRINT 1 2

	:param argtypes: Keyword argument list of argtypes. Keywords must match the decorated function's parameters.
				The special keyword *_return* designates the return type, which cannot be used for overloads,
				but will be checked for correctness if specified.
				Each parameter may specify a type, a tuple of argtypes, or a value.
				To explicitly accept all argtypes, pass arg=object.
				If a value is passed rather than a type or tuple of argtypes, that value will provide an even more specific
				overload (for example, allowing the base case of a recursive function to be defined as an overload
				of the function that will be selected when, ex, param0=0)
	:return: A wrapper function that performs overload resolution and calls the correct function
	:rtype: function
	"""
	with perf_timer.PerfTimer("Overload decorator"):
		argtypes = dict(**argtypes)

		def _wrapOuter(oldFunc):
			""" Outer decorator wrapper - set up the inner decorator """

			# co_varnames includes both parameters and locals - trim it to just parameters

			varNames = oldFunc.__code__.co_varnames[0:oldFunc.__code__.co_argcount]

			# Check that all the types provided are actual types and that none of them reference nonexistent parameters
			for name, typ in argtypes.items():
				if isinstance(typ, tuple):
					for subtype in typ:
						if not isinstance(subtype, (_typeType, _classType)):
							raise TypeError("Tuple parameters to Overload must contain only argtypes - not {}".format(subtype))

				if name == "_return":
					continue
				if name not in varNames:
					raise TypeError("Overloaded function {} has no parameter {}".format(oldFunc.__name__, name))

			# Check that all the function's parameters are represented - for overloads, error if they're not
			for name in varNames:
				if name == "self":
					continue
				if name not in argtypes:
					raise TypeError("Overloaded function {}: Parameter {} has no type assigned (use 'object' to accept all argtypes)".format(oldFunc.__name__, name))

			oldFunc.__types__ = argtypes
			oldFunc.__varNames__ = varNames

			def _wrap(*args, **kwargs):
				"""
				Inner wrapper - this function actually replaces the decorated function and is called every tim
				the decorated function is called. It goes through all the decorated functions with this function's
				name and picks the one that most closely matches the provided arguments, if any.

				"Most closely" here means that if one function takes int, and one takes 0, 0 more closely matches
				0 than int does.
				"""

				# Set up a list of prioritized functions, giving them a match closeness score
				prioritizedFuncs = {}
				for func in Overload.funcs[oldFunc.__name__]:
					numArgsGiven = len(args) + len(kwargs)
					numArgsTaken = len(func.__varNames__)
					numDefaults = len(func.__defaults__) if func.__defaults__ is not None else 0
					# If the number of arguments provided doesn't match the number of parameters to this overload,
					# skip it
					if numArgsGiven > numArgsTaken or numArgsGiven < (numArgsTaken - numDefaults):
						continue

					disqualified = False
					priority = 0
					for key in kwargs:
						# If there are any keyword arguments provided that aren't accepted by this overload, skip it
						if key not in func.__varNames__:
							disqualified = True
							break
					if disqualified:
						continue

					# Quick eliminations out of the way, now the hard part... check all the types
					for i, name in enumerate(func.__varNames__):
						argtype = func.__types__.get(name)

						# pick the correct matching passed-in argument
						if i < len(args):
							elem = args[i]
						else:
							elem = kwargs.get(name, NOT_SET)

						# If the specified argument type is object, everything matches at the lowest priority
						if argtype is object:
							priority += 1
						elif isinstance(argtype, (_typeType, _classType)):
							# If the specified argument is a single type...
							if type(elem) is argtype: # pylint: disable=unidiomatic-typecheck
								# If the passed type is an exact match, this is a higher priority match
								priority += 3
							elif isinstance(elem, argtype):
								# Otherwise if the passed type's a subclass, middle priority
								priority += 2
							else:
								# If an element has been passed in that doesn't match the type, or no element's passed for
								# an argument with no default value, this overload is disqualified
								if elem is not NOT_SET or i < (numArgsTaken - numDefaults):
									disqualified = True
								break
						elif isinstance(argtype, tuple):
							# Otherwise this is a list of accepted types
							if isinstance(elem, argtype):
								# If the element matches, middle priority, same as subclass
								priority += 2
							else:
								# If an element has been passed in that doesn't match the type, or no element's passed for
								# an argument with no default value, this overload is disqualified
								if elem is not NOT_SET or i < (numArgsTaken - numDefaults):
									disqualified = True
								break
						else:
							# If the specified type is a VALUE and not a type, and the element is equal to it, this is
							# TOP priority!
							if elem == argtype:
								priority += 4
							else:
								disqualified = True
								break

					if not disqualified:
						# If we're not disqualified and something else has the same total priority as this, flag it as ambiguous
						# Otherwise put it in the priority map
						if priority in prioritizedFuncs:
							raise TypeError("Call to overloaded function {} is ambiguous: could not determine priority overload based on the provided arguments.".format(oldFunc.__name__))
						prioritizedFuncs.update({ priority : func })

				# Now we've built our prioritized function list. If anything's in it at all, pick the one with the highest
				# priority and execute. Otherwise, flag a "no viable overload"
				if prioritizedFuncs:
					orderedFuncs = sorted(prioritizedFuncs.items(), reverse=True)

					# Execute the function and check the return type
					result = orderedFuncs[0][1](*args, **kwargs)
					returntype = argtypes.get('_return')
					if returntype != NOT_SET:
						if isinstance(returntype, (_typeType, _classType, tuple)):
							if not isinstance(result, returntype):
								raise TypeError("Function {} returned invalid return type {}; expected {}".format(oldFunc.__name__, type(result), returntype))
						elif result != returntype:
							raise TypeError("Function {} returned invalid return value {}; expected {}".format(oldFunc.__name__, type(result), returntype))
					return result

				raise TypeError("No overload of {} found that matches the given arguments: {} {}".format(oldFunc.__name__, args if args else "", kwargs if kwargs else ""))

			# Back to the outer wrapper now! Everything from here down only happens once per instance of the decorator.
			# Create a persistent overload list as a part of /this/ function
			if not hasattr(Overload, "funcs"):
				Overload.funcs = {}

			# Add this function to the list
			if oldFunc.__name__ in Overload.funcs:
				funcs = Overload.funcs[oldFunc.__name__]
				numArgsTaken = len(oldFunc.__varNames__)
				numDefaults = len(oldFunc.__defaults__) if oldFunc.__defaults__ is not None else 0
				numNonDefaulted = numArgsTaken - numDefaults
				# Iterate through the functions to find anything that has the same non-defaulted signature
				for func in funcs:
					numOtherArgsTaken = len(func.__varNames__)
					numOtherDefaults = len(func.__defaults__) if func.__defaults__ is not None else 0
					numOtherNonDefaulted = numOtherArgsTaken - numOtherDefaults
					if numNonDefaulted != numOtherNonDefaulted:  # Different numnber of non-defaulted arguments, not a dupe
						continue

					differentKeywords = False
					differentPositions = False
					defaultsProblem = False
					# Determine if this function has either different keywords or the same keywords in different positions
					for i, name in enumerate(func.__varNames__):
						if i >= numNonDefaulted:
							defaultsProblem = True
							break

						argType = func.__types__.get(name)
						otherArgType = oldFunc.__types__.get(name)
						positionalArgType = oldFunc.__types__.get(oldFunc.__varNames__[i]) if i < numArgsTaken else None

						if not isinstance(argType, (_typeType, _classType, tuple)):
							argType = None
						if not isinstance(otherArgType, (_typeType, _classType, tuple)):
							otherArgType = None
						if not isinstance(positionalArgType, (_typeType, _classType, tuple)):
							positionalArgType = None

						if argType is not otherArgType:
							differentKeywords = True
						if positionalArgType is not argType:
							differentPositions = True
						if differentKeywords and differentPositions:
							break

					# If it has the same keywords in the same positions, start checking the types
					if not differentKeywords or not differentPositions:
						for i, name in enumerate(oldFunc.__varNames__):
							if i >= numNonDefaulted:
								defaultsProblem = True
								break

							argType = func.__types__.get(name)
							otherArgType = oldFunc.__types__.get(name)
							positionalArgType = oldFunc.__types__.get(oldFunc.__varNames__[i]) if i < numArgsTaken else None

							if not isinstance(argType, (_typeType, _classType, tuple)):
								argType = None
							if not isinstance(otherArgType, (_typeType, _classType, tuple)):
								otherArgType = None
							if not isinstance(positionalArgType, (_typeType, _classType, tuple)):
								positionalArgType = None

							if argType is not otherArgType:
								differentKeywords = True
							if positionalArgType is not argType:
								differentPositions = True
							if differentKeywords and differentPositions:
								break

					def _getName(val):
						if hasattr(val, "__name__"):
							return val.__name__
						return str(val)

					# Same positional arguments - error
					if not differentPositions:
						positionalKeywordSignature = []
						for i, name in enumerate(oldFunc.__varNames__):
							positionalKeywordSignature.append({name : _getName(oldFunc.__types__.get(name))})
						otherPositionalKeywordSignature = []
						for i, name in enumerate(func.__varNames__):
							otherPositionalKeywordSignature.append({name : _getName(func.__types__.get(name))})
						if defaultsProblem:
							raise TypeError(
								"Two or more overloads of {} share the same deduced positional signature except for defaulted parameters: "
								"{} and {}, with defaults starting at position {}: {} and {}".format(
									oldFunc.__name__,
									positionalKeywordSignature,
									otherPositionalKeywordSignature,
									numNonDefaulted+1,
									oldFunc.__defaults__,func.__defaults__
								)
							)
						raise TypeError(
								"Two or more overloads of {} share the same deduced positional signature: {} and {}".format(
									oldFunc.__name__,
									positionalKeywordSignature,
									otherPositionalKeywordSignature
								)
						)

					# Same keyword arguments - error
					if not differentKeywords:
						positionalKeywordSignature = []
						for i, name in enumerate(oldFunc.__varNames__):
							positionalKeywordSignature.append({name : _getName(oldFunc.__types__.get(name))})
						otherPositionalKeywordSignature = []
						for i, name in enumerate(func.__varNames__):
							otherPositionalKeywordSignature.append({name : _getName(func.__types__.get(name))})
						if defaultsProblem:
							raise TypeError(
								"Two or more overloads of {} share the same deduced keyword signature except for defaulted parameters: "
								"{} and {}, with defaults starting at position {}: {} and {}".format(
									oldFunc.__name__,
									positionalKeywordSignature,
									otherPositionalKeywordSignature,
									numNonDefaulted+1,
									oldFunc.__defaults__,
									func.__defaults__
								)
							)
						raise TypeError(
							"Two or more overloads of {} share the same deduced keyword signature: {} and {}".format(
								oldFunc.__name__,
								positionalKeywordSignature,
								otherPositionalKeywordSignature
							)
						)
				funcs.append(oldFunc)
			else:
				Overload.funcs[oldFunc.__name__] = [oldFunc]
			return _wrap
		return _wrapOuter


def MetaClass(meta):
	"""
	Decorator to enable metaclasses in a way that's compliant with both python 2 and python 3
	(and arguably nicer and more readable than both)

	:param meta: Class to decorate
	:type meta: any
	:return: The class with metaclass added to it
	:rtype: type
	"""
	def _wrap(cls):
		return meta(cls.__name__, cls.__bases__, dict(cls.__dict__))
	return _wrap

### UNIT TESTS ###

class TestTypeCheck(testcase.TestCase):
	"""Test for the TypeChecked decorator"""

	def setUp(self):
		Overload.funcs = {}

	# pylint: disable=unused-argument,unused-variable,invalid-name
	def testSimpleTypeCheck(self):
		"""Simple test that type checks work for built-in types"""
		@TypeChecked(var1=int, var2=StrType)
		def _simpleCheck(var1, var2):
			pass

		self.assertRaises(TypeError, _simpleCheck, "1", 2)
		self.assertRaises(TypeError, _simpleCheck, 1, 2)
		self.assertRaises(TypeError, _simpleCheck, "1", "2")
		_simpleCheck(1, "2")

	def testComplexTypeCheck(self):
		"""Test that type checks work when the type specified is a tuple or abstract base class"""
		import numbers
		@TypeChecked(var1=(int, StrType), var2=numbers.Number)
		def _tupleABCCheck(var1, var2):
			pass

		_tupleABCCheck(1, 2)
		_tupleABCCheck("1", 2)
		_tupleABCCheck(1, 2.0)
		_tupleABCCheck("1", 2.0)

	def testParamNone(self):
		"""Test that the value None passed as a type raises an exception"""
		with self.assertRaises(TypeError):
			@TypeChecked(var1=None)
			def _noneCheck(var1):
				pass

	def testParamInt(self):
		"""Test that a non-type value other than None raises an exception"""
		with self.assertRaises(TypeError):
			@TypeChecked(var1=1)
			def _noneCheck(var1):
				pass

	def testOldAndNewClasses(self):
		"""Test that both old-style and new-style classes are accepted and work properly"""
		class _oldClass: # pylint: disable=bad-option-value,old-style-class,no-init
			pass

		class _newClass(object):
			pass

		@TypeChecked(var1=_oldClass, var2=_newClass)
		def _classCheck(var1, var2):
			pass

		_classCheck(_oldClass(), _newClass())
		self.assertRaises(TypeError, _classCheck, _oldClass(), _oldClass())
		self.assertRaises(TypeError, _classCheck, _newClass(), _oldClass())
		self.assertRaises(TypeError, _classCheck, _newClass(), _newClass())

	def testInvalidVar(self):
		"""Test that a variable name specified that doesn't exist raises an exception"""
		with self.assertRaises(TypeError):
			@TypeChecked(var1=int)
			def _invalidVar(var2):
				pass


class TestOverload(testcase.TestCase):
	"""Test for the Overload decorator"""

	# pylint: disable=unused-argument,unused-variable,invalid-name,function-redefined
	def testSimpleOverloads(self):
		"""Test that overloads work in the general case and non-matching argument sets throw exceptions"""

		class _sharedLocals(object):
			intstr = False
			strint = False

		@Overload(arg1=int, arg2=StrType)
		def _simpleOverload(arg1, arg2):
			_sharedLocals.intstr = True

		@Overload(arg1=StrType, arg2=int)
		def _simpleOverload(arg1, arg2):
			_sharedLocals.strint = True

		_simpleOverload(1, "2")
		self.assertTrue(_sharedLocals.intstr)
		self.assertFalse(_sharedLocals.strint)
		_sharedLocals.intstr = False

		_simpleOverload("1", 2)
		self.assertTrue(_sharedLocals.strint)
		self.assertFalse(_sharedLocals.intstr)

		with self.assertRaises(TypeError):
			_simpleOverload("1", "2")

		with self.assertRaises(TypeError):
			_simpleOverload(1, 2)

	def testValueOverloads(self):
		"""Test that an overload on a value works and has higher priority than an overload on a type"""

		class _sharedLocals(object):
			zero = False
			one = False

		@Overload(arg1=0)
		def _simpleOverload(arg1):
			_sharedLocals.zero = True

		@Overload(arg1=int)
		def _simpleOverload(arg1):
			_sharedLocals.one = True

		_simpleOverload(1)
		self.assertTrue(_sharedLocals.one)
		self.assertFalse(_sharedLocals.zero)
		_sharedLocals.one = False

		_simpleOverload(0)
		self.assertTrue(_sharedLocals.zero)
		self.assertFalse(_sharedLocals.one)

	def testInvalidVar(self):
		"""Test that a variable name specified that doesn't exist raises an exception"""
		with self.assertRaises(TypeError):
			@Overload(var1=int)
			def _invalidVar(var2):
				pass

	def testDoubleOverload(self):
		"""Test that creating an overload with a signature that's already been made throws an exception"""
		with self.assertRaises(TypeError):
			@Overload(var1=int)
			def _doubleOverload(var1):
				pass
			@Overload(var1=int)
			def _doubleOverload(var1):
				pass
