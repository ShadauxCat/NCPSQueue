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

csbuild.SetIntermediateDirectory("intermediate")
csbuild.SetOutputDirectory("out")

class AddDoubles(Tool):
	"""
	Simple base class to test global toolchain contexts
	"""
	supportedArchitectures=None

class Doubler(AddDoubles):
	"""
	Simple tool that opens a file, doubles its contents numerically, and writes a new file.
	"""
	inputFiles = {".first"}
	outputFiles = {".first"}
	exclusive = True

	def Run(self, inputProject, inputFile):
		with open(inputFile.filename, "r") as f:
			value = int(f.read())
		value *= 2
		outFile = os.path.join(inputProject.intermediateDir, os.path.splitext(os.path.basename(inputFile.filename))[0] + ".double.first")
		with open(outFile, "w") as f:
			f.write(str(value))
			f.flush()
			os.fsync(f.fileno())
		return outFile

class Tripler(AddDoubles):
	"""
	Simple tool that opens a file, doubles its contents numerically, and writes a new file.
	"""
	inputFiles = {".first"}
	outputFiles = {".first"}
	exclusive = True

	def Run(self, inputProject, inputFile):
		with open(inputFile.filename, "r") as f:
			value = int(f.read())
		value *= 3
		outFile = os.path.join(inputProject.intermediateDir, os.path.splitext(os.path.basename(inputFile.filename))[0] + ".triple.first")
		with open(outFile, "w") as f:
			f.write(str(value))
			f.flush()
			os.fsync(f.fileno())
		return outFile

class Quadrupler(AddDoubles):
	"""
	Simple tool that opens a file, doubles its contents numerically, and writes a new file.
	"""
	inputFiles = {".first"}
	outputFiles = {".first"}
	exclusive = True

	def Run(self, inputProject, inputFile):
		with open(inputFile.filename, "r") as f:
			value = int(f.read())
		value *= 4
		outFile = os.path.join(inputProject.intermediateDir, os.path.splitext(os.path.basename(inputFile.filename))[0] + ".quadruple.first")
		with open(outFile, "w") as f:
			f.write(str(value))
			f.flush()
			os.fsync(f.fileno())
		return outFile

class Adder(AddDoubles):
	"""
	Simple tool that opens multiple doubled files and adds their contents together numerically, outputting a final file.
	"""
	inputGroups = {".first"}
	outputFiles = {".second"}

	def RunGroup(self, inputProject, inputFiles):
		value = 0
		for inputFile in inputFiles:
			with open(inputFile.filename, "r") as f:
				value += int(f.read())
		outFile = os.path.join(inputProject.outputDir, inputProject.outputName + ".second")
		with open(outFile, "w") as f:
			f.write(str(value))
			f.flush()
			os.fsync(f.fileno())
		return outFile

csbuild.RegisterToolchain("AddDoubles", "", Doubler, Tripler, Quadrupler, Adder)
csbuild.SetDefaultToolchain("AddDoubles")

with csbuild.Project("TestProject", "."):
	csbuild.SetOutput("Foo", csbuild.ProjectType.Application)
