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
.. module:: setup
	:synopsis: Setup script for csbuild.

.. moduleauthor:: Zoe Bare
"""

from __future__ import unicode_literals, division, print_function

from setuptools import setup

with open("csbuild/version", "r") as f:
	csbuildVersion = f.read().strip()

setup(
	name = "csbuild",
	version = csbuildVersion,
	packages = ["csbuild"],
	include_package_data = True,
	author = "Sleeping Cat, LLC",
	author_email = "jaedyn.pypi@jaedyn.co",
	url = "https://github.com/SleepingCatGames/csbuild2",
	description = "Programming language-agnostic build system",
	long_description = """CSBuild is a language-agnostic build system focused on maximizing developer iteration time and providing tools for enabling developers to improve their build workflow. """,
	classifiers = [
		"Development Status :: 2 - Pre-Alpha",
		"Environment :: Console",
		"Intended Audience :: Developers",
		"License :: OSI Approved :: MIT License",
		"Natural Language :: English",
		"Operating System :: Microsoft :: Windows",
		"Operating System :: MacOS :: MacOS X",
		"Operating System :: POSIX :: Linux",
		"Programming Language :: Assembly",
		"Programming Language :: C",
		"Programming Language :: C++",
		"Programming Language :: Java",
		"Programming Language :: Objective C",
		"Programming Language :: Python :: 2.7",
		"Programming Language :: Python :: 3.4",
		"Programming Language :: Python :: 3.5",
		"Programming Language :: Python :: 3.6",
		"Programming Language :: Python :: 3.7",
		"Programming Language :: Python :: 3.8",
		"Programming Language :: Python :: 3.9",
		"Topic :: Software Development :: Build Tools",
	],
	install_requires = [
		"graphviz",
	],
)
