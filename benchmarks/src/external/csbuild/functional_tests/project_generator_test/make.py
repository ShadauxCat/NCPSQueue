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
from csbuild.toolchain import Tool, SolutionGenerator
import os

fooSet = False
barSet = False
quxSet = False
quuxset = False

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
		csbuild.currentPlan.SetValue("foo", True)

	@staticmethod
	def SetBar():
		"""
		Set bar to true, yay testing.
		"""
		global barSet
		assert barSet is False
		barSet = True
		csbuild.currentPlan.SetValue("bar", True)

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
		csbuild.currentPlan.SetValue("qux", True)

	@staticmethod
	def SetQuux():
		"""
		Does nothing.
		"""
		pass

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

class DummyProjectGenerator(Tool):
	"""Dummy project generator"""
	inputGroups = {".first"}
	outputFiles = {".proj"}

	def __init__(self, projectSettings):
		self._projectSettings = projectSettings

		self._foo = projectSettings.get("foo", False)
		self._bar = projectSettings.get("bar", False)
		self._qux = projectSettings.get("qux", False)
		self._quux = projectSettings.get("quux", False)

		Tool.__init__(self, projectSettings)


	def SetupForProject(self, project):
		projectSettings = self._projectSettings

		# These checks done here because information is needed from the project to know what the values should be
		# Project settings should NEVER be read outside of __init__ in production code. It will not work as expected.
		assert "foo" not in projectSettings._settingsDict #pylint: disable=protected-access
		assert "{}!foo".format(id(DummyProjectGenerator)) in projectSettings._settingsDict #pylint: disable=protected-access

		if project.name == "TestProject":
			if project.toolchainName == "AddDoubles":
				if project.targetName == "release":
					assert "bar" not in projectSettings._settingsDict #pylint: disable=protected-access
					assert "{}!bar".format(id(DummyProjectGenerator)) in projectSettings._settingsDict #pylint: disable=protected-access
				assert "qux" not in projectSettings._settingsDict #pylint: disable=protected-access
				assert "{}!qux".format(id(DummyProjectGenerator)) in projectSettings._settingsDict #pylint: disable=protected-access
				assert "quux" not in projectSettings._settingsDict #pylint: disable=protected-access
				assert "{}!quux".format(id(DummyProjectGenerator)) in projectSettings._settingsDict #pylint: disable=protected-access

	@staticmethod
	def SetQuux():
		"""
		Set quux to true, yay testing.
		"""
		csbuild.currentPlan.SetValue("quux", True)

	@staticmethod
	def SetFoo():
		"""
		Set foo to true, yay testing.
		"""
		csbuild.currentPlan.SetValue("foo", True)

	@staticmethod
	def SetQux():
		"""
		Set qux to true, yay testing.
		"""
		csbuild.currentPlan.SetValue("qux", True)

	@staticmethod
	def SetBar():
		"""
		Set bar to true, yay testing.
		"""
		csbuild.currentPlan.SetValue("bar", True)

	@property
	def foo(self):  # pylint: disable=blacklisted-name
		"""Get foo"""
		return self._foo

	@property
	def bar(self):  # pylint: disable=blacklisted-name
		"""Get bar"""
		return self._bar

	@property
	def qux(self):
		"""Get qux"""
		return self._qux

	@property
	def quux(self):
		"""Get quux"""
		return self._quux

	def RunGroup(self, inputProject, inputFiles):
		assert self._foo is True
		assert self._bar is (inputProject.targetName == "release")
		assert self._qux is True
		assert self._quux is True
		outStr = "\n".join([inputFile.filename for inputFile in inputFiles])
		outFile = os.path.join(csbuild.GetSolutionPath(), inputProject.outputName + "_" + inputProject.targetName + ".proj")
		with open(outFile, "w") as f:
			f.write(outStr)
			f.flush()
			os.fsync(f.fileno())
		return outFile

class DummySolutionGenerator(SolutionGenerator):
	"""Dummy solution generator"""

	@staticmethod
	def GenerateSolution(outputDir, solutionName, projects):
		"""
		Generates the actual solution file from the projects generated by each tool.
		The actual project objects are passed to the solution generator, allowing the generator to gather information
		about the projects themselves, as well as outputs returned from the project generator tools
		(via project.inputFiles[".ext"], which is a list of csbuild._build.input_file.InputFile objects) and
		data on the tools (via calling methods and properties on the tool through project.toolchain.Tool(ToolType).Method()
		or project.toolchain.Tool(ToolType).property)

		:param outputDir: Top-level directory all solution files should be placed into
		:type outputDir: str
		:param solutionName: Desired base name of the solution
		:type solutionName: str
		:param projects: Set of all built projects
		:type projects: list[csbuild._build.project.Project]
		"""
		outStr = ""
		for proj in projects:
			# I do not know why pylint thinks inputFile is a str.
			outStr += "\n".join(sorted([inputFile.filename for inputFile in proj.inputFiles[".proj"]]))  # pylint: disable=no-member
			print(proj.toolchain.Tool(DummyProjectGenerator))
			print(proj.toolchain.Tool(DummyProjectGenerator).foo)
			assert proj.toolchain.Tool(DummyProjectGenerator).foo is True
			assert proj.toolchain.Tool(DummyProjectGenerator).bar is (proj.targetName == "release")
			assert proj.toolchain.Tool(DummyProjectGenerator).qux is True
			assert proj.toolchain.Tool(DummyProjectGenerator).quux is True

		outFile = os.path.join(outputDir, solutionName + ".sln")
		with open(outFile, "w") as f:
			f.write(outStr)
			f.flush()
			os.fsync(f.fileno())

csbuild.RegisterToolchain("AddDoubles", "", Doubler)
csbuild.RegisterProjectGenerator("DummyGenerator", [DummyProjectGenerator], DummySolutionGenerator)
csbuild.SetDefaultToolchain("AddDoubles")

csbuild.SetFoo()

with csbuild.Project("TestProject", "."):
	with csbuild.Toolchain("AddDoubles"):
		csbuild.AddTool(Adder)
		csbuild.SetQux()
		with csbuild.Target("release"):
			csbuild.SetBar()
		csbuild.Tool(Adder).SetQuux()
	csbuild.SetOutput("Foo", csbuild.ProjectType.Application)
