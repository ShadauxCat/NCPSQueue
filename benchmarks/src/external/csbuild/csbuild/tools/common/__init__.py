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
.. package:: common
	:synopsis: Abstract tools and functions that can be shared between other tools.

.. moduleauthor:: Zoe Bare
"""

# Required to keep lint happy.
from __future__ import unicode_literals, division, print_function

import os

from csbuild import log

def FindLibraries(libNames, libDirs, libExts):
	"""
	Helper function to explicitly search for libraries.  This is needed by linker tools that cannot run a
	specific executable for this.

	:param libNames: Library names to search for.
	:type libNames: list[str]

	:param libDirs: Library directories to search in.
	:type libDirs: list[str]

	:param libExts: File extensions (in priority order) to use in combination with library names.
	:type libExts: list[str]

	:return: Dictionary of library names to their full paths.
	:rtype: dict[str, str] or None
	"""
	notFound = set()
	found = {}

	def _searchForLib(libraryName, libraryDir, libExt):
		# Add the extension if it's not already there.
		filename = "{}{}".format(libraryName, libExt) if not libraryName.endswith(libExt) else libraryName

		# Try searching for the library name as it is.
		log.Info("Looking for library {} in directory {}...".format(filename, libraryDir))
		fullPath = os.path.join(libraryDir, filename)

		# Check if the file exists at the current path.
		if os.access(fullPath, os.F_OK):
			return fullPath

		# If the library couldn't be found, simulate posix by adding the "lib" prefix.
		filename = "lib{}".format(filename)

		log.Info("Looking for library {} in directory {}...".format(filename, libraryDir))
		fullLibraryPath = os.path.join(libraryDir, filename)

		# Check if the modified filename exists at the current path.
		if os.access(fullLibraryPath, os.F_OK):
			return fullLibraryPath

		return None

	for libraryName in libNames:
		if os.access(libraryName, os.F_OK):
			abspath = os.path.abspath(libraryName)
			log.Info("... found {}".format(abspath))
			found[libraryName] = abspath
		else:
			for libraryExt in libExts:
				for libraryDir in libDirs:
					# Search for the library with the current extension.
					fullPath = _searchForLib(libraryName, libraryDir, libraryExt)
					if fullPath:
						log.Info("... found {}".format(fullPath))
						found[libraryName] = fullPath
						break

			if libraryName not in found:
				# Failed to find the library in any of the provided directories.
				log.Error("Failed to find library \"{}\".".format(libraryName))
				notFound.add(libraryName)

	return None if notFound else found
