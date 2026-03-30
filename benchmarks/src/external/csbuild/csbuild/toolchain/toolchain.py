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
.. module:: toolchain
	:synopsis: Mixin class to join tools together

.. moduleauthor:: Jaedyn K. Draper
"""

from __future__ import unicode_literals, division, print_function

import contextlib
import threading
import sys
import types

from .._utils import shared_globals
from . import Tool as ToolClass, CompileChecker
from .._utils import PlatformString, ordered_set
from .._utils.decorators import TypeChecked
from .._utils.string_abc import String
from .._testing import testcase
from .. import perf_timer

currentToolId = None

if sys.version_info[0] >= 3:
	_typeType = type
	_classType = type
else:
	# pylint: disable=invalid-name
	_typeType = types.TypeType
	_classType = types.ClassType

staticInitsRun = set()
overloadedStaticInits = set()

class InvalidFunctionCall(Exception):
	"""
	Exception indicating an invalid function call.
	"""
	pass

class Toolchain(object):
	"""
	Creates a toolchain mixin class from the given list of classes.
	This mixin class has the following special behaviors:

	* If two classes both inherit from the same class, variables initialized in the base class's __init__ will be shared
	  between all subclasses
	* Private functions and data members are specific to the class they're defined in, even if they share a name in
	  two different classes - the code will intelligently call the correct (intended) function based on the location
	  it's called from
	* Public functions will be called as a group - all tools that have a certain function on it will have that function
	  called when the toolchain's function of that name is called.

	:param projectSettings: Settings to initialize tool classes with
	:type projectSettings: dict
	:param classes: list of Tool classes
	:type classes: class inherited from Tool
	:param kwargs: Optional arguments:
	    *runInit* to disable initialization so that static methods may be called
		on platforms where full initialization may not work.
		*checkers* to provide a mapping of extension to CompileChecker instance
	:type kwargs: runInit: bool
	:return: generated Toolchain class
	:rtype: Toolchain
	"""
	def __new__(cls, projectSettings, *classes, **kwargs):
		with perf_timer.PerfTimer("Toolchain creation"):
			for cls in classes:
				assert issubclass(cls, ToolClass), "Toolchains must be composed only of classes that inherit from Tool"

			# Python 2 compatibility... python 3 allows keyword arguments after *args, but python 2 doesn't
			runInit = kwargs.pop("runInit", True)
			checkers = kwargs.pop("checkers", {})
			assert not kwargs, "Unsupported arguments to toolchain init: {}".format(kwargs.keys())
			defaultChecker = CompileChecker()

			with perf_timer.PerfTimer("Local data init"):
				# Keep track of some state data...
				class _classTrackrClass(object):
					def __init__(self):
						# List of classes that have had __init__ called on them.
						# Since base class data is shared, we don't want to initialize them more than once
						self.initialized = set()

						# List of inits that are already overloaded so we don't wrap them multiple times
						self.overloadedInits = set()

						# Mutable list of classes
						self.classes = ordered_set.OrderedSet()

						# Mutable list of bases
						self.bases = ordered_set.OrderedSet()

						# List of paths by which files can go through tools at various starting points.
						self.paths = {}

						# List of reachable extensions given currently active or pending tools
						self.reachability = {}

						# List of null input tools that have been processed
						self.activeClasses = ordered_set.OrderedSet()

						# List of compile checkers
						self.checkers = {}

				_classTrackr = _classTrackrClass()
				_classTrackr.checkers = checkers

				_threadSafeClassTrackr = threading.local()

				# The last class to have a public function called on it
				# This is used to resolve private function calls and private member variable access - only
				# those elements that exist on this class or its bases will be visible
				_threadSafeClassTrackr.lastClass = None

				# Limited class lookup table. When non-empty, only classes in this set will be
				# visible when performing member lookups
				_threadSafeClassTrackr.limit = ordered_set.OrderedSet()

				def _getLastClass():
					if hasattr(_threadSafeClassTrackr, "lastClass"):
						return _threadSafeClassTrackr.lastClass
					return None

				def _getLimit():
					if hasattr(_threadSafeClassTrackr, "limit"):
						return _threadSafeClassTrackr.limit
					return ordered_set.OrderedSet()

				@contextlib.contextmanager
				def Use(cls):
					"""
					Simple context manager to simplify scope management for the class tracker
					:param cls: The class to manage, or 'self' to access self variables
					:type cls: class, or Toolchain instance
					"""
					global currentToolId
					lastToolId = currentToolId
					currentToolId = [id(x) for x in cls.mro()]
					oldClass = _getLastClass()
					_threadSafeClassTrackr.lastClass = cls
					try:
						yield
					finally:
						_threadSafeClassTrackr.lastClass = oldClass
						currentToolId = lastToolId

				# Replace each class's __init__ function with one that will prevent double-init
				# and will ensure that _threadSafeClassTrackr.lastClass is set properly so that variables
				# initialize with the correct visibility
				def _setinit(base):
					# Use a variable on the function to prevent us from wrapping this over and over
					if base.__init__ not in _classTrackr.overloadedInits:
						oldinit = base.__init__

						for superbase in list(base.mro())[1:]:
							if superbase is object:
								break
							if hasattr(oldinit, '__func__'):
								if hasattr(superbase.__init__, '__func__') and oldinit.__func__ is superbase.__init__.__func__:
									base.__oldInit__ = oldinit
									return
							else:
								if not hasattr(superbase.__init__, '__func__') and oldinit is superbase.__init__:
									base.__oldInit__ = oldinit
									return

						def _initwrap(self, *args, **kwargs):
							# Don't re-init if already initialized
							if base not in _classTrackr.initialized:
								_classTrackr.initialized.add(base)
								# Track the current class for __setattr__
								with Use(base):
									oldinit(self, *args, **kwargs)

						# Replace existing init and set the memoization value
						base.__init__ = _initwrap
						base.__oldInit__ = oldinit
						_classTrackr.overloadedInits.add(base.__init__)
					if base.__static_init__ not in overloadedStaticInits:
						oldstaticinit = base.__static_init__

						for superbase in list(base.mro())[1:]:
							if superbase is object:
								break
							if oldstaticinit is superbase.__static_init__:
								return

						@staticmethod
						def _staticinitwrap(*args, **kwargs):
							# Don't re-init if already initialized
							if oldstaticinit not in staticInitsRun:
								staticInitsRun.add(oldstaticinit)
								oldstaticinit(*args, **kwargs)
						base.__static_init__ = _staticinitwrap
						base.__old_static_init__ = oldstaticinit
						base.__old_static_init_owner__ = base
						overloadedStaticInits.add(base.__static_init__)

			# Collect a list of all the base classes
			for cls in classes:
				assert (cls.inputFiles is None or cls.inputFiles or cls.inputGroups or cls.crossProjectInputGroups), "Tool {} has no inputs set".format(cls.__name__)
				assert cls.outputFiles, "Tool {} has no outputs set".format(cls.__name__)
				# mro() - "method resolution order", which happens to also be a list of all classes in the inheritance
				# tree, including the class itself (but we only care about its base classes
				for base in cls.mro():
					if base is cls:
						continue
					# Replace the base class's __init__ so we can track members properly
					if runInit:
						_setinit(base)
					if base is ToolClass:
						break
					_classTrackr.bases.add(base)

			# Create paths for each tool, showing the total path a file will take from this tool to its final output
			for cls in classes:
				needAnotherPass = True
				path = ordered_set.OrderedSet()
				while needAnotherPass:
					needAnotherPass = False
					outputs = set(cls.outputFiles)
					for cls2 in classes:
						if cls2 is cls:
							continue

						if cls2 in path:
							continue

						if cls2.inputFiles is not None:
							for inputFile in cls2.inputFiles:
								if inputFile in outputs:
									path.add(cls2)
									outputs.update(cls2.outputFiles)
									needAnotherPass = True
						for inputFile in cls2.inputGroups:
							if inputFile in outputs:
								path.add(cls2)
								outputs.update(cls2.outputFiles)
								needAnotherPass = True
				_classTrackr.paths[cls] = path


			_classTrackr.classes = ordered_set.OrderedSet(classes)
			_classTrackr.activeClasses = ordered_set.OrderedSet(classes)

			# Set up a map of class to member variable dict
			# All member variables will be stored here instead of in the class's __dict__
			# This is what allows for both sharing of base class values, and separation of
			# derived class values that share the same name, so they don't overwrite each other
			classValues = {cls : {} for cls in _classTrackr.classes | _classTrackr.bases}

			with perf_timer.PerfTimer("Template class construction"):
				# Create a class so that we can call methods on that class
				class LimitView(object):
					"""Represents a limited view into a toolchain"""
					# The constructor takes the list of tools to limit to - i.e., toolchain.Tool(SomeClass, OtherClass)
					def __init__(self, obj, *tools):
						self.obj = obj

						# Ensure resolution order of these tools is the same as the classes themselves
						if len(tools) > 1:
							self.tools = ordered_set.OrderedSet()
							for cls in classes:
								for tool in tools:
									if cls == tool or issubclass(cls, tool):
										self.tools.add(tool)
										break
								if len(tools) == len(self.tools):
									break
						else:
							self.tools = ordered_set.OrderedSet(tools)

					# When asked for an attribute, set the class tracker's limit set and then retrieve the attribute
					# from the toolchain class (this class) that generated the LimitView. Resolution will be limited
					# to the tools provided above.
					def __getattr__(self, item):
						_threadSafeClassTrackr.limit = self.tools

						try:
							val = getattr(self.obj, item)
						except:
							_threadSafeClassTrackr.limit = ordered_set.OrderedSet()
							raise

						def _limit(*args, **kwargs):
							try:
								return val(*args, **kwargs)
							finally:
								_threadSafeClassTrackr.limit = ordered_set.OrderedSet()

						_limit.__name__ = item

						if isinstance(val, (types.MethodType, types.FunctionType)):
							return _limit

						_threadSafeClassTrackr.limit = ordered_set.OrderedSet()
						return val

				class ReadOnlySettingsView(object):
					"""
					Represents a read-only, class-scoped view into a project's settings dictionary.
					:param settingsDict: Settings
					:type settingsDict: dict
					"""
					# pylint: disable=invalid-name
					# Names here are to match dict interface
					def __init__(self, settingsDict):
						self._settingsDict = settingsDict

					def __getitem__(self, item):
						"""
						Get item from the dictionary
						:param item: the key to search for
						:type item: any
						:return: the item
						:rtype: any
						:return: Whatever was placed in the settings dictionary
						:rtype: any
						:raises KeyError: if the key is not present in the dictionary within the calling class's scope
						"""
						for toolId in currentToolId:
							key = "{}!{}".format(toolId, item)
							if key in self._settingsDict:
								return self._settingsDict[key]
						raise KeyError(item)

					def items(self):
						"""
						Iterate the key,value tuple pairs in the dictionary
						"""
						for key, value in self._settingsDict.items():
							for toolId in currentToolId:
								if key.startswith("{}!".format(toolId)):
									yield key.split("!", 1)[1], value

					def keys(self):
						"""
						Iterate the keys in the dictionary
						"""
						for key in self._settingsDict.keys():
							for toolId in currentToolId:
								if key.startswith("{}!".format(toolId)):
									yield key.split("!", 1)[1]

					def __iter__(self):
						"""
						Iterate the keys in the dictionary
						"""
						for key in self._settingsDict.keys():
							for toolId in currentToolId:
								if key.startswith("{}!".format(toolId)):
									yield key.split("!", 1)[1]

					def __contains__(self, item):
						"""
						Check if a key is in the dictionary
						:param item: key to check
						:type item: any
						:return: true if in, false otherwise
						:rtype: bool
						"""
						for toolId in currentToolId:
							key = "{}!{}".format(toolId, item)
							if key in self._settingsDict:
								return True
						return False

					def get(self, item, default):
						"""
						Get the item from the dict. If not present, return default
						:param item: Key to search for
						:type item: any
						:param default: default value to return
						:type default: any
						:return: the value, or default
						:rtype: any
						"""
						for toolId in currentToolId:
							key = "{}!{}".format(toolId, item)
							if key in self._settingsDict:
								return self._settingsDict[key]
						return default

					def values(self):
						"""
						Iterate the values in the dictionary
						"""
						for key, value in self._settingsDict.items():
							for toolId in currentToolId:
								if key.startswith("{}!".format(toolId)):
									yield value

					def __len__(self):
						"""
						Get number of items in the dictionary
						:return: count of items
						:rtype: int
						"""
						length = 0
						for key in self._settingsDict.keys():
							for toolId in currentToolId:
								if key.startswith("{}!".format(toolId)):
									length += 1
									break
						return length

				class ToolchainTemplate(object):
					"""
					Template class that provides the methods for the toolchain class.
					This class is never instantiated, its methods are just copied to the dynamically-created toolchain class below
					This is a hacky hack to get around the fact that python2 doesn't support the syntax
					class Toolchain(*classes)
					to give the class dynamically-created base classes (which is required because they need to all share the
					same, and type-appropriate, self object)
					"""
					def __init__(self):
						if runInit:
							# Initialize all dynamically created bases.
							for cls in _classTrackr.classes:
								actualStaticInitMethod = cls.__static_init__
								if hasattr(cls, "__old_static_init__") and cls.__old_static_init_owner__ is cls:
									actualStaticInitMethod = cls.__old_static_init__
								if actualStaticInitMethod not in staticInitsRun:
									cls.__static_init__()
								with Use(cls):
									cls.__init__(self, ReadOnlySettingsView(projectSettings))
							_threadSafeClassTrackr.lastClass = None

							for base in _classTrackr.bases:
								base.__init__ = base.__oldInit__
								del base.__oldInit__
								#base.__static_init__ = base.__old_static_init__
								#del base.__old_static_init__

					@TypeChecked(tool=(_classType, _typeType))
					def Use(self, tool):
						"""
						Enter a tool context, must be called before calling any functions that were directly pulled from the tool.
						i.e.,::
							with toolchain.Use(tool):
								tool.Run(toolchain, *args)
						:param tool: The tool context to enter
						:type tool: type
						:returns: Context manager to be used with a 'with' statement
						:rtype: context manager
						"""
						return Use(tool)

					@TypeChecked(tool=(_classType, _typeType))
					def CreateReachability(self, tool):
						"""
						Create reachability info for a tool as it's about to be used.
						The tool does not have to actively be in the task queue, this should be called every time an input
						is assigned to a tool, whether it's being processed immediately or being marked as pending.
						:param tool: The tool to mark reachability for
						:type tool: type
						"""
						for output in tool.outputFiles:
							_classTrackr.reachability.setdefault(output, 0)
							_classTrackr.reachability[output] += 1

						for otherTool in _classTrackr.paths[tool]:
							for output in otherTool.outputFiles:
								_classTrackr.reachability.setdefault(output, 0)
								_classTrackr.reachability[output] += 1

					@TypeChecked(tool=(_classType, _typeType))
					def ReleaseReachability(self, tool):
						"""
						Releases reachability info for a tool, marking one instance of the tool finished.
						Note that for group inputs, this should be released as many times as it was created (i.e., if every
						input called CreateReachability, then it needs to also be released once per input)
						:param tool: The tool to release reachability for
						:type tool: type
						"""
						for output in tool.outputFiles:
							_classTrackr.reachability.setdefault(output, 0)
							_classTrackr.reachability[output] -= 1
							assert _classTrackr.reachability[output] >= 0, "Cannot release reachability without creating it"

						for otherTool in _classTrackr.paths[tool]:
							for output in otherTool.outputFiles:
								_classTrackr.reachability.setdefault(output, 0)
								_classTrackr.reachability[output] -= 1
								assert _classTrackr.reachability[output] >= 0, "Cannot release reachability without creating it"

					def HasAnyReachability(self):
						"""
						Check if any builds have started that didn't finish, if anything at all is reachable.
						:return: True if reachable, False otherwise
						:rtype: bool
						"""
						for val in _classTrackr.reachability.values():
							if val != 0:
								return True
						return False

					@TypeChecked(extension=String)
					def IsOutputActive(self, extension):
						"""
						Check whether an output of the given extension is capable of being generated.
						:param extension:
						:type extension: str, bytes
						:return: Whether or not the input is active
						:rtype: bool
						"""
						return _classTrackr.reachability.get(extension, 0) != 0

					@TypeChecked(tool=(_classType, _typeType), extension=String)
					def CanCreateOutput(self, tool, extension):
						"""
						Check whether a tool is capable of ever creating a given output, even indirectly through other tools
						:param tool: The tool to check
						:type tool: type
						:param extension: The extension to check
						:type extension: str, bytes
						:return: Whether or not the tool can create that output
						:rtype: bool
						"""
						if extension in tool.outputFiles:
							return True
						for otherTool in _classTrackr.paths[tool]:
							if extension in otherTool.outputFiles:
								return True
						return False

					def GetAllTools(self):
						"""
						Get the full list of tools in this toolchain
						:return: Tool list
						:rtype: ordered_set.OrderedSet
						"""
						return _classTrackr.classes

					def GetActiveTools(self):
						"""
						Get the full list of active tools in this toolchain
						:return: Tool list
						:rtype: ordered_set.OrderedSet
						"""
						return _classTrackr.activeClasses

					@TypeChecked(tool=(_typeType, _classType))
					def DeactivateTool(self, tool):
						"""
						Remove the specified tool from the active tool list. This is used internally when processing
						null tools to ensure they don't get processed multiple times. You should NOT use this in a
						makefile - instead, you should use RemoveTool

						:param tool: tool to remove
						:type tool: type
						"""
						_classTrackr.activeClasses.remove(tool)

					@TypeChecked(tool=(_typeType, _classType))
					def IsToolActive(self, tool):
						"""
						Return whether or not the specified tool is active

						:param tool: tool to remove
						:type tool: type
						:return: Whether or not the tool is active
						:rtype: bool
						"""
						return tool in _classTrackr.activeClasses

					@TypeChecked(extension=(String, type(None)), generatingTools=(set, type(None)))
					def GetToolsFor(self, extension, generatingTools=None):
						"""
						Get all tools that take a given input. If any generatingTools are specified, they will be excluded from the result.

						:param extension: The extension of the file to be fed to the new tools
						:type extension: str, bytes
						:param generatingTools: The tools that generated this input
						:type generatingTools: set[class] or None
						:return: A set of all tools that can take this input as group or individual inputs.
							It's up to the caller to inspect the object to determine which type of input to provide.
							It's also up to the caller to not call group input tools until IsOutputActive() returns False
							for ALL of that tool's group inputs.
						:rtype: ordered_set.OrderedSet[type]
						"""
						ret = ordered_set.OrderedSet()
						for cls in _classTrackr.activeClasses:
							if generatingTools and cls in generatingTools:
								continue

							if extension is None and cls.inputFiles is None:
								if cls.exclusive:
									return ordered_set.OrderedSet([cls])
								ret.add(cls)
							elif cls.inputFiles is not None and extension in cls.inputFiles:
								if cls.exclusive:
									return ordered_set.OrderedSet([cls])
								ret.add(cls)

						return ret

					@TypeChecked(extension=String, generatingTools=(set, type(None)))
					def GetGroupToolsFor(self, extension, generatingTools=None):
						"""
						Get all tools that take a given group input. If any generatingTools are specified, they will be excluded from the result.

						:param extension: The extension of the file to be fed to the new tools
						:type extension: str, bytes
						:param generatingTools: The tools that generated this input
						:type generatingTools: set[class] or None
						:return: A set of all tools that can take this input as group or individual inputs.
							It's up to the caller to inspect the object to determine which type of input to provide.
							It's also up to the caller to not call group input tools until IsOutputActive() returns False
							for ALL of that tool's group inputs.
						:rtype: set[type]
						"""
						ret = ordered_set.OrderedSet()
						for cls in _classTrackr.classes:
							if generatingTools and cls in generatingTools:
								continue

							for dep in cls.dependencies:
								if self.IsOutputActive(dep):
									continue

							if extension in cls.inputGroups:
								if cls.exclusive:
									return ordered_set.OrderedSet([cls])
								ret.add(cls)

						return ret

					@TypeChecked(_return=set)
					def GetSearchExtensions(self):
						"""
						Return the full list of all extensions handled as inputs by any tool in the toolchain.
						:return: Set of all extensions
						:rtype: set[String]
						"""
						ret = set()
						for cls in _classTrackr.classes:
							if cls.inputFiles is not None:
								ret |= cls.inputFiles
							ret |= cls.inputGroups
						return ret


					def __setattr__(self, name, val):
						lastClass =  _getLastClass()
						limit = _getLimit()
						if not lastClass and len(limit) == 1:
							for dummy in limit:
								with Use(dummy):
									setattr(self, name, val)
									return

						assert lastClass is not None, "Setting attributes is not supported on Toolchain instances. " \
							"Use toolchain.Tool(FooTool) to limit to a single tool before setting attributes."
						if lastClass is self:
							object.__setattr__(self, name, val)
							return

						cls = lastClass

						# Iterate all the base classes until we find one that's already set this value.
						# If we don't find one that's set this value, this value is being initialized and should
						# be placed within the scope of the class that's initializing it. That class and its children
						# will then be able to see it, but its bases and siblings (classes that share a common base)
						# will not.
						for base in lastClass.mro():
							if base == ToolClass:
								break
							if name in classValues[base]:
								cls = base
						classValues[cls][name] = val

					def Tool(self, *args):
						"""
						Obtain a LimitView object that allows functions to be run only on specific tools

						:param args: List of classes to limit function execution on
						:type args: class
						:return: limit view object
						:rtype: LimitView
						"""
						return LimitView(self, *args)

					@TypeChecked(tool=(_typeType, _classType))
					def AddTool(self, tool):
						"""
						Add a new tool to the toolchain. This can only be used by a toolchain initialized with
						runInit = False to add that tool to the static method resolution; a toolchain initialized
						with runInit = True is finalized and cannot have new tools added to it

						:param tool: Class inheriting from Tool
						:type tool: type
						"""
						assert not runInit, "AddTool can't be called from this context"
						assert tool not in _classTrackr.classes, "Tool {} has already been added".format(tool)

						from .. import currentPlan
						currentPlan.AddToSet("tools", tool)

						for base in cls.mro():
							if base is cls:
								continue
							if base is ToolClass:
								break
							# Replace the base class's __init__ so we can track members properly
							if runInit:
								_setinit(base)
							_classTrackr.bases.add(base)
							classValues.setdefault(base, {})

						classValues[tool] = {}

						_classTrackr.classes.add(tool)

						if tool.supportedArchitectures is not None:
							shared_globals.allArchitectures.update(set(tool.supportedArchitectures))

						object.__setattr__(self, "__class__", type(PlatformString("Toolchain"), tuple(_classTrackr.classes), dict(ToolchainTemplate.__dict__)))

					@TypeChecked(tool=(_typeType, _classType))
					def RemoveTool(self, tool):
						"""
						Removes a tool from the toolchain. This can be used in a makefile to remove tools within
						certain contexts, such as on a specific platform, or to remove default tools, such as
						the built-in C++ linker tools.

						:param tool: Class inheriting from Tool
						:type tool: type
						"""
						assert not runInit, "RemoveTool can't be called from this context"
						assert tool in _classTrackr.classes, "Tool {} has not been added".format(tool)

						from .. import currentPlan
						currentPlan.AddToSet("disabledTools", tool)

						_classTrackr.classes.remove(tool)

						object.__setattr__(self, "__class__", type(PlatformString("Toolchain"), tuple(_classTrackr.classes), dict(ToolchainTemplate.__dict__)))


					@TypeChecked(extension=String, checker=CompileChecker)
					def AddChecker(self, extension, checker):
						"""
						Add a compile checker for a given extension.

						:param extension: The extension this checker applies to
						:type extension: str
						:param checker: The CompileChecker instance to be used for files with this extension
						:type checker: CompileChecker
						"""
						assert not runInit, "AddChecker can't be called from this context"

						from .. import currentPlan
						currentPlan.UpdateDict("checkers", {extension: checker})
						_classTrackr.checkers[extension] = checker

					@TypeChecked(extension=String)
					def GetChecker(self, extension):
						"""
						Get the checker for a given extension. If none has been registered, returns a default CompileChecker instance

						:param extension: The extension to check
						:type extension: str
						:return: The checker to use
						:rtype: CompileChecker
						"""
						return _classTrackr.checkers.get(extension, defaultChecker)

					def __deepcopy__(self, memo):
						memo[id(self)] = self
						return self

					def __getattribute__(self, name):
						with perf_timer.PerfTimer("Toolchain attribute resolution"):
							if name[0] == "$":
								name = name[1:]
								for cls in _classTrackr.classes | _classTrackr.bases:
									if cls.__name__ == name:
										return self.Tool(cls)
								raise AttributeError("The requested tool '{}' was not found in this toolchain.".format(name))

							if hasattr(ToolchainTemplate, name):
								# Anything implemented in ToolchainTemplate has priority over things implemented elsewhere
								# Return these things as actions on the toolchain itself rather than on its tools.
								return object.__getattribute__(self, name)

							lastClass = _getLastClass()
							limit = _getLimit()
							if len(limit) == 1 and shared_globals.runMode == shared_globals.RunMode.GenerateSolution:
								cls = list(limit)[0]
								if hasattr(cls, name):
									sentinel = object()
									val = sentinel
									for cls2 in cls.mro():
										if name in cls2.__dict__:
											val = cls2.__dict__[name]
											break
									if not isinstance(val, (types.FunctionType, types.MethodType, property)):
										for cls in _classTrackr.classes:
											if cls in shared_globals.allGeneratorTools:
												limit.add(cls)

							if not lastClass and len(limit) == 1:
								for dummy in limit:
									with Use(dummy):
										return getattr(self, name)

							if lastClass:
								# If we only have one class to look at, we can shortcut a little bit.
								# Also we can give access to instance methods and instance data that we can't give access to with
								# multiple classes in view.

								if lastClass is self:
									return object.__getattribute__(self, name)

								# Iterate the class's mro looking for the first one that has this name present for it.
								# This starts with the class itself and then goes through its bases
								for cls in lastClass.mro():
									if cls == ToolClass:
										break
									if name in classValues[cls]:
										return classValues[cls][name]

								# If we didn't find it there, then look for it on the class itself
								# This is either a function, method, or static variable, not an instance variable.
								# Would love to guarantee this is a function...
								# But for some reason python lets you access statics through self, so whatever...
								cls = lastClass
								if hasattr(cls, name):
									# Have to use __dict__ instead of getattr() because otherwise we can't identify static methods
									# See http://stackoverflow.com/questions/14187973/python3-check-if-method-is-static
									sentinel = object()
									val = sentinel
									for cls2 in cls.mro():
										if name in cls2.__dict__:
											val = cls2.__dict__[name]
											break
									assert val is not sentinel, "this shouldn't happen"
									if isinstance(val, property):
										return val.__get__(self)
									if isinstance(val, (staticmethod, classmethod)):
										return val.__get__(cls)
									if isinstance(val, (types.FunctionType, types.MethodType)):
										assert runInit, "Cannot call non-static methods of class {} from this context!".format(cls.__name__)
										return types.MethodType(val, self)
									return val

								if hasattr(object, name) or hasattr(ToolClass, name):
									return object.__getattribute__(self, name)
								raise AttributeError("'{}' object has no attribute '{}'".format(cls.__name__, name))

							# For public variables we want to return a wrapper function that calls all
							# matching functions. This should definitely be a function. If it's not a function,
							# things will not work.
							def _runMultiFunc(*args, **kwargs):
								functions = {}

								# Iterate through all classes and collect functions that match this name
								# We'll keep a list of all the functions that match, but only call each matching
								# function once. And when we call it we'll use the most base class we find that
								# has it - which should be the one that defined it - and only call each one once
								# (so if there are two subclasses of a base that base's functions won't get called twice)
								if limit:
									classes = limit
									if shared_globals.runMode == shared_globals.RunMode.GenerateSolution:
										for cls in _classTrackr.classes:
											if cls in shared_globals.allGeneratorTools:
												classes.add(cls)
								else:
									classes = _classTrackr.classes
								for cls in classes:
									if hasattr(cls, name):
										# Have to use __dict__ instead of getattr() because otherwise we can't identify static methods
										# See http://stackoverflow.com/questions/14187973/python3-check-if-method-is-static
										func = None
										for cls2 in cls.mro():
											if name in cls2.__dict__:
												func = cls2.__dict__[name]
												break
										assert func is not None, "this shouldn't happen"
										if func not in functions or issubclass(functions[func], cls):
											functions[func] = cls

								# Having collected all functions, iterate and call them
								for func, cls in functions.items():
									with Use(cls):
										func.__get__(cls)(*args, **kwargs)

							hasNonFunc = False
							if limit:
								classes = limit
							else:
								classes = _classTrackr.classes
							found = False
							for cls in classes:
								if hasattr(cls, name):
									# Have to use __dict__ instead of getattr() because otherwise we can't identify static methods
									# See http://stackoverflow.com/questions/14187973/python3-check-if-method-is-static
									func = None
									found = True
									for cls2 in cls.mro():
										if name in cls2.__dict__:
											func = cls2.__dict__[name]
											break

									assert func is not None, "this shouldn't happen"
									if isinstance(func, (types.FunctionType, types.MethodType, property)):
										raise InvalidFunctionCall(
											"Function call is invalid. '{}' is an instance method and is being called on a toolchain with more than one tool in its view. "
											"Only staticmethods and classmethods are automatically bundled, non-static methods must be called with toolchain.Tool(FooTool).BarMethod()"
											.format(name)
										)
									if not isinstance(func, staticmethod) and not isinstance(func, classmethod):
										hasNonFunc = True

							if hasNonFunc:
								values = {}
								for cls in classes:
									if hasattr(cls, name):
										# Have to use __dict__ instead of getattr() because otherwise we can't identify static methods
										# See http://stackoverflow.com/questions/14187973/python3-check-if-method-is-static
										val = None
										clsContainingVal = None
										for cls2 in cls.mro():
											if name in cls2.__dict__:
												val = cls2.__dict__[name]
												clsContainingVal = cls2
												break
										assert val is not None, "this shouldn't happen"
										if clsContainingVal in values:
											continue
										if values:
											raise AttributeError(
												"Toolchain attribute {} is ambiguous (exists on multiple tools). Try accessing on the class directly, or through toolchain.Tool(class)".format(name)
											)
										values[clsContainingVal] = val
								return values.popitem()[1]

							# Finding one tool without this function present on it is not an error.
							# However, if no tools had this function, that is an error - let python internals
							# throw us an AttributeError
							if not found:
								return object.__getattribute__(self, name)

							return _runMultiFunc

			with perf_timer.PerfTimer("Final toolchain creation"):
				return type(PlatformString("Toolchain"), classes, dict(ToolchainTemplate.__dict__))()

	################################################################################
	################################################################################
	### Stub functions for the sake of making code complete work.                ###
	### See above for actually implementations in ToolchainTemplate.             ###
	################################################################################
	################################################################################

	@contextlib.contextmanager
	@TypeChecked(tool=(_classType, _typeType))
	def Use(self, tool):
		"""
		Enter a tool context, must be called before calling any functions that were directly pulled from the tool.
		i.e.,::
			with toolchain.Use(tool):
				tool.Run(toolchain, *args)
		:param tool: The tool context to enter
		:type tool: type
		:returns: Context manager to be used with a 'with' statement
		:rtype: context manager
		"""
		pass

	@TypeChecked(tool=(_classType, _typeType))
	def CreateReachability(self, tool):
		"""
		Create reachability info for a tool as it's about to be used.
		The tool does not have to actively be in the task queue, this should be called every time an input
		is assigned to a tool, whether it's being processed immediately or being marked as pending.
		:param tool: The tool to mark reachability for
		:type tool: type
		"""
		pass

	@TypeChecked(tool=(_classType, _typeType))
	def ReleaseReachability(self, tool):
		"""
		Releases reachability info for a tool, marking one instance of the tool finished.
		Note that for group inputs, this should be released as many times as it was created (i.e., if every
		input called CreateReachability, then it needs to also be released once per input)
		:param tool: The tool to release reachability for
		:type tool: type
		"""
		pass

	def HasAnyReachability(self):
		"""
		Check if any builds have started that didn't finish, if anything at all is reachable.
		:return: True if reachable, False otherwise
		:rtype: bool
		"""
		pass

	@TypeChecked(extension=String)
	def IsOutputActive(self, extension):
		"""
		Check whether an output of the given extension is capable of being generated.
		:param extension:
		:type extension: str, bytes
		:return: Whether or not the input is active
		:rtype: bool
		"""

	@TypeChecked(tool=(_classType, _typeType), extension=String)
	def CanCreateOutput(self, tool, extension):
		"""
		Check whether a tool is capable of ever creating a given output, even indirectly through other tools
		:param tool: The tool to check
		:type tool: type
		:param extension: The extension to check
		:type extension: str, bytes
		:return: Whether or not the tool can create that output
		:rtype: bool
		"""

	def GetAllTools(self):
		"""
		Get the full list of tools in this toolchain
		:return: Tool list
		:rtype: ordered_set.OrderedSet
		"""
		pass

	def GetActiveTools(self):
		"""
		Get the full list of active tools in this toolchain
		:return: Tool list
		:rtype: ordered_set.OrderedSet
		"""
		pass

	@TypeChecked(tool=(_typeType, _classType))
	def DeactivateTool(self, tool):
		"""
		Remove the specified tool from the active tool list. This is used internally when processing
		null tools to ensure they don't get processed multiple times. You should NOT use this in a
		makefile - instead, you should use RemoveTool

		:param tool: tool to remove
		:type tool: type
		"""
		pass

	@TypeChecked(tool=(_typeType, _classType))
	def IsToolActive(self, tool):
		"""
		Return whether or not the specified tool is active

		:param tool: tool to remove
		:type tool: type
		:return: Whether or not the tool is active
		:rtype: bool
		"""
		pass

	@TypeChecked(extension=String, generatingTools=(set, type(None)))
	def GetToolsFor(self, extension, generatingTools=None):
		"""
		Get all tools that take a given input. If any generatingTools are specified, they will be excluded from the result.

		:param extension: The extension of the file to be fed to the new tools
		:type extension: str, bytes
		:param generatingTools: The tools that generated this input
		:type generatingTools: set[class] or None
		:return: A set of all tools that can take this input as group or individual inputs.
			It's up to the caller to inspect the object to determine which type of input to provide.
			It's also up to the caller to not call group input tools until IsOutputActive() returns False
			for ALL of that tool's group inputs.
		:rtype: set[type]
		"""
		pass

	@TypeChecked(extension=String, generatingTools=(set, type(None)))
	def GetGroupToolsFor(self, extension, generatingTools=None):
		"""
		Get all tools that take a given group input. If any generatingTools are specified, they will be excluded from the result.

		:param extension: The extension of the file to be fed to the new tools
		:type extension: str, bytes
		:param generatingTools: The tool that generated this input
		:type generatingTools: set[class] or None
		:return: A set of all tools that can take this input as group or individual inputs.
			It's up to the caller to inspect the object to determine which type of input to provide.
			It's also up to the caller to not call group input tools until IsOutputActive() returns False
			for ALL of that tool's group inputs.
		:rtype: set[type]
		"""
		pass

	@TypeChecked(_return=set)
	def GetSearchExtensions(self):
		"""
		Return the full list of all extensions handled as inputs by any tool in the toolchain.
		:return: Set of all extensions
		:rtype: set[String]
		"""
		pass

	def Tool(self, *args):
		"""
		Obtain a LimitView object that allows functions to be run only on specific tools

		:param args: List of classes to limit function execution on
		:type args: class
		:return: limit view object
		:rtype: LimitView
		"""
		pass

	@TypeChecked(tool=(_typeType, _classType))
	def AddTool(self, tool):
		"""
		Add a new tool to the toolchain. This can only be used by a toolchain initialized with
		runInit = False to add that tool to the static method resolution; a toolchain initialized
		with runInit = True is finalized and cannot have new tools added to it

		:param tool: Class inheriting from Tool
		:type tool: type
		"""
		pass

	@TypeChecked(tool=(_typeType, _classType))
	def RemoveTool(self, tool):
		"""
		Removes a tool from the toolchain. This can be used in a makefile to remove tools within
		certain contexts, such as on a specific platform, or to remove default tools, such as
		the built-in C++ linker tools.

		:param tool: Class inheriting from Tool
		:type tool: type
		"""
		pass

	@TypeChecked(extension=String, checker=CompileChecker)
	def AddChecker(self, extension, checker):
		"""
		Add a compile checker for a given extension.

		:param extension: The extension this checker applies to
		:type extension: str
		:param checker: The CompileChecker instance to be used for files with this extension
		:type checker: CompileChecker
		"""
		pass

	@TypeChecked(extension=String)
	def GetChecker(self, extension):
		"""
		Get the checker for a given extension. If none has been registered, returns a default CompileChecker instance

		:param extension: The extension to check
		:type extension: str
		:return: The checker to use
		:rtype: CompileChecker
		"""
		pass

class TestToolchainMixin(testcase.TestCase):
	"""Test the toolchain mixin"""
	# pylint: disable=invalid-name

	def setUp(self):
		"""Test the toolchain mixin"""
		# pylint: disable=missing-docstring
		global staticInitsRun
		staticInitsRun = set()
		# pylint: disable=protected-access
		ToolClass._initialized = False

		self.maxDiff = None

		class _sharedLocals(object):
			baseInitialized = 0
			derived1Initialized = 0
			derived2Initialized = 0
			baseStaticInitialized = 0
			derived1StaticInitialized = 0
			derived2StaticInitialized = 0
			doBaseThingCalledInBase = 0
			doBaseThing2CalledInBase = 0
			overloadFnCalledInBase = 0
			overloadFnCalledInDerived1 = 0
			overloadFnCalledInDerived2 = 0
			setSomeValCalledInBase = 0
			baseInternalThingCalledInBase = 0
			basePrivateThingCalledInBase = 0
			derived1AccessSomeValResult = None
			derived1AccessTestResult = None
			derived2AccessSomeValResult = None
			derived2AccessTestResult = None
			derived1PrivateThingCalled = 0
			derived1SameNameThingCalled = 0
			derived2PrivateThingCalled = 0
			derived2SameNameThingCalled = 0
			doDerived1ThingCalled = 0
			doDerived2ThingCalled = 0
			doBaseThingCalledInDerived2 = 0
			baseInternalThingCalledInDerived1 = 0
			basePrivateThingCalledInDerived2 = 0
			doMultiThingCalledInDerived1 = 0
			doMultiThingCalledInDerived2 = 0
			derived1Static = 0
			derived2Static = 0


		class _base(ToolClass):
			inputFiles = None
			outputFiles = {""}

			class MyEnum(object):
				"""Demo enum class"""
				Foo = 1
				Bar = 2

			testStaticVar = 3

			def __init__(self, projectSettings):
				_sharedLocals.baseInitialized += 1
				self._someval = 0
				ToolClass.__init__(self, projectSettings)

			@staticmethod
			def __static_init__():
				ToolClass.__static_init__()
				_sharedLocals.baseStaticInitialized += 1

			def Run(self, inputProject, inputFile):
				pass

			@staticmethod
			def DoBaseThing():
				_sharedLocals.doBaseThingCalledInBase += 1

			@staticmethod
			def DoBaseThing2():
				_sharedLocals.doBaseThing2CalledInBase += 1

			@staticmethod
			def OverloadedFn():
				_sharedLocals.overloadFnCalledInBase += 1

			def SetSomeVal(self):
				_sharedLocals.setSomeValCalledInBase += 1
				self._someval = 12345

			def _baseInternalThing(self):
				_sharedLocals.baseInternalThingCalledInBase += 1

			def _basePrivateThing(self):
				self._baseInternalThing()
				_sharedLocals.basePrivateThingCalledInBase += 1


		class _derived1(_base):
			def __init__(self, projectSettings):
				_sharedLocals.derived1Initialized += 1
				self._test = 1
				_base.__init__(self, projectSettings)

			@staticmethod
			def __static_init__():
				_base.__static_init__()
				_sharedLocals.derived1StaticInitialized += 1

			def Derived1CallInternals(self):
				self._basePrivateThing()
				self._derived1PrivateThing()
				self._sameNamePrivateThing()

			def Derived1AccessSomeVal(self):
				_sharedLocals.derived1AccessSomeValResult = self._someval
				_sharedLocals.derived1AccessTestResult = self._test

			@staticmethod
			def OverloadedFn():
				_sharedLocals.overloadFnCalledInDerived1 += 1

			def _baseInternalThing(self):
				_sharedLocals.baseInternalThingCalledInDerived1 += 1

			def _derived1PrivateThing(self):
				_sharedLocals.derived1PrivateThingCalled += 1

			def _sameNamePrivateThing(self):
				_sharedLocals.derived1SameNameThingCalled += 1

			@staticmethod
			def DoDerived1Thing():
				_sharedLocals.doDerived1ThingCalled += 1

			@staticmethod
			def DoMultiThing():
				_sharedLocals.doMultiThingCalledInDerived1 += 1

			@staticmethod
			def Derived1Static():
				_sharedLocals.derived1Static += 1

		class _derived2(_base):
			def __init__(self, projectSettings):
				_sharedLocals.derived2Initialized += 1
				self._test = 2
				_base.__init__(self, projectSettings)

			@staticmethod
			def __static_init__():
				_base.__static_init__()
				_sharedLocals.derived2StaticInitialized += 1

			def Derived2CallInternals(self):
				self._basePrivateThing()
				self._derived2PrivateThing()
				self._sameNamePrivateThing()

			def Derived2AccessSomeVal(self):
				_sharedLocals.derived2AccessSomeValResult = self._someval
				_sharedLocals.derived2AccessTestResult = self._test

			@staticmethod
			def OverloadedFn():
				_sharedLocals.overloadFnCalledInDerived2 += 1

			@staticmethod
			def DoBaseThing():
				_sharedLocals.doBaseThingCalledInDerived2 += 1

			def Derived2SetSomeVal(self):
				self._someval = 54321

			def _basePrivateThing(self):
				self._baseInternalThing()
				_sharedLocals.basePrivateThingCalledInDerived2 += 1

			def _derived2PrivateThing(self):
				_sharedLocals.derived2PrivateThingCalled += 1

			def _sameNamePrivateThing(self):
				_sharedLocals.derived2SameNameThingCalled += 1

			@staticmethod
			def DoDerived2Thing():
				_sharedLocals.doDerived2ThingCalled += 1

			@staticmethod
			def DoMultiThing():
				_sharedLocals.doMultiThingCalledInDerived2 += 1

			@staticmethod
			def Derived2Static():
				_sharedLocals.derived2Static += 1

		self.expectedState = {key: val for key, val in _sharedLocals.__dict__.items() if not key.startswith("_")}
		self._sharedLocals = _sharedLocals
		self._derived1 = _derived1
		self._derived2 = _derived2
		self._base = _base

		self.mixin = Toolchain({}, _derived1, _derived2)
		self.assertChanged(
			baseInitialized=1,
			derived1Initialized=1,
			derived2Initialized=1,
			baseStaticInitialized=1,
			derived1StaticInitialized=1,
			derived2StaticInitialized=1,
		)

	def assertUnchanged(self):
		"""Assert that the state dict has not changed"""
		#Set the expected changes on our expected state and assert that the changed expected state
		#(including the previous values in that state) matches the actual state
		actualState = {key: val for key, val in self._sharedLocals.__dict__.items() if not key.startswith("_")}
		self.assertEqual(self.expectedState, actualState)

	def assertChanged(self, **kwargs):
		"""Assert that the listed changes (and ONLY the listed changes) have occurred in the state dict"""
		#Set the expected changes on our expected state and assert that the changed expected state
		#(including the previous values in that state) matches the actual state
		for key, val in kwargs.items():
			self.assertNotEqual(self.expectedState[key], val)
		self.expectedState.update(kwargs)
		actualState = {key: val for key, val in self._sharedLocals.__dict__.items() if not key.startswith("_")}
		self.assertEqual(self.expectedState, actualState)

	def testStaticFunctionCalls(self):
		"""Test that static method calls with runInit=False work correctly"""
		mixin2 = Toolchain({}, self._derived1, runInit=False)
		mixin2.AddTool(self._derived2)

		self.assertEqual(mixin2.MyEnum.Foo, 1)
		self.assertEqual(mixin2.MyEnum.Bar, 2)
		self.assertEqual(mixin2.testStaticVar, 3)

		#Assert init ran once - during setUp - and only once.
		#i.e., mixin2 should not have run init!
		self.assertEqual(1, self._sharedLocals.baseInitialized)
		self.assertEqual(1, self._sharedLocals.derived1Initialized)
		self.assertEqual(1, self._sharedLocals.derived2Initialized)
		mixin2.Derived1Static()
		self.assertChanged(derived1Static = 1)
		mixin2.Derived2Static()
		self.assertChanged(derived2Static = 1)

	def testPrivateFunctionCalls(self):
		"""Test that internal private function calls work with a variety of inheritance scenarios"""
		# Call internal functions on derived 1
		# This should call _basePrivateThing on the base class and _baseInternalThing on the child
		# And it should call Derived1PrivateThing on Derived1
		# And it should call the function named _sameNamePrivateThing defined in Derived1, but NOT the one defined in Derived2
		self.mixin.Tool(self._derived1).Derived1CallInternals()

		self.assertChanged(
			basePrivateThingCalledInBase=1,
			derived1PrivateThingCalled=1,
			derived1SameNameThingCalled=1,
			baseInternalThingCalledInDerived1=1
		)

		# Call internal functions on derived 2
		# This should call _basePrivateThing on the derived class and _baseInternalThing on the base
		# And it should call Derived2PrivateThing on Derived2
		# And it should call the function named _sameNamePrivateThing defined in Derived2, but NOT the one defined in Derived1
		self.mixin.Tool(self._derived2).Derived2CallInternals()

		self.assertChanged(
			baseInternalThingCalledInBase=1,
			derived2PrivateThingCalled=1,
			derived2SameNameThingCalled=1,
			basePrivateThingCalledInDerived2=1
		)

	def testMultiFunctionCall(self):
		"""Test that calling a function with multiple implementations calls all implementations"""
		# This should call the functioned defined on the base class by way of Derived1
		# as well as the overload defined on Derived2
		self.mixin.DoBaseThing()

		self.assertChanged(
			doBaseThingCalledInBase=1,
			doBaseThingCalledInDerived2=1
		)

	def testFunctionCallDeduplication(self):
		"""Test that a given function implementation is only called once"""
		# This should call DoBaseThing2 on the base class and should only call it ONCE
		self.mixin.DoBaseThing2()

		self.assertChanged(
			doBaseThing2CalledInBase=1
		)

	def testBaseClassFunctionNotCalledIfOverloaded(self):
		"""Test that a base class implementation is not called if all derived classes override it"""
		# This should call the overloaded functions on both Derived1 and Derived2 and should NOT call the base implementation
		self.mixin.Tool(self._derived1).OverloadedFn()
		self.mixin.Tool(self._derived2).OverloadedFn()

		self.assertChanged(
			overloadFnCalledInDerived1=1,
			overloadFnCalledInDerived2=1
		)

	def testAccessSharedData(self):
		"""Test that accessing data initialized by the base class accesses shared data, and
		that accessing data initialized by the child class is isolated from other classes using the same name"""
		# This should access self._someVal and self._test in Derived1 as set up by their constructors
		# self._test should be 1 because it should see the Derived1 instance of it, and not the Derived2 instance
		self.mixin.Tool(self._derived1).Derived1AccessSomeVal()

		self.assertChanged(
			derived1AccessSomeValResult=0,
			derived1AccessTestResult=1
		)

		# This should access self._someVal and self._test in Derived2 as set up by their constructors
		# self._test should be 2 because it should see the Derived2 instance of it, and not the Derived1 instance
		self.mixin.Tool(self._derived2).Derived2AccessSomeVal()

		self.assertChanged(
			derived2AccessSomeValResult=0,
			derived2AccessTestResult=2
		)

	def testChangeSharedDataInBase(self):
		"""Test that changes to shared data by the base class are seen by all children"""
		# Set self._someVal to 12345 in the base class. This should affect both child classes
		self.mixin.Tool(self._base).SetSomeVal()

		self.assertChanged(
			setSomeValCalledInBase=1,
		)

		# Access values again via Derived1. self.someVal should be 12345 now.
		self.mixin.Tool(self._derived1).Derived1AccessSomeVal()

		self.assertChanged(
			derived1AccessSomeValResult=12345,
			derived1AccessTestResult=1,
		)

		# Access values again via Derived2. Just like with Derived1, self.someVal should be 12345 now.
		self.mixin.Tool(self._derived2).Derived2AccessSomeVal()

		self.assertChanged(
			derived2AccessSomeValResult=12345,
			derived2AccessTestResult=2,
		)

	def testCallNonStaticMethodWithoutLimitViewThrows(self):
		"""Test that trying to call an instance method without defining a single class for scope throws an exception"""
		with self.assertRaises(InvalidFunctionCall):
			self.mixin.SetSomeVal()

		with self.assertRaises(InvalidFunctionCall):
			self.mixin.Derived1AccessSomeVal()

	def testChangeSharedDataInDerived(self):
		"""Test that changes to shared data by a derived class are seen by other derived classes"""
		# Set SomeVal by way of Derived2, which despite being a child class should still set the base class instance
		self.mixin.Tool(self._derived2).Derived2SetSomeVal()

		# Access values again via Derived1. self.someVal should be 54321 now as set by Derived2.
		self.mixin.Tool(self._derived1).Derived1AccessSomeVal()

		self.assertChanged(
			derived1AccessSomeValResult=54321,
			derived1AccessTestResult=1,
		)

		# Access values again via Derived2. Just like with Derived1, self.someVal should be 54321 now.
		self.mixin.Tool(self._derived2).Derived2AccessSomeVal()

		self.assertChanged(
			derived2AccessSomeValResult=54321,
			derived2AccessTestResult=2,
		)

	def testFunctionsImplementedOnlyInOneClass(self):
		"""Test that functions work correctly even if not all tools support it"""
		# Call a function defined only in Derived1 and not in the base class
		self.mixin.Tool(self._derived1).DoDerived1Thing()

		self.assertChanged(
			doDerived1ThingCalled=1,
		)

		# Call a function defined only in Derived2 and not in the base class
		self.mixin.Tool(self._derived2).DoDerived2Thing()

		self.assertChanged(
			doDerived2ThingCalled=1,
		)

	def testLimitByTool(self):
		"""Test that the Tool() function correctly limits a function call to only the specified tools"""
		# Call a function defined in both Derived1 and Derived2, but only call the Derived2 version
		self.mixin.Tool(self._derived2).DoMultiThing()

		self.assertChanged(
			doMultiThingCalledInDerived2=1,
		)

		# Call a function defined in both Derived1 and Derived2, but only call the Derived1 version
		self.mixin.Tool(self._derived1).DoMultiThing()

		self.assertChanged(
			doMultiThingCalledInDerived1=1,
		)

		# Call a function defined in both Derived1 and Derived2, and this time call both versions to verify
		# that multiple arguments to Tool works as expected
		self.mixin.Tool(self._derived1, self._derived2).DoMultiThing()

		self.assertChanged(
			doMultiThingCalledInDerived1=2,
			doMultiThingCalledInDerived2=2,
		)

		# Call a function defined in both Derived1 and Derived2, and this time call them both without going through Tool()
		self.mixin.DoMultiThing()

		self.assertChanged(
			doMultiThingCalledInDerived1=3,
			doMultiThingCalledInDerived2=3,
		)
