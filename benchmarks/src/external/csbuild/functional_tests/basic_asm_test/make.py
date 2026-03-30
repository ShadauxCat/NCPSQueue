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

.. moduleauthor:: Zoe Bare
"""

from __future__ import unicode_literals, division, print_function

import csbuild

csbuild.SetOutputDirectory("out")

with csbuild.Project("hello_world", "hello_world", autoDiscoverSourceFiles=False):
	csbuild.SetOutput("hello_world", csbuild.ProjectType.Application)

	csbuild.AddSourceFiles("hello_world/main.cpp")
	csbuild.Toolchain("gcc", "clang").AddSourceFiles("hello_world/getnum.gcc.S")

	with csbuild.Platform("Darwin"):
		csbuild.AddDefines("IS_PLATFORM_MACOS")

	with csbuild.Architecture("x86"):
		csbuild.AddDefines("IS_ARCH_X86")
		csbuild.Toolchain("msvc").AddSourceFiles("hello_world/getnum.msvc-x86.asm")

	with csbuild.Architecture("x64"):
		csbuild.AddDefines("IS_ARCH_X64")
		csbuild.Toolchain("msvc").AddSourceFiles("hello_world/getnum.msvc-x64.asm")

	with csbuild.Architecture("arm"):
		csbuild.AddDefines("IS_ARCH_ARM_32")

	with csbuild.Architecture("arm64"):
		csbuild.AddDefines("IS_ARCH_ARM_64")
