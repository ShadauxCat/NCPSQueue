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
.. module:: make
	:synopsis: Makefile for this test

.. moduleauthor:: Jaedyn K. Draper
"""

from __future__ import unicode_literals, division, print_function

import csbuild
from csbuild.toolchain import Tool
import os

fooSet = False
barSet = False
quxSet = False

csbuild.SetIntermediateDirectory("intermediate")
csbuild.SetOutputDirectory("out")

class AddDoubles(Tool):
	"""
	Simple base class to test global toolchain contexts
	"""
	supportedArchitectures=None
	def __init__(self, projectSettings):
		assert "foo" not in projectSettings._settingsDict #pylint: disable=protected-access
		assert "{}!foo".format(id(AddDoubles)) in projectSettings._settingsDict #pylint: disable=protected-access
		self._foo = projectSettings.get("foo", False)

		assert "bar" not in projectSettings._settingsDict #pylint: disable=protected-access
		assert "{}!bar".format(id(AddDoubles)) in projectSettings._settingsDict #pylint: disable=protected-access
		self._bar = projectSettings.get("bar", False)

		Tool.__init__(self, projectSettings)

	@staticmethod
	def SetFoo():
		"""
		Set foo to true, yay testing.
		"""
		global fooSet
		assert fooSet is False
		fooSet = True
		csbuild.currentPlan.SetValue("foo", True) #pylint: disable=protected-access

	@staticmethod
	def SetBar():
		"""
		Set bar to true, yay testing.
		"""
		global barSet
		assert barSet is False
		barSet = True
		csbuild.currentPlan.SetValue("bar", True) #pylint: disable=protected-access

class Doubler(AddDoubles):
	"""
	Simple tool that opens a file, doubles its contents numerically, and writes a new file.
	"""
	inputFiles = {".first"}

	outputFiles = {".second"}

	def Run(self, inputProject, inputFile):
		assert self._foo is True
		assert self._bar is True
		with open(inputFile.filename, "r") as f:
			value = int(f.read())
		value *= 2
		outFile = os.path.join(inputProject.intermediateDir, os.path.splitext(os.path.basename(inputFile.filename))[0] + ".second")
		with open(outFile, "w") as f:
			f.write(str(value))
			f.flush()
			os.fsync(f.fileno())
		return outFile

class Adder(AddDoubles):
	"""
	Simple tool that opens multiple doubled files and adds their contents together numerically, outputting a final file.
	"""
	inputGroups = {".second"}
	outputFiles = {".third"}

	def __init__(self, projectSettings):
		assert "qux" not in projectSettings._settingsDict #pylint: disable=protected-access
		assert "{}!qux".format(id(Adder)) in projectSettings._settingsDict #pylint: disable=protected-access
		self._qux = projectSettings.get("qux", False)

		AddDoubles.__init__(self, projectSettings)

	@staticmethod
	def SetQux():
		"""
		Set qux to true, yay testing.
		"""
		global quxSet
		assert quxSet is False
		quxSet = True
		csbuild.currentPlan.SetValue("qux", True) #pylint: disable=protected-access

	def RunGroup(self, inputProject, inputFiles):
		assert self._foo is True
		assert self._bar is True
		assert self._qux is True
		value = 0
		for inputFile in inputFiles:
			with open(inputFile.filename, "r") as f:
				value += int(f.read())
		outFile = os.path.join(inputProject.outputDir, inputProject.outputName + ".third")
		with open(outFile, "w") as f:
			f.write(str(value))
			f.flush()
			os.fsync(f.fileno())
		return outFile

csbuild.RegisterToolchain("AddDoubles", "", Doubler)
csbuild.SetDefaultToolchain("AddDoubles")

csbuild.SetFoo()

with csbuild.Project("TestProject", "."):
	with csbuild.Toolchain("AddDoubles"):
		csbuild.AddTool(Adder)
		csbuild.SetQux()
		with csbuild.Target("release"):
			csbuild.SetBar()
	csbuild.SetOutput("Foo", csbuild.ProjectType.Application)
