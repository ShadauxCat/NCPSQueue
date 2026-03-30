# Copyright (C) 2018 Jaedyn K. Draper
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
.. package:: visual_studio
	:synopsis: Visual Studio project generators

.. moduleauthor:: Zoe Bare
"""

from __future__ import unicode_literals, division, print_function

from . import internal

from .platform_handlers import VsBasePlatformHandler

from csbuild._utils.decorators import TypeChecked

from csbuild.toolchain import SolutionGenerator

from csbuild.tools.common.msvc_tool_base import MsvcToolBase
from csbuild.tools.common.tool_traits import HasDefines, HasIncludeDirectories, HasCcLanguageStandard, HasCxxLanguageStandard


def _writeProjectFiles(outputDir, solutionName, projects, version):
	generators = [x.toolchain.Tool(VsProjectGenerator) for x in projects]

	# Remove all generators that have no project data.
	generators = [gen for gen in generators if gen.projectData]

	internal.WriteProjectFiles(outputDir, solutionName, generators, version)


@TypeChecked(handlers=dict)
def UpdatePlatformHandlers(handlers):
	"""
	Added custom platform handlers to the Visual Studio generator.

	:param handlers: Dictionary of platform handlers mappings to their build targets.
	:type handlers: dict[ tuple[ str, str, str or None or tuple[str] ], class ]
	"""
	internal.UpdatePlatformHandlers(handlers)


@TypeChecked(enable=bool)
def SetEnableFileTypeFolders(enable):
	"""
	Helper function to toggle the "file type folder" feature in the project generator.

	:param enable: Enable file type folders in the generated projects.
	:type enable: bool
	"""
	if isinstance(enable, bool):
		internal.ENABLE_FILE_TYPE_FOLDERS = enable


class VsProjectGenerator(MsvcToolBase, HasDefines, HasIncludeDirectories, HasCcLanguageStandard, HasCxxLanguageStandard):
	"""
	Visual Studio project generator

	:param projectSettings: A read-only scoped view into the project settings dictionary
	:type projectSettings: toolchain.ReadOnlySettingsView
	"""
	inputGroups = internal.ALL_FILE_EXTENSIONS
	outputFiles = { ".proj" }

	def __init__(self, projectSettings):
		MsvcToolBase.__init__(self, projectSettings)
		HasDefines.__init__(self, projectSettings)
		HasIncludeDirectories.__init__(self, projectSettings)
		HasCcLanguageStandard.__init__(self, projectSettings)
		HasCxxLanguageStandard.__init__(self, projectSettings)

		self._projectData = None
		self._sourceFiles = []
		self._groupSegments = []

	def SetupForProject(self, project):
		try:
			MsvcToolBase.SetupForProject(self, project)
		except:
			# Do nothing on failure. This likely means something went wrong with trying to find
			# an installation of Visual Studio. Nothing is completely dependent on this, so it's
			# ok if it fails.
			pass

		HasDefines.SetupForProject(self, project)
		HasIncludeDirectories.SetupForProject(self, project)
		HasCcLanguageStandard.SetupForProject(self, project)
		HasCxxLanguageStandard.SetupForProject(self, project)

	def RunGroup(self, inputProject, inputFiles):
		self._projectData = inputProject
		self._sourceFiles = [x.filename for x in inputFiles]
		# TODO: Once project groups are implemented, parse it for the current project and store the results in self._groupSegments.

		return "{}.proj".format(inputProject.outputName)

	@property
	def sourceFiles(self):
		"""Project source files"""
		return self._sourceFiles

	@property
	def groupSegments(self):
		"""Project group segments"""
		return self._groupSegments

	@property
	def includeDirectories(self):
		"""Project include directories"""
		return self._includeDirectories

	@property
	def defines(self):
		"""Project defines"""
		return self._defines

	@property
	def ccLanguageStandard(self):
		"""Project C language standard"""
		return self._ccStandard

	@property
	def cxxLanguageStandard(self):
		"""Project C++ language standard"""
		return self._cxxStandard

	@property
	def projectData(self):
		"""Project settings data"""
		return self._projectData

class VsSolutionGenerator2010(SolutionGenerator):
	"""Visual Studio 2010 solution generator"""

	@staticmethod
	def GenerateSolution(outputDir, solutionName, projects):
		"""
		Generates the actual solution file from the projects generated by each tool.
		The actual project objects are passed to the solution generator, allowing the generator to gather information
		about the projects themselves, as well as outputs returned from the project generator tools
		(via project.inputFiles[".ext"], which is a list of csbuild._build.input_file.InputFile objects) and
		data on the tools (via calling methods and properties on the tool through project.toolchain.Tool(ToolType).Method()
		or project.toolchain.Tool(ToolType).property)

		:param outputDir: Top-level directory all solution files should be placed into
		:type outputDir: str
		:param solutionName: Desired base name of the solution
		:type solutionName: str
		:param projects: Set of all built projects
		:type projects: list[csbuild._build.project.Project]
		"""
		_writeProjectFiles(outputDir, solutionName, projects, internal.Version.Vs2010)


class VsSolutionGenerator2012(SolutionGenerator):
	"""Visual Studio 2012 solution generator"""

	@staticmethod
	def GenerateSolution(outputDir, solutionName, projects):
		"""
		Generates the actual solution file from the projects generated by each tool.
		The actual project objects are passed to the solution generator, allowing the generator to gather information
		about the projects themselves, as well as outputs returned from the project generator tools
		(via project.inputFiles[".ext"], which is a list of csbuild._build.input_file.InputFile objects) and
		data on the tools (via calling methods and properties on the tool through project.toolchain.Tool(ToolType).Method()
		or project.toolchain.Tool(ToolType).property)

		:param outputDir: Top-level directory all solution files should be placed into
		:type outputDir: str
		:param solutionName: Desired base name of the solution
		:type solutionName: str
		:param projects: Set of all built projects
		:type projects: list[csbuild._build.project.Project]
		"""
		_writeProjectFiles(outputDir, solutionName, projects, internal.Version.Vs2012)


class VsSolutionGenerator2013(SolutionGenerator):
	"""Visual Studio 2013 solution generator"""

	@staticmethod
	def GenerateSolution(outputDir, solutionName, projects):
		"""
		Generates the actual solution file from the projects generated by each tool.
		The actual project objects are passed to the solution generator, allowing the generator to gather information
		about the projects themselves, as well as outputs returned from the project generator tools
		(via project.inputFiles[".ext"], which is a list of csbuild._build.input_file.InputFile objects) and
		data on the tools (via calling methods and properties on the tool through project.toolchain.Tool(ToolType).Method()
		or project.toolchain.Tool(ToolType).property)

		:param outputDir: Top-level directory all solution files should be placed into
		:type outputDir: str
		:param solutionName: Desired base name of the solution
		:type solutionName: str
		:param projects: Set of all built projects
		:type projects: list[csbuild._build.project.Project]
		"""
		_writeProjectFiles(outputDir, solutionName, projects, internal.Version.Vs2013)


class VsSolutionGenerator2015(SolutionGenerator):
	"""Visual Studio 2015 solution generator"""

	@staticmethod
	def GenerateSolution(outputDir, solutionName, projects):
		"""
		Generates the actual solution file from the projects generated by each tool.
		The actual project objects are passed to the solution generator, allowing the generator to gather information
		about the projects themselves, as well as outputs returned from the project generator tools
		(via project.inputFiles[".ext"], which is a list of csbuild._build.input_file.InputFile objects) and
		data on the tools (via calling methods and properties on the tool through project.toolchain.Tool(ToolType).Method()
		or project.toolchain.Tool(ToolType).property)

		:param outputDir: Top-level directory all solution files should be placed into
		:type outputDir: str
		:param solutionName: Desired base name of the solution
		:type solutionName: str
		:param projects: Set of all built projects
		:type projects: list[csbuild._build.project.Project]
		"""
		_writeProjectFiles(outputDir, solutionName, projects, internal.Version.Vs2015)


class VsSolutionGenerator2017(SolutionGenerator):
	"""Visual Studio 2017 solution generator"""

	@staticmethod
	def GenerateSolution(outputDir, solutionName, projects):
		"""
		Generates the actual solution file from the projects generated by each tool.
		The actual project objects are passed to the solution generator, allowing the generator to gather information
		about the projects themselves, as well as outputs returned from the project generator tools
		(via project.inputFiles[".ext"], which is a list of csbuild._build.input_file.InputFile objects) and
		data on the tools (via calling methods and properties on the tool through project.toolchain.Tool(ToolType).Method()
		or project.toolchain.Tool(ToolType).property)

		:param outputDir: Top-level directory all solution files should be placed into
		:type outputDir: str
		:param solutionName: Desired base name of the solution
		:type solutionName: str
		:param projects: Set of all built projects
		:type projects: list[csbuild._build.project.Project]
		"""
		_writeProjectFiles(outputDir, solutionName, projects, internal.Version.Vs2017)


class VsSolutionGenerator2019(SolutionGenerator):
	"""Visual Studio 2019 solution generator"""

	@staticmethod
	def GenerateSolution(outputDir, solutionName, projects):
		"""
		Generates the actual solution file from the projects generated by each tool.
		The actual project objects are passed to the solution generator, allowing the generator to gather information
		about the projects themselves, as well as outputs returned from the project generator tools
		(via project.inputFiles[".ext"], which is a list of csbuild._build.input_file.InputFile objects) and
		data on the tools (via calling methods and properties on the tool through project.toolchain.Tool(ToolType).Method()
		or project.toolchain.Tool(ToolType).property)

		:param outputDir: Top-level directory all solution files should be placed into
		:type outputDir: str
		:param solutionName: Desired base name of the solution
		:type solutionName: str
		:param projects: Set of all built projects
		:type projects: list[csbuild._build.project.Project]
		"""
		_writeProjectFiles(outputDir, solutionName, projects, internal.Version.Vs2019)


class VsSolutionGenerator2022(SolutionGenerator):
	"""Visual Studio 2022 solution generator"""

	@staticmethod
	def GenerateSolution(outputDir, solutionName, projects):
		"""
		Generates the actual solution file from the projects generated by each tool.
		The actual project objects are passed to the solution generator, allowing the generator to gather information
		about the projects themselves, as well as outputs returned from the project generator tools
		(via project.inputFiles[".ext"], which is a list of csbuild._build.input_file.InputFile objects) and
		data on the tools (via calling methods and properties on the tool through project.toolchain.Tool(ToolType).Method()
		or project.toolchain.Tool(ToolType).property)

		:param outputDir: Top-level directory all solution files should be placed into
		:type outputDir: str
		:param solutionName: Desired base name of the solution
		:type solutionName: str
		:param projects: Set of all built projects
		:type projects: list[csbuild._build.project.Project]
		"""
		_writeProjectFiles(outputDir, solutionName, projects, internal.Version.Vs2022)
