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
import glob

csbuild.SetIntermediateDirectory("intermediate")
csbuild.SetOutputDirectory("out")

class NullInput(Tool):
	"""
	Simple base class
	"""
	supportedArchitectures=None

class Doubler(NullInput):
	"""
	Simple tool that opens a file, doubles its contents numerically, and writes a new file.
	"""
	inputFiles = {".first"}

	outputFiles = {".second"}

	def Run(self, inputProject, inputFile):
		with open(inputFile.filename, "r") as f:
			value = int(f.read())
		value *= 2
		outFile = os.path.join(inputProject.intermediateDir, os.path.splitext(os.path.basename(inputFile.filename))[0] + ".second")
		with open(outFile, "w") as f:
			f.write(str(value))
			f.flush()
			os.fsync(f.fileno())
		return outFile

class Adder(NullInput):
	"""
	Simple tool that opens multiple doubled files and adds their contents together numerically, outputting a final file.
	"""
	inputGroups = {".second"}
	outputFiles = {".third"}

	def RunGroup(self, inputProject, inputFiles):
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

class NullInputMakes20(NullInput):
	"""
	This tool replaces the input processing of 10.first from basic_tool_test by directly creating 10.second
	"""
	inputFiles = None
	outputFiles = {".second"}

	def Run(self, inputProject, _):
		outFile = os.path.join(inputProject.intermediateDir, "10.second")
		with open(outFile, "w") as f:
			f.write("20")
			f.flush()
			os.fsync(f.fileno())
		return outFile

class NullInputAdds(NullInput):
	"""
	This tool replaces Adder and manually iterates the .second files to add them together.
	If the 'dependencies' parameter is broken, this will fail!
	"""
	inputFiles = None
	dependencies = {".second"}
	outputFiles = {".third"}

	def Run(self, inputProject, _):
		value = 0
		for inputFile in glob.glob(os.path.join(inputProject.intermediateDir, "*.second")):
			with open(inputFile, "r") as f:
				value += int(f.read())
		outFile = os.path.join(inputProject.outputDir, inputProject.outputName + ".third")
		with open(outFile, "w") as f:
			f.write(str(value))
			f.flush()
			os.fsync(f.fileno())
		return outFile

csbuild.RegisterToolchain("NullInput", "", NullInputMakes20, Doubler, Adder)
csbuild.RegisterToolchain("NullInputWithDepends", "", NullInputAdds, Doubler)
csbuild.SetDefaultToolchain("NullInput")

with csbuild.Project("TestProject", "."):
	csbuild.SetOutput("Foo", csbuild.ProjectType.Application)
