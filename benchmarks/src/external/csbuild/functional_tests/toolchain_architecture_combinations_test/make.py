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

csbuild.SetOutputDirectory("out")

class WriteOutput(Tool):
	"""Dummy class"""
	inputFiles = None

	def __init__(self, projectSettings, ext):
		self._ext = ext
		Tool.__init__(self, projectSettings)

	def Run(self, inputProject, inputFile):
		outFile = os.path.join(inputProject.outputDir, ".".join([inputProject.outputName, inputProject.architectureName, inputProject.targetName, self._ext]))
		csbuild.log.Build("Writing {}", outFile)
		with open(outFile, "w") as f:
			f.write("foo")
			f.flush()
			os.fsync(f.fileno())
		return outFile

class WriteA(WriteOutput):
	"""Dummy class"""
	supportedArchitectures = {"A", "B", "C", "D"}
	outputFiles = {".A"}
	def __init__(self, projectSettings):
		WriteOutput.__init__(self, projectSettings, "A")

class WriteB(WriteOutput):
	"""Dummy class"""
	supportedArchitectures = {"A", "B", "C", "D"}
	outputFiles = {".B"}
	def __init__(self, projectSettings):
		WriteOutput.__init__(self, projectSettings, "B")

class WriteC(WriteOutput):
	"""Dummy class"""
	supportedArchitectures = {"A", "B", "C", "D"}
	outputFiles = {".C"}
	def __init__(self, projectSettings):
		WriteOutput.__init__(self, projectSettings, "C")

class WriteD(WriteOutput):
	"""Dummy class"""
	supportedArchitectures = {"A", "B", "C", "D", "E"}
	outputFiles = {".D"}
	def __init__(self, projectSettings):
		WriteOutput.__init__(self, projectSettings, "D")

class WriteWindows(WriteOutput):
	"""Dummy class"""
	supportedArchitectures = {"A", "B", "C", "D"}
	supportedPlatforms = {"Windows"}
	outputFiles = {".Windows"}
	def __init__(self, projectSettings):
		WriteOutput.__init__(self, projectSettings, "Windows")

class WriteLinux(WriteOutput):
	"""Dummy class"""
	supportedArchitectures = {"A", "B", "C", "D"}
	supportedPlatforms = {"Linux"}
	outputFiles = {".Linux"}
	def __init__(self, projectSettings):
		WriteOutput.__init__(self, projectSettings, "Linux")

class WriteMacOs(WriteOutput):
	"""Dummy class"""
	supportedArchitectures = {"A", "B", "C", "D"}
	supportedPlatforms = {"Darwin"}
	outputFiles = {".Darwin"}
	def __init__(self, projectSettings):
		WriteOutput.__init__(self, projectSettings, "Darwin")

csbuild.RegisterToolchain("A", "A", WriteA)
csbuild.RegisterToolchain("B", "B", WriteB)
csbuild.RegisterToolchain("C", "C", WriteC)
csbuild.RegisterToolchain("D", "D", WriteD)
csbuild.RegisterToolchain("Windows", "A", WriteWindows)
csbuild.RegisterToolchain("Linux", "A", WriteLinux)
csbuild.RegisterToolchain("Darwin", "A", WriteMacOs)

csbuild.SetDefaultToolchain("A")
csbuild.SetDefaultTarget("A")

with csbuild.Target("A"):
	pass

with csbuild.Target("B"):
	pass

with csbuild.Project("AlwaysWorks", ".", autoDiscoverSourceFiles=False):
	csbuild.SetOutput("foo", csbuild.ProjectType.Application)

with csbuild.Project("ProjectWithLimitedArchitectures", ".", autoDiscoverSourceFiles=False):
	csbuild.SetSupportedArchitectures("A", "B", "C")
	csbuild.SetOutput("arch", csbuild.ProjectType.Application)

with csbuild.Architecture("A", "B", "C"):
	with csbuild.Project("ProjectWithLimitedArchitectures2", ".", autoDiscoverSourceFiles=False):
		csbuild.SetOutput("arch2", csbuild.ProjectType.Application)

with csbuild.Project("ProjectWithExcludedTarget", ".", autoDiscoverSourceFiles=False):
	csbuild.SetSupportedTargets("A")
	csbuild.SetOutput("target", csbuild.ProjectType.Application)

with csbuild.Target("A"):
	with csbuild.Project("ProjectWithExcludedTarget2", ".", autoDiscoverSourceFiles=False):
		csbuild.SetOutput("target2", csbuild.ProjectType.Application)

with csbuild.Project("ProjectWithSpecialTarget", ".", autoDiscoverSourceFiles=False):
	with csbuild.Target("special"):
		csbuild.SetOutput("special", csbuild.ProjectType.Application)
	csbuild.SetOutput("unspecial", csbuild.ProjectType.Application)

with csbuild.Target("special", addToCurrentScope=False):
	with csbuild.Project("ProjectWithSpecialTarget2", ".", autoDiscoverSourceFiles=False):
		csbuild.SetOutput("special2", csbuild.ProjectType.Application)

with csbuild.Project("LimitedToolchains", ".", autoDiscoverSourceFiles=False):
	csbuild.SetSupportedToolchains("B", "C", "D")
	csbuild.SetOutput("toolchain", csbuild.ProjectType.Application)

with csbuild.Toolchain("B", "C", "D"):
	with csbuild.Project("LimitedToolchains2", ".", autoDiscoverSourceFiles=False):
		csbuild.SetOutput("toolchain2", csbuild.ProjectType.Application)

with csbuild.Project("WindowsProject", ".", autoDiscoverSourceFiles=False):
	csbuild.SetSupportedPlatforms("Windows")
	csbuild.SetOutput("Windows", csbuild.ProjectType.Application)

with csbuild.Project("LinuxProject", ".", autoDiscoverSourceFiles=False):
	csbuild.SetSupportedPlatforms("Linux")
	csbuild.SetOutput("Linux", csbuild.ProjectType.Application)

with csbuild.Project("MacProject", ".", autoDiscoverSourceFiles=False):
	csbuild.SetSupportedPlatforms("Darwin")
	csbuild.SetOutput("Darwin", csbuild.ProjectType.Application)

with csbuild.Platform("Windows"):
	with csbuild.Project("WindowsProject2", ".", autoDiscoverSourceFiles=False):
		csbuild.SetOutput("Windows2", csbuild.ProjectType.Application)

with csbuild.Platform("Linux"):
	with csbuild.Project("LinuxProject2", ".", autoDiscoverSourceFiles=False):
		csbuild.SetOutput("Linux2", csbuild.ProjectType.Application)

with csbuild.Platform("Darwin"):
	with csbuild.Project("DarwinProject2", ".", autoDiscoverSourceFiles=False):
		csbuild.SetOutput("Darwin2", csbuild.ProjectType.Application)
