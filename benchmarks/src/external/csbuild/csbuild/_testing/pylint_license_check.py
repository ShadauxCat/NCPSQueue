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
.. module:: pylint_license_check
	:synopsis: Pylint custom checker to check for licensing issues and general always-required stuff

.. moduleauthor:: Jaedyn K. Draper
"""

from __future__ import unicode_literals, division, print_function

import os
import re
import sys

if sys.version_info.major >= 3:
	from pylint.checkers import BaseChecker, BaseRawFileChecker

else:
	class BaseRawFileChecker(object):
		# pylint: disable=missing-class-docstring
		pass

	class BaseChecker(object):
		# pylint: disable=missing-class-docstring
		pass

MANDATORY_COPYRIGHT_HEADER = R"""^(# -\*- coding: utf-8 -\*-

)?# Copyright \(C\) 201\d [^\n]+
#
# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files \(the "Software"\),
# to deal in the Software without restriction, including without limitation
# the rights to use, copy, modify, merge, publish, distribute, sublicense,
# and/or sell copies of the Software, and to permit persons to whom the
# Software is furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software\.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT\. IN NO EVENT SHALL
# THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE\.""".replace("\r", "")

FUTURE_IMPORT_REQ = "from __future__ import unicode_literals, division, print_function"

class HeaderCheck(BaseChecker):
	"""check for line continuations with '\' instead of using triple
	quoted string or parenthesis
	"""

	# pylint: disable=invalid-name

	__implements__ = BaseRawFileChecker

	name = 'csbuild_license_check'
	msgs = {
		'E9901': (
			'Missing license header',
			'missing-license-header',
			'missing-license-header'
		),
		'E9902': (
			'All files must import unicode_literals, division, and print_function from __future__',
			'missing-future-imports',
			'missing-future-imports'
		),
		'E9903': (
			'All modules must include a docstring containing .. module:: <module_name>',
			'module-name-missing-in-docstring',
			'module-name-missing-in-docstring'
		),
		'E9904': (
			'__init__.py in a package must include a docstring containing .. package:: <package_name>',
			'package-name-missing-in-docstring',
			'package-name-missing-in-docstring'
		)
	}
	options = ()

	def process_module(self, module):
		"""
		Process a module the module's content is accessible via node.stream() function.

		:param module: Module being processed.
		:type module: :class:`astroid.scoped_nodes.Module`
		"""
		with module.stream() as stream:
			txt = b"".join(stream).decode("UTF-8")

			txt = txt.replace("\r", "")

			if not re.match(MANDATORY_COPYRIGHT_HEADER, txt):
				self.add_message('missing-license-header', line=0)
			if FUTURE_IMPORT_REQ not in txt:
				self.add_message('missing-future-imports', line=0)

			package = os.path.basename(os.path.dirname(module.file))
			moduleName = os.path.basename(module.file)
			moduleName = os.path.splitext(moduleName)[0]
			if moduleName == "__init__":
				if ".. package:: {}".format(package) not in txt:
					self.add_message('package-name-missing-in-docstring', line=0)
			elif ".. module:: {}".format(moduleName) not in txt:
				self.add_message('module-name-missing-in-docstring', line=0)



def register(linter):  # pylint: disable=invalid-name
	"""required method to auto register this checker"""
	linter.register_checker(HeaderCheck(linter))
