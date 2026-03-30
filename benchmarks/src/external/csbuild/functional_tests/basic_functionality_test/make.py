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

class NullClass(Tool):
	"""Empty tool just to make things work."""
	inputFiles = {".foo"}
	outputFiles = {".bar"}
	supportedArchitectures=None
	inputFiles=None
	outputFiles={""}

	def Run(self, inputProject, inputFile):
		return "(no output)"

csbuild.RegisterToolchain("msvc", "dummy", NullClass)
csbuild.RegisterToolchain("gcc", "dummy", NullClass)

with csbuild.Project("hello_world_2", "./", ["hello_world"]):
	with csbuild.Target("debug"):
		csbuild.SetOutput("hello_world_2_debug")

	with csbuild.Target("release"):
		csbuild.SetOutput("hello_world_2")

with csbuild.Project("hello_world_3", "./", ["hello_world"]):
	with csbuild.Target("debug"):
		csbuild.SetOutput("hello_world_3_debug")

	with csbuild.Target("release"):
		csbuild.SetOutput("hello_world_3")

with csbuild.Project("hello_world", "./"):
	with csbuild.Target("release"):
		csbuild.SetOutput("hello_world_release")

	csbuild.SetOutput("hello_world")
