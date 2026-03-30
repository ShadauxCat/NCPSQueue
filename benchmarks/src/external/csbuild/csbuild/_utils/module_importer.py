# Copyright (C) 2024 Jaedyn K. Draper
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
.. module:: module_importer
	:synopsis: Helper class to satisfy the module import functionality we require.
		The `imp` module was deprecated in Python 3.4 and removed in 3.12,
		so we recreate the functions we need here.
"""

import sys

if sys.version_info[0] > 3 or (sys.version_info[0] == 3 and sys.version_info[1] >= 12):
	from . import _imp_replacement

	load_source = _imp_replacement.load_source
	load_module = _imp_replacement.load_module
	find_module = _imp_replacement.find_module
	lock_held = _imp_replacement.lock_held
	acquire_lock = _imp_replacement.acquire_lock
	release_lock = _imp_replacement.release_lock

else:
	import imp # pylint: disable=deprecated-module,import-error

	load_source = imp.load_source
	load_module = imp.load_module
	find_module = imp.find_module
	lock_held = imp.lock_held
	acquire_lock = imp.acquire_lock
	release_lock = imp.release_lock
