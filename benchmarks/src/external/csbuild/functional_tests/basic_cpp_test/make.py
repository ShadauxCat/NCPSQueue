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

csbuild.SetOutputDirectory("out")
csbuild.SetDefaultTarget("static")

with csbuild.Target("static"):
	csbuild.SetOutputDirectory("static")

with csbuild.Target("shared"):
	csbuild.SetOutputDirectory("shared")

with csbuild.Project("libhello", "libhello"):
	with csbuild.Target("shared"):
		csbuild.SetOutput("libhello", csbuild.ProjectType.SharedLibrary)

	with csbuild.Target("static"):
		csbuild.SetOutput("libhello", csbuild.ProjectType.StaticLibrary)

with csbuild.Project("hello_world", "hello_world", ["libhello"]):
	csbuild.Platform("Darwin").AddLibraries("libgmalloc.dylib")
	csbuild.Platform("Linux").AddLibraries("pthread", "libm.so", "libc.so.6")
	csbuild.Platform("Windows").AddLibraries("winmm", "DbgHelp.lib")
	csbuild.SetOutput("hello_world", csbuild.ProjectType.Application)

with csbuild.Project("fail_libraries", "hello_world"):
	csbuild.AddLibraries("nonexistent", "nothere")
	csbuild.SetOutput("hello_world", csbuild.ProjectType.Application)

with csbuild.Project("fail_compile", "fail_compile"):
	csbuild.SetOutput("fail_compile", csbuild.ProjectType.Application)

with csbuild.Project("fail_link", "fail_link"):
	csbuild.SetOutput("fail_link", csbuild.ProjectType.Application)
