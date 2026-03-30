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
.. package:: platform_handlers
	:synopsis: Built-in platform handlers for the Visual Studio project generator.

.. moduleauthor:: Zoe Bare
"""

from __future__ import unicode_literals, division, print_function

import abc

from csbuild._utils.decorators import MetaClass

from xml.etree import ElementTree as ET

def _ignore(_):
	pass

class VsInstallInfo(object):
	"""
	Visual Studio version data helper class.

	:ivar friendlyName: Friendly version name for logging.
	:type friendlyName: str

	:ivar fileVersion: File format version (e.g., "Microsoft Visual Studio Solution File, Format Version XX.XX" where "XX.XX" is the member value).
	:type fileVersion: str

	:ivar versionId: Version of Visual Studio the solution belongs to (e.g., "# Visual Studio XX" where "XX" is the member value).
	:type versionId: str

	:ivar toolsetVersion: Platform toolset version for the Visual Studio version.
	:type toolsetVersion: str
	"""
	def __init__(self, friendlyName, fileVersion, versionId, toolsetVersion):
		self.friendlyName = friendlyName
		self.fileVersion = fileVersion
		self.versionId = versionId
		self.toolsetVersion = toolsetVersion


@MetaClass(abc.ABCMeta)
class VsBasePlatformHandler(object):
	"""
	Visual Studio platform handler base class.

	:ivar buildSpec: Internal build specification being written.
	:type buildSpec: tuple[str, str, str]

	:ivar vsInstallInfo: Information relating to the selected version of Visual Studio.
	:type vsInstallInfo: csbuild.tools.project_generators.visual_studio.platform_handlers.VsInstallInfo
	"""
	def __init__(self, buildSpec, vsInstallInfo):
		self.buildSpec = buildSpec
		self.vsInstallInfo = vsInstallInfo

		self._addXmlNode = ET.SubElement

	@staticmethod
	def GetVisualStudioPlatformName():
		"""
		Get the name that is recognizeable by Visual Studio for the current platform.

		:return: Visual Studio platform name.
		:rtype: str
		"""
		pass

	@staticmethod
	def GetOutputExtensionIfDebuggable(projectOutputType):
		"""
		Get the file extension of the input project output type for the current platform.
		Only applies to debuggable projects.  Any other project types should return `None`.

		:param projectOutputType: Final output type of a project.
		:type projectOutputType: any

		:return: Application extension.
		:rtype: str or None
		"""
		_ignore(projectOutputType)
		return None

	@staticmethod
	def GetIntellisenseIncludeSearchPaths(project, buildSpec):
		"""
		Get a list of any platform-specific include search paths needed by intellisense.

		:param project: Visual Studio project data.
		:type project: csbuild.tools.project_generators.visual_studio.internal.VsProject

		:param buildSpec: Build spec being written to use with the project data.
		:type buildSpec: tuple[str, str, str]

		:return: List of include search paths.
		:rtype: list[str]
		"""
		_ignore(project)
		_ignore(buildSpec)
		return []

	@staticmethod
	def GetIntellisensePreprocessorDefinitions(project, buildSpec):
		"""
		Get a list of any platform-specific preprocessor definitions needed by intellisense.

		:param project: Visual Studio project data.
		:type project: csbuild.tools.project_generators.visual_studio.internal.VsProject

		:param buildSpec: Build spec being written to use with the project data.
		:type buildSpec: tuple[str, str, str]

		:return: List of preprocessor definitions.
		:rtype: list[str]
		"""
		_ignore(project)
		_ignore(buildSpec)
		return []

	@staticmethod
	def GetIntellisenseAdditionalOptions(project, buildSpec):
		"""
		Get any additional NMake options to configure intellisense.

		:param project: Visual Studio project data.
		:type project: csbuild.tools.project_generators.visual_studio.internal.VsProject

		:param buildSpec: Build spec being written to use with the project data.
		:type buildSpec: tuple[str, str, str]

		:return: Additional NMake options.
		:rtype: str or None
		"""
		_ignore(project)
		_ignore(buildSpec)
		return ""

	def WriteGlobalHeader(self, parentXmlNode, project):
		"""
		Write any top-level information about this platform at the start of the project file.

		:param parentXmlNode: Parent project XML node.
		:type parentXmlNode: xml.etree.ElementTree.SubElement

		:param project: Visual Studio project data.
		:type project: csbuild.tools.project_generators.visual_studio.internal.VsProject
		"""
		pass

	def WriteGlobalFooter(self, parentXmlNode, project):
		"""
		Write any final data nodes needed by the project.

		:param parentXmlNode: Parent project XML node.
		:type parentXmlNode: xml.etree.ElementTree.SubElement

		:param project: Visual Studio project data.
		:type project: csbuild.tools.project_generators.visual_studio.internal.VsProject
		"""
		pass

	def WriteGlobalImportTargets(self, parentXmlNode, project):
		"""
		Write global import target needed for the project.

		:param parentXmlNode: Parent project XML node.
		:type parentXmlNode: xml.etree.ElementTree.SubElement

		:param project: Visual Studio project data.
		:type project: csbuild.tools.project_generators.visual_studio.internal.VsProject
		"""
		pass

	def WriteProjectConfiguration(self, parentXmlNode, project, buildSpec, vsConfig):
		"""
		Write the project configuration nodes for this platform.

		:param parentXmlNode: Parent project XML node.
		:type parentXmlNode: xml.etree.ElementTree.SubElement

		:param project: Visual Studio project data.
		:type project: csbuild.tools.project_generators.visual_studio.internal.VsProject

		:param buildSpec: Build spec being written to use with the project data.
		:type buildSpec: tuple[str, str, str]

		:param vsConfig: Visual Studio configuration being written.
		:type vsConfig: str
		"""
		_ignore(project)
		_ignore(buildSpec)

		vsPlatformName = self.GetVisualStudioPlatformName()
		vsBuildTarget = "{}|{}".format(vsConfig, vsPlatformName)

		projectConfigXmlNode = self._addXmlNode(parentXmlNode, "ProjectConfiguration")
		projectConfigXmlNode.set("Include", vsBuildTarget)

		configXmlNode = self._addXmlNode(projectConfigXmlNode, "Configuration")
		configXmlNode.text = vsConfig

		platformXmlNode = self._addXmlNode(projectConfigXmlNode, "Platform")
		platformXmlNode.text = vsPlatformName

	def WriteConfigPropertyGroup(self, parentXmlNode, project, buildSpec, vsConfig):
		"""
		Write the property group nodes for the project's configuration and platform.

		:param parentXmlNode: Parent project XML node.
		:type parentXmlNode: xml.etree.ElementTree.SubElement

		:param project: Visual Studio project data.
		:type project: csbuild.tools.project_generators.visual_studio.internal.VsProject

		:param buildSpec: Build spec being written to use with the project data.
		:type buildSpec: tuple[str, str, str]

		:param vsConfig: Visual Studio configuration being written.
		:type vsConfig: str
		"""
		pass

	def WriteImportProperties(self, parentXmlNode, project, buildSpec, vsConfig):
		"""
		Write any special import properties for this platform.

		:param parentXmlNode: Parent project XML node.
		:type parentXmlNode: xml.etree.ElementTree.SubElement

		:param project: Visual Studio project data.
		:type project: csbuild.tools.project_generators.visual_studio.internal.VsProject

		:param buildSpec: Build spec being written to use with the project data.
		:type buildSpec: tuple[str, str, str]

		:param vsConfig: Visual Studio configuration being written.
		:type vsConfig: str
		"""
		_ignore(project)
		_ignore(buildSpec)

		vsPlatformName = self.GetVisualStudioPlatformName()
		vsBuildTarget = "{}|{}".format(vsConfig, vsPlatformName)

		importGroupXmlNode = self._addXmlNode(parentXmlNode, "ImportGroup")
		importGroupXmlNode.set("Label", "PropertySheets")
		importGroupXmlNode.set("Condition", "'$(Configuration)|$(Platform)'=='{}'".format(vsBuildTarget))

		importXmlNode = self._addXmlNode(importGroupXmlNode, "Import")
		importXmlNode.set("Label", "LocalAppDataPlatform")
		importXmlNode.set("Project", r"$(UserRootDir)\Microsoft.Cpp.$(Platform).user.props")
		importXmlNode.set("Condition", r"exists('$(UserRootDir)\Microsoft.Cpp.$(Platform).user.props')")

	def WriteUserDebugPropertyGroup(self, parentXmlNode, project, buildSpec, vsConfig):
		"""
		Write the property group nodes specifying the user debug settings.

		:param parentXmlNode: Parent project XML node.
		:type parentXmlNode: xml.etree.ElementTree.SubElement

		:param project: Visual Studio project data.
		:type project: csbuild.tools.project_generators.visual_studio.internal.VsProject

		:param buildSpec: Build spec being written to use with the project data.
		:type buildSpec: tuple[str, str, str]

		:param vsConfig: Visual Studio configuration being written.
		:type vsConfig: str
		"""
		pass

	def WriteExtraPropertyGroupBuildNodes(self, parentXmlNode, project, buildSpec, vsConfig):
		"""
		Write extra property group nodes related to platform build properties.

		:param parentXmlNode: Parent project XML node.
		:type parentXmlNode: xml.etree.ElementTree.SubElement

		:param project: Visual Studio project data.
		:type project: csbuild.tools.project_generators.visual_studio.internal.VsProject

		:param buildSpec: Build spec being written to use with the project data.
		:type buildSpec: tuple[str, str, str]

		:param vsConfig: Visual Studio configuration being written.
		:type vsConfig: str
		"""
		pass
