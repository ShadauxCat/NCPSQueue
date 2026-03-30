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
.. package:: internal
	:synopsis: Internal functionality for the Visual Studio solution generator.

.. moduleauthor:: Zoe Bare
"""

from __future__ import unicode_literals, division, print_function

import codecs
import contextlib
import csbuild
import hashlib
import os
import sys
import tempfile
import uuid

from csbuild import log
from csbuild._utils import GetCommandLineString, PlatformString

from xml.etree import ElementTree as ET
from xml.dom import minidom

from ..platform_handlers import VsInstallInfo
from ..platform_handlers.android import VsNsightTegraPlatformHandler
from ..platform_handlers.ps3 import VsPs3PlatformHandler
from ..platform_handlers.ps4 import VsPs4PlatformHandler
from ..platform_handlers.ps5 import VsPs5PlatformHandler
from ..platform_handlers.psvita import VsPsVitaPlatformHandler
from ..platform_handlers.windows import VsWindowsX86PlatformHandler, VsWindowsX64PlatformHandler

from ....assemblers.gcc_assembler import GccAssembler
from ....assemblers.msvc_assembler import MsvcAssembler

from ....cpp_compilers.cpp_compiler_base import CppCompilerBase

from ....java_compilers.java_compiler_base import JavaCompilerBase


class Version(object):
	"""
	Enum values representing Visual Studio versions.
	"""
	Vs2010 = "2010"
	Vs2012 = "2012"
	Vs2013 = "2013"
	Vs2015 = "2015"
	Vs2017 = "2017"
	Vs2019 = "2019"
	Vs2022 = "2022"


FILE_FORMAT_VERSION_INFO = {
	Version.Vs2010: VsInstallInfo("Visual Studio 2010", "11.00", "2010", "v100"),
	Version.Vs2012: VsInstallInfo("Visual Studio 2012", "12.00", "2012", "v110"),
	Version.Vs2013: VsInstallInfo("Visual Studio 2013", "12.00", "2013", "v120"),
	Version.Vs2015: VsInstallInfo("Visual Studio 2015", "12.00", "14", "v140"),
	Version.Vs2017: VsInstallInfo("Visual Studio 2017", "12.00", "15", "v141"),
	Version.Vs2019: VsInstallInfo("Visual Studio 2019", "12.00", "Version 16", "v142"),
	Version.Vs2022: VsInstallInfo("Visual Studio 2022", "12.00", "Version 17", "v143"),
}

CPP_SOURCE_FILE_EXTENSIONS = CppCompilerBase.inputFiles
CPP_HEADER_FILE_EXTENSIONS = { ".h", ".hh", ".hpp", ".hxx" }
OBJC_SOURCE_FILE_EXTENSIONS = { ".m", ".mm" }
HLSL_SOURCE_FILE_EXTENSIONS = { ".hlsl" }
HLSL_HEADER_FILE_EXTENSIONS = { ".hlsli" }
PYTHON_FILE_EXTENSIONS = { ".py" }
BATCH_FILE_EXTENSIONS = { ".bat", ".cmd" }

ASM_FILE_EXTENSIONS = GccAssembler.inputFiles | MsvcAssembler.inputFiles

MISC_FILE_EXTENSIONS = { ".inl", ".inc", ".def" } \
	| JavaCompilerBase.inputGroups

ALL_FILE_EXTENSIONS = CPP_SOURCE_FILE_EXTENSIONS \
	| CPP_HEADER_FILE_EXTENSIONS \
	| OBJC_SOURCE_FILE_EXTENSIONS \
	| HLSL_SOURCE_FILE_EXTENSIONS \
	| HLSL_HEADER_FILE_EXTENSIONS \
	| ASM_FILE_EXTENSIONS \
	| PYTHON_FILE_EXTENSIONS \
	| BATCH_FILE_EXTENSIONS \
	| MISC_FILE_EXTENSIONS

# Switch for toggling the project folders separating files by their extensions.
ENABLE_FILE_TYPE_FOLDERS = False

# Global dictionary of generated UUIDs for Visual Studio projects.  This is needed to make sure there are no
# duplicates when generating new UUIDs.
UUID_TRACKER = {}

# Keep track of the registered platform handlers.
PLATFORM_HANDLERS = {}

# Collection of all valid build specs used by input project generators. This will be pruned against
# registered platform handlers.
BUILD_SPECS = []

# Absolute path to the main makefile that invoked csbuild.
MAKEFILE_PATH = os.path.abspath(sys.modules["__main__"].__file__)

# Absolute path to the "regenerate solution" batch file. This will be filled in when the solution generator is run.
REGEN_FILE_PATH = ""

_createRootXmlNode = ET.Element
_addXmlNode = ET.SubElement

def _makeXmlCommentNode(parentXmlNode, text):
	comment = ET.Comment(text)
	parentXmlNode.append(comment)
	return comment

def _generateUuid(name):
	if not name:
		return "{{{}}}".format(str(uuid.UUID(int=0)))

	name = PlatformString(name if name else "")

	nameIndex = 0
	nameToHash = name

	# Keep generating new UUIDs until we've found one that isn't already in use. This is only useful in cases
	# where we have a pool of objects and each one needs to be guaranteed to have a UUID that doesn't collide
	# with any other object in the same pool.  Though, because of the way UUIDs work, having a collision should
	# be extremely rare anyway.
	while True:
		newUuid = uuid.uuid5( uuid.NAMESPACE_OID, nameToHash )
		mappedName = UUID_TRACKER.get(newUuid, None)

		if not mappedName or mappedName == nameToHash:
			if not mappedName:
				UUID_TRACKER.update({ newUuid: name })

			return "{{{}}}".format(str(newUuid)).upper()

		# Name collision!  The easy solution here is to slightly modify the name in a predictable way.
		nameToHash = "{}{}".format( name, nameIndex )
		nameIndex += 1


def _getVsConfigName(buildSpec):
	# Visual Studio can be exceptionally picky about configuration names.  For instance, if your build script
	# has the "debug" target, you may run into problems with Visual Studio showing that alongside it's own
	# "Debug" configuration, which it may have decided to silently add alongside your own.  The solution is to
	# just put the configurations in a format it expects (first letter upper case). That way, it will see "Debug"
	# already there and won't try to silently 'fix' that up for you.
	return buildSpec[2].capitalize()


def _createBuildSpec(generator):
	return generator.projectData.toolchainName  \
		, generator.projectData.architectureName \
		, generator.projectData.targetName


def _createVsPlatform(buildSpec, platformHandler):
	return "{}|{}".format(_getVsConfigName(buildSpec), platformHandler.GetVisualStudioPlatformName())


def _constructRelPath(filePath, rootPath):
	try:
		# Attempt to construct the relative path from the root.
		newPath = os.path.relpath(filePath, rootPath)

	except:
		# If that fails, return the input path as-is.
		newPath = filePath

	return newPath


def _getItemRootFolderName(filePath):
	fileExt = os.path.splitext(filePath)[1]
	if fileExt in CPP_SOURCE_FILE_EXTENSIONS:
		return "C/C++ source files"
	if fileExt in CPP_HEADER_FILE_EXTENSIONS:
		return "C/C++ header files"
	if fileExt in ASM_FILE_EXTENSIONS:
		return "Assembly source files"
	if fileExt in HLSL_SOURCE_FILE_EXTENSIONS:
		return "Shader source files"
	if fileExt in HLSL_HEADER_FILE_EXTENSIONS:
		return "Shader header files"
	if fileExt in PYTHON_FILE_EXTENSIONS:
		return "Python source files"
	if fileExt in BATCH_FILE_EXTENSIONS:
		return "Batch source files"
	if not fileExt:
		return "Unknown files"

	return "{} files".format(fileExt)


def _getSourceFileProjectStructure(projWorkingPath, projExtraPaths, filePath, separateFileExtensions):
	projStructure = []

	# The first item should be the file name directory if separating by file extension.
	if separateFileExtensions:
		folderName = _getItemRootFolderName(filePath)

		projStructure.append(folderName)

	relativePath = None

	tempPath = _constructRelPath(filePath, projWorkingPath)

	if tempPath != filePath:
		# The input file path is under the project's working directory.
		relativePath = tempPath

	else:
		# The input file path is outside the project's working directory.
		projStructure.append("[External]")

		# Search each extra source directory in the project to see if the input file path is under one of them.
		for extraPath in projExtraPaths:
			tempPath = _constructRelPath(filePath, extraPath)

			if tempPath != filePath:
				# Found the extra source directory that contains the input file path.
				relativePath = tempPath
				rootPath = filePath[:-(len(relativePath) + 1)]
				baseFolderName = os.path.basename(rootPath)

				# For better organization, add the input file to a special directory that hopefully identifies it.
				projStructure.append(baseFolderName)
				break

	if not relativePath:
		# The input file was not found under any source directory, so it'll just be added by itself.
		projStructure.append(os.path.basename(filePath))

	else:
		# Take the relative path and split it into segments to form the remaining directories for the project structure.
		relativePath = relativePath.replace("\\", "/")
		pathSegments = relativePath.split("/")

		projStructure.extend(pathSegments)

	return projStructure


class VsProjectType(object):
	"""
	Enum describing project types.
	"""
	Root = "root"
	Standard = "standard"
	Filter = "filter"


class VsProjectSubType(object):
	"""
	Enum describing project sub-types.
	"""
	Normal = "normal"
	BuildAll = "build_all"
	Regen = "regen"


class VsProjectItemType(object):
	"""
	Enum describing project item types.
	"""
	File = "file"
	Folder = "folder"


class VsProjectItem(object):
	"""
	Container for items owned by Visual Studio projects.
	"""
	def __init__(self, name, dirPath, itemType, parentSegments):
		self.name = name if name else ""
		self.dirPath = dirPath if dirPath else ""
		self.guid = _generateUuid(os.path.join(self.dirPath, self.name))
		self.itemType = itemType
		self.supportedBuildSpecs = set()
		self.children = {}
		self.parentSegments = parentSegments if parentSegments else []
		self.tag = None

		if self.itemType == VsProjectItemType.File:
			fileExt = os.path.splitext(self.name)[1]
			if fileExt in CPP_SOURCE_FILE_EXTENSIONS:
				self.tag = "ClCompile"
			elif fileExt in CPP_HEADER_FILE_EXTENSIONS:
				self.tag = "ClInclude"
			elif fileExt in HLSL_SOURCE_FILE_EXTENSIONS:
				self.tag = "FxCompile"
			else:
				self.tag = "None"

	def GetSegmentPath(self):
		"""
		Get the item parent segments as a path string.

		:return: Parent segment path string.
		:rtype: str
		"""
		return os.sep.join(self.parentSegments)


class VsProject(object):
	"""
	Container for project-level data in Visual Studio.
	"""
	def __init__(self, name, relFilePath, projType):
		makeFileName = os.path.basename(MAKEFILE_PATH)
		makeFileItem = VsProjectItem(makeFileName, os.path.dirname(MAKEFILE_PATH), VsProjectItemType.File, [])
		makeFileItem.supportedBuildSpecs = set(BUILD_SPECS)

		self.name = name
		self.relFilePath = relFilePath
		self.projType = projType
		self.subType = VsProjectSubType.Normal
		self.guid = _generateUuid(name)
		self.children = {}
		self.items = { makeFileItem.name: makeFileItem }
		self.supportedBuildSpecs = set()
		self.platformGenerator = {}
		self.platformOutputType = {}
		self.platformOutputName = {}
		self.platformOutputDirPath = {}
		self.platformIntermediateDirPath = {}
		self.platformIncludePaths = {}
		self.platformDefines = {}
		self.platformCcLanguageStandard = {}
		self.platformCxxLanguageStandard = {}

		self.slnTypeGuid = {
			VsProjectType.Standard: "{8BC9CEB8-8B4A-11D0-8D11-00A0C91BC942}",
			VsProjectType.Filter: "{2150E333-8FDC-42A3-9474-1A3956D46DE8}",
		}.get(self.projType, "{UNKNOWN}")

	def GetVcxProjFilePath(self, extraExtension=""):
		"""
		Get the relative file path to this project's vcxproj file.

		:param extraExtension: Extra part to add onto the file extension (allows us to construct ".vcxproj.filters" and ".vcxproj.user" files.
		:type extraExtension: str

		:return: Relative vcxproj file path.
		:rtype: str
		"""
		return os.path.join("vsproj", self.relFilePath, "{}.vcxproj{}".format(self.name, extraExtension))

	def MergeProjectData(self, buildSpec, generator):
		"""
		Merge data for a given build spec and generator into the project.

		:param buildSpec: Build spec matching the input generator.
		:type buildSpec: tuple[str, str, str]

		:param generator: Generator containing the data that needs to be merged into the project.
		:type generator: csbuild.tools.project_generators.visual_studio.VsProjectGenerator or None
		"""
		if self.projType == VsProjectType.Standard:

			# Register support for the input build spec.
			if buildSpec not in self.supportedBuildSpecs:
				self.supportedBuildSpecs.add(buildSpec)
				self.platformOutputType.update({ buildSpec: csbuild.ProjectType.Application })
				self.platformOutputName.update({ buildSpec: "" })
				self.platformOutputDirPath.update({ buildSpec: "" })
				self.platformIntermediateDirPath.update({ buildSpec: "" })
				self.platformIncludePaths.update({ buildSpec: [] })
				self.platformDefines.update({ buildSpec: [] })
				self.platformCcLanguageStandard.update({ buildSpec: None })
				self.platformCxxLanguageStandard.update({ buildSpec: None })

			# Merge the data from the generator.
			if generator:
				self.platformGenerator[buildSpec] = generator
				self.platformIncludePaths[buildSpec].extend(list(generator.includeDirectories))
				self.platformDefines[buildSpec].extend(list(generator.defines))
				self.platformCcLanguageStandard[buildSpec] = generator.ccLanguageStandard
				self.platformCxxLanguageStandard[buildSpec] = generator.cxxLanguageStandard

				projectData = generator.projectData

				self.platformOutputType[buildSpec] = projectData.projectType
				self.platformOutputName[buildSpec] = projectData.outputName
				self.platformOutputDirPath[buildSpec] = os.path.abspath(projectData.outputDir)
				self.platformIntermediateDirPath[buildSpec] = os.path.abspath(projectData.intermediateDir)

				# Added items for each source file in the project.
				for filePath in generator.sourceFiles:
					fileStructure = _getSourceFileProjectStructure(projectData.workingDirectory, projectData.sourceDirs, filePath, ENABLE_FILE_TYPE_FOLDERS)
					parentMap = self.items

					# Get the file item name, then remove it from the project structure.
					fileItemName = fileStructure[-1]
					fileStructure = fileStructure[:-1]
					parentSegments = []

					# Build the hierarchy of folder items for the current file.
					for segment in fileStructure:
						if segment not in parentMap:
							parentMap.update({ segment: VsProjectItem(segment, os.sep.join(parentSegments), VsProjectItemType.Folder, parentSegments) })

						parentMap = parentMap[segment].children

						# Keep track of each segment along the way since each item (including the folder items)
						# need to know their parent segements when the vcxproj.filters file is generated.
						parentSegments.append(segment)

					if fileItemName not in parentMap:
						# The current file item is new, so map it under the parent item.
						fileItem = VsProjectItem(fileItemName, os.path.dirname(filePath), VsProjectItemType.File, parentSegments)

						parentMap.update({ fileItemName: fileItem })

					else:
						# The current file item already exists, so get the original object for its mapping.
						fileItem = parentMap[fileItemName]

					# Update the set of supported platforms for the current file item.
					fileItem.supportedBuildSpecs.add(buildSpec)


class VsFileProxy(object):
	"""
	Handler for copying a temp file to it's final location.
	"""
	def __init__(self, realFilePath, tempFilePath):
		self.realFilePath = realFilePath
		self.tempFilePath = tempFilePath

	def Check(self):
		"""
		Check the temp file to see if it differs from the output file, then copy if they don't match.
		"""
		outDirPath = os.path.dirname(self.realFilePath)

		# Create the output directory if it doesn't exist.
		if not os.access(outDirPath, os.F_OK):
			os.makedirs(outDirPath)

		# Open the input file and get a hash of its data.
		with open(self.tempFilePath, "rb") as inputFile:
			inputFileData = inputFile.read()
			inputHash = hashlib.md5()

			inputHash.update(inputFileData)

			inputHash = inputHash.hexdigest()

		if os.access(self.realFilePath, os.F_OK):
			# Open the output file and get a hash of its data.
			with open(self.realFilePath, "rb") as outputFile:
				outputFileData = outputFile.read()
				outputHash = hashlib.md5()

				outputHash.update(outputFileData)

				outputHash = outputHash.hexdigest()

		else:
			# The output file doesn't exist, so use an empty string to stand in for the hash.
			outputHash = ""

		# Do a consistency check using the MD5 hashes of the input and output files to determine if we
		# need to copy the data to the output file.
		if inputHash != outputHash:
			log.Build("[WRITING] {}".format(self.realFilePath))

			with open(self.realFilePath, "wb") as outputFile:
				outputFile.write(inputFileData)
				outputFile.flush()
				os.fsync(outputFile.fileno())

		else:
			log.Build("[UP-TO-DATE] {}".format(self.realFilePath))

		os.remove(self.tempFilePath)


def _evaluatePlatforms(generators, vsInstallInfo):
	global PLATFORM_HANDLERS
	global BUILD_SPECS

	if not PLATFORM_HANDLERS:
		# No platform handlers have been registered by user, so we can add reasonable defaults here.
		PLATFORM_HANDLERS.update({
			("android-gcc", "arm", ()): VsNsightTegraPlatformHandler,
			("android-gcc", "arm64", ()): VsNsightTegraPlatformHandler,
			("android-gcc", "x86", ()): VsNsightTegraPlatformHandler,
			("android-gcc", "x64", ()): VsNsightTegraPlatformHandler,
			("android-gcc", "mips", ()): VsNsightTegraPlatformHandler,
			("android-gcc", "mips64", ()): VsNsightTegraPlatformHandler,
			("android-clang", "arm", ()): VsNsightTegraPlatformHandler,
			("android-clang", "arm64", ()): VsNsightTegraPlatformHandler,
			("android-clang", "x86", ()): VsNsightTegraPlatformHandler,
			("android-clang", "x64", ()): VsNsightTegraPlatformHandler,
			("android-clang", "mips", ()): VsNsightTegraPlatformHandler,
			("android-clang", "mips64", ()): VsNsightTegraPlatformHandler,
			("msvc", "x86", ()): VsWindowsX86PlatformHandler,
			("msvc", "x64", ()): VsWindowsX64PlatformHandler,
			("ps3", "cell", ()): VsPs3PlatformHandler,
			("ps4", "x64", ()): VsPs4PlatformHandler,
			("ps5", "x64", ()): VsPs5PlatformHandler,
			("psvita", "arm", ()): VsPsVitaPlatformHandler,
		})

	# Find all specs used by the generators.
	allFoundSpecs = { _createBuildSpec(gen) for gen in generators }
	allFoundTargets = sorted(list({ spec[2] for spec in allFoundSpecs }))
	tempHandlers = {}

	# Instantiate each registered platform handler.
	for key, cls in PLATFORM_HANDLERS.items():
		# Convert the key to a list so we can modify it if necessary.
		key = list(key)

		if not key[2]:
			# If there were no configs specified by the user, that is an indication to use all known configs.
			key[2] = allFoundTargets
		else:
			# Of the configs provided by the user, trim them all down to only those we know about.
			key[2] = [x for x in key[2] if x in allFoundTargets]

		allKeyConfigs = key[2]

		# Split out the configs so each one produces a different key. This will make dictionary lookups easier.
		for config in allKeyConfigs:
			key = (key[0], key[1], config)
			tempHandlers.update({ key: cls })

	sortedHandlerKeys = sorted(tempHandlers.keys())

	log.Info("Found build specs in available projects: {}".format(sorted(allFoundSpecs)))
	log.Info("Build specs mapped to platform handlers: {}".format(sortedHandlerKeys))

	# We have all the handlers stored in a temporary dictionary so we can refill them globally as we validate them.
	PLATFORM_HANDLERS = {}

	foundVsPlatforms = set()
	rejectedBuildSpecs = set()

	# Validate the platform handlers to make sure none of them overlap.
	for key in sortedHandlerKeys:
		# Do not include specs that are not common to the available generators.
		if key in allFoundSpecs:
			cls = tempHandlers[key]
			vsPlatform = _createVsPlatform(key, cls)
			if vsPlatform in foundVsPlatforms:
				rejectedBuildSpecs.add(key)
			else:
				foundVsPlatforms.add(vsPlatform)
				PLATFORM_HANDLERS.update({ key: cls(key, vsInstallInfo) })

	if rejectedBuildSpecs:
		log.Warn("Rejecting the following build specs since they are registered to overlapping Visual Studio platforms: {}".format(sorted(rejectedBuildSpecs)))

	# Prune the generators down to a list with only supported platforms.
	prunedGenerators = [x for x in generators if _createBuildSpec(x) in PLATFORM_HANDLERS]

	foundBuildSpecs = set()

	# Compile a list of all remaining build specs out of the pruned generator.
	for gen in prunedGenerators:
		foundBuildSpecs.add(_createBuildSpec(gen))

	BUILD_SPECS = sorted(foundBuildSpecs)

	if PLATFORM_HANDLERS:
		log.Info("Using Visual Studio platforms: {}".format(", ".join(sorted({ handler.GetVisualStudioPlatformName() for _, handler in PLATFORM_HANDLERS.items() }))))

	return prunedGenerators


def _createRegenerateBatchFile(outputRootPath):
	global REGEN_FILE_PATH

	outputFilePath = os.path.join(outputRootPath, "regenerate_solution.bat")
	pythonExePath = os.path.normcase(sys.executable)
	makefilePath = _constructRelPath(MAKEFILE_PATH, outputRootPath)
	cmdLine = GetCommandLineString()

	tmpFd, tempFilePath = tempfile.mkstemp(prefix="vs_regen_")

	# Write the batch file data.
	with os.fdopen(tmpFd, "w") as f:
		writeLineToFile = lambda text: f.write("{}\n".format(text)) # pylint: disable=unnecessary-lambda-assignment

		writeLineToFile("@echo off")
		writeLineToFile("SETLOCAL")
		writeLineToFile("PUSHD %~dp0")
		writeLineToFile("\"{}\" \"{}\" {}".format(pythonExePath, makefilePath, cmdLine))
		writeLineToFile("POPD")

		f.flush()
		os.fsync(f.fileno())

	REGEN_FILE_PATH = outputFilePath
	proxy = VsFileProxy(REGEN_FILE_PATH, tempFilePath)

	proxy.Check()


def _buildProjectHierarchy(generators):
	rootProject = VsProject(None, "", VsProjectType.Root)
	buildAllProject = VsProject("(BUILD_ALL)", "", VsProjectType.Standard)
	regenProject = VsProject("(REGENERATE_SOLUTION)", "", VsProjectType.Standard)

	# Set the default project special types so they can be identified.
	buildAllProject.subType = VsProjectSubType.BuildAll
	regenProject.subType = VsProjectSubType.Regen

	# The default projects can be used with all build specs.
	for buildSpec in BUILD_SPECS:
		buildAllProject.MergeProjectData(buildSpec, None)
		regenProject.MergeProjectData(buildSpec, None)

	# Add the default projects to the hierarchy.
	rootProject.children.update({
		buildAllProject.name: buildAllProject,
		regenProject.name: regenProject,
	})

	# Parse the data from each project generator.
	for gen in generators:
		buildSpec = _createBuildSpec(gen)
		parent = rootProject

		# Find the appropriate parent project if this project is part of a group.
		for segment in gen.groupSegments:
			# If the current segment in the group is not represented in the current parent's child project list yet,
			# create it and insert it.
			if segment not in parent.children:
				parent.children.update({ segment: VsProject(segment, os.path.join(parent.relFilePath, segment), VsProjectType.Filter) })

			parent = parent.children[segment]

		projName = gen.projectData.name

		if projName not in parent.children:
			# The current project does not exist yet, so create it and map it as a child to the parent project.
			proj = VsProject(projName, parent.relFilePath, VsProjectType.Standard)
			parent.children.update({ projName: proj })

		else:
			# Get the existing project entry from the parent.
			proj = parent.children[projName]

		# Merge the generator's platform data into the project.
		proj.MergeProjectData(buildSpec, gen)

	return rootProject


def _buildFlatProjectList(rootProject):
	flatProjects = []
	projectStack = [rootProject]

	# Build a flat list of all projects and filters.
	while projectStack:
		project = projectStack.pop(0)

		# Add each child project to the stack.
		for projKey in sorted(list(project.children), key=lambda x: x.lower()):
			childProject = project.children[projKey]

			flatProjects.append(childProject)
			projectStack.append(childProject)

	return flatProjects


def _buildFlatProjectItemList(rootItems):
	flatProjectItems = []
	dummyRootItem = VsProjectItem(None, None, None, None)
	itemStack = [dummyRootItem]

	# Assign the input items to the dummy root.
	dummyRootItem.children = rootItems

	# Build a flat list of all projects and filters.
	while itemStack:
		item = itemStack.pop(0)

		# Add each child project to the stack.
		for projKey in sorted(list(item.children)):
			childItem = item.children[projKey]

			flatProjectItems.append(childItem)
			itemStack.append(childItem)

	return flatProjectItems


def _writeSolutionFile(rootProject, outputRootPath, solutionName, vsInstallInfo):
	class SolutionWriter(object): # pylint: disable=missing-docstring
		def __init__(self, fileHandle):
			self.fileHandle = fileHandle
			self.indentation = 0

		def Line(self, text): # pylint: disable=missing-docstring
			self.fileHandle.write("{}{}\r\n".format("\t" * self.indentation, text))

		@contextlib.contextmanager
		def Section(self, sectionName, headerSuffix): # pylint: disable=missing-docstring
			self.Line("{}{}".format(sectionName, headerSuffix))

			self.indentation += 1

			try:
				yield

			finally:
				self.indentation -= 1

				self.Line("End{}".format(sectionName))

	realFilePath = os.path.join(outputRootPath, "{}.sln".format(solutionName))
	tmpFd, tempFilePath = tempfile.mkstemp(prefix="vs_sln_")

	# Close the file since it needs to be re-opened with a specific encoding.
	os.close(tmpFd)

	# Visual Studio solution files need to be UTF-8 with the byte order marker because Visual Studio is VERY picky
	# about these files. If ANYTHING is missing or not formatted properly, the Visual Studio version selector may
	# not open the with the right version or Visual Studio itself may refuse to even attempt to load the file.
	with codecs.open(tempFilePath, "w", "utf-8-sig") as f:
		writer = SolutionWriter(f)

		writer.Line("") # Required empty line.
		writer.Line("Microsoft Visual Studio Solution File, Format Version {}".format(vsInstallInfo.fileVersion))
		writer.Line("# Visual Studio {}".format(vsInstallInfo.versionId))

		flatProjectList = _buildFlatProjectList(rootProject)

		# Write out the initial setup data for each project and filter.
		for project in flatProjectList:
			data = "(\"{}\") = \"{}\", \"{}\", \"{}\"".format(project.slnTypeGuid, project.name, project.GetVcxProjFilePath(), project.guid)

			with writer.Section("Project", data):
				pass

		# Begin setting the global configuration data.
		with writer.Section("Global", ""):

			# Write out the build specs supported by this solution.
			with writer.Section("GlobalSection", "(SolutionConfigurationPlatforms) = preSolution"):
				vsPlatforms = set()
				for buildSpec in BUILD_SPECS:
					handler = PLATFORM_HANDLERS[buildSpec]
					vsPlatform = _createVsPlatform(buildSpec, handler)

					vsPlatforms.add(vsPlatform)

				# Output the platforms sorted case-insensitive as Visual Studio expects.
				for vsPlatform in sorted(vsPlatforms, key=lambda x: x.lower()):
					writer.Line("{0} = {0}".format(vsPlatform))

			# Write out the supported project-to-spec mappings.
			with writer.Section("GlobalSection", "(ProjectConfigurationPlatforms) = postSolution"):
				for project in flatProjectList:
					# Only standard projects should be listed here.
					if project.projType == VsProjectType.Standard:
						vsPlatforms = set()
						for buildSpec in BUILD_SPECS:
							handler = PLATFORM_HANDLERS[buildSpec]
							vsPlatform = _createVsPlatform(buildSpec, handler)

							vsPlatforms.add(vsPlatform)

						# Output the platforms sorted case-insensitive as Visual Studio expects.
						for vsPlatform in sorted(vsPlatforms, key=lambda x: x.lower()):
							writer.Line("{0}.{1}.ActiveCfg = {1}".format(project.guid, vsPlatform))

							# Only enable the BuildAll project.  This will make sure the global build command only
							# builds this project and none of the others (which can still be selectively built).
							if project.subType == VsProjectSubType.BuildAll:
								writer.Line("{0}.{1}.Build.0 = {1}".format(project.guid, vsPlatform))

			# Write out any standalone solution properties.
			with writer.Section("GlobalSection", "(SolutionProperties) = preSolution"):
				writer.Line("HideSolutionNode = FALSE")

			nestedProjectsMappings = set()
			for parentProject in flatProjectList:
				for childProject in parentProject.children:
					nestedProjectsMappings.add("{} = {}".format(childProject.guid, parentProject.guid))

			# Write out the mapping that describe the solution hierarchy.
			if nestedProjectsMappings:
				with writer.Section("GlobalSection", "(NestedProjects) = preSolution"):
					for mapping in sorted(nestedProjectsMappings):
						writer.Line(mapping)

		f.flush()
		os.fsync(f.fileno())

	# Transfer the temp file to the final output location.
	VsFileProxy(realFilePath, tempFilePath).Check()


def _saveXmlFile(realFilePath, rootNode):
	# Grab a string of the XML document we've created and save it.
	xmlString = PlatformString(ET.tostring(rootNode))

	# Use minidom to reformat the XML since ElementTree doesn't do it for us.
	formattedXmlString = PlatformString(minidom.parseString(xmlString).toprettyxml("\t", "\n", encoding = "utf-8"))

	tmpFd, tempFilePath = tempfile.mkstemp(prefix="vs_vcxproj_")

	# Write the temp xml file data.
	with os.fdopen(tmpFd, "w") as f:
		f.write(formattedXmlString)

	VsFileProxy(realFilePath, tempFilePath).Check()


def _writeMainVcxProj(outputRootPath, project, globalPlatformHandlers):
	outputFilePath = os.path.join(outputRootPath, project.GetVcxProjFilePath())
	outputDirPath = os.path.dirname(outputFilePath)

	# Create the root XML node with the default data.
	rootXmlNode = _createRootXmlNode("Project")
	rootXmlNode.set("DefaultTargets", "Build")
	rootXmlNode.set("ToolsVersion", "4.0")
	rootXmlNode.set("xmlns", "http://schemas.microsoft.com/developer/msbuild/2003")

	_makeXmlCommentNode(rootXmlNode, "Project header")

	# Write any top-level information a generator platform may require.
	for _, platformHandler in globalPlatformHandlers.items():
		platformHandler.WriteGlobalHeader(rootXmlNode, project)

	_makeXmlCommentNode(rootXmlNode, "Project configurations")

	itemGroupXmlNode = _addXmlNode(rootXmlNode, "ItemGroup")
	itemGroupXmlNode.set("Label", "ProjectConfigurations")

	# Write the project configurations.
	for buildSpec in BUILD_SPECS:
		platformHandler = PLATFORM_HANDLERS[buildSpec]
		platformHandler.WriteProjectConfiguration(itemGroupXmlNode, project, buildSpec, _getVsConfigName(buildSpec))

	_makeXmlCommentNode(rootXmlNode, "Project files")

	# Write the project's files.
	flatProjectItems = _buildFlatProjectItemList(project.items)
	flatProjectItems = [item for item in flatProjectItems if item.itemType == VsProjectItemType.File]
	groupedProjectItems = {}

	# Group the project file items by XML tag.
	for item in flatProjectItems:
		if item.tag not in groupedProjectItems:
			groupedProjectItems.update({ item.tag: [] })

		groupedProjectItems[item.tag].append(item)

	# Write out each item for each tagged group.
	for key in sorted(groupedProjectItems.keys()):
		projectItems = groupedProjectItems[key]
		itemGroupXmlNode = _addXmlNode(rootXmlNode, "ItemGroup")

		for item in projectItems:
			sourceFileXmlNode = _addXmlNode(itemGroupXmlNode, item.tag)
			sourceFileXmlNode.set("Include", _constructRelPath(os.path.join(item.dirPath, item.name), outputDirPath))

			excludeBuildSpecs = set(BUILD_SPECS).difference(item.supportedBuildSpecs)
			vsExcludedBuildTargets = []

			for buildSpec in excludeBuildSpecs:
				platformHandler = PLATFORM_HANDLERS[buildSpec]
				vsConfig = _getVsConfigName(buildSpec)
				vsPlatformName = platformHandler.GetVisualStudioPlatformName()
				vsBuildTarget = "{}|{}".format(vsConfig, vsPlatformName)

				vsExcludedBuildTargets.append(vsBuildTarget)

			vsExcludedBuildTargets = sorted(vsExcludedBuildTargets, key=lambda x: x.lower())

			# Exclude the file item for each unsupported build spec.
			for vsBuildTarget in vsExcludedBuildTargets:
				excludeXmlNode = _addXmlNode(sourceFileXmlNode, "ExcludedFromBuild")
				excludeXmlNode.set("Condition", "'$(Configuration)|$(Platform)'=='{}'".format(vsBuildTarget))
				excludeXmlNode.text = "true"

	_makeXmlCommentNode(rootXmlNode, "Project global properties")

	# Add the global property group.
	propertyGroupXmlNode = _addXmlNode(rootXmlNode, "PropertyGroup")
	propertyGroupXmlNode.set("Label", "Globals")

	_makeXmlCommentNode(rootXmlNode, "Import properties")

	importXmlNode = _addXmlNode(rootXmlNode, "Import")
	importXmlNode.set("Project", r"$(VCTargetsPath)\Microsoft.Cpp.Default.props")

	projectGuidXmlNode = _addXmlNode(propertyGroupXmlNode, "ProjectGuid")
	projectGuidXmlNode.text = project.guid

	namespaceXmlNode = _addXmlNode(propertyGroupXmlNode, "RootNamespace")
	namespaceXmlNode.text = project.name

	# We're not creating a native project, so Visual Studio needs to know this is a makefile project.
	keywordXmlNode = _addXmlNode(propertyGroupXmlNode, "Keyword")
	keywordXmlNode.text = "MakeFileProj"

	_makeXmlCommentNode(rootXmlNode, "Platform config property groups")

	# Write the config property groups for each platform.
	for buildSpec in BUILD_SPECS:
		platformHandler = PLATFORM_HANDLERS[buildSpec]
		platformHandler.WriteConfigPropertyGroup(rootXmlNode, project, buildSpec, _getVsConfigName(buildSpec))

	_makeXmlCommentNode(rootXmlNode, "Import properties (continued)")

	# Write out the standard import property.
	importXmlNode = _addXmlNode(rootXmlNode, "Import")
	importXmlNode.set("Project", r"$(VCTargetsPath)\Microsoft.Cpp.props")

	# Write the import properties for each platform.
	for buildSpec in BUILD_SPECS:
		# Skip build specs that are not supported by the project.
		if buildSpec not in project.supportedBuildSpecs:
			continue

		platformHandler = PLATFORM_HANDLERS[buildSpec]
		platformHandler.WriteImportProperties(rootXmlNode, project, buildSpec, _getVsConfigName(buildSpec))

	_makeXmlCommentNode(rootXmlNode, "Platform build commands")

	# Write the build commands for each platform.
	for buildSpec in BUILD_SPECS:
		# Skip build specs that are not supported by the project.
		if buildSpec not in project.supportedBuildSpecs:
			continue

		platformHandler = PLATFORM_HANDLERS[buildSpec]
		extraBuildArgs = csbuild.GetSolutionArgs().replace(",", " ")

		if project.subType == VsProjectSubType.Regen:
			buildArgs = [
				"\"{}\"".format(_constructRelPath(REGEN_FILE_PATH, outputDirPath))
			]

			rebuildArgs = buildArgs
			cleanArgs = buildArgs

		else:
			buildArgs = [
				"\"{}\"".format(os.path.normcase(sys.executable)),
				"\"{}\"".format(_constructRelPath(MAKEFILE_PATH, outputDirPath)),
				"-o", "\"{}\"".format(buildSpec[0]),
				"-a", "\"{}\"".format(buildSpec[1]),
				"-t", "\"{}\"".format(buildSpec[2]),
			]

			if project.subType != VsProjectSubType.BuildAll:
				buildArgs.extend([
					"-p", "\"{}\"".format(project.name),
				])

			rebuildArgs = buildArgs + ["-r", extraBuildArgs]
			cleanArgs = buildArgs + ["-c", extraBuildArgs]

			buildArgs.append(extraBuildArgs)

		buildArgs = " ".join([x for x in buildArgs if x])
		rebuildArgs = " ".join([x for x in rebuildArgs if x])
		cleanArgs = " ".join([x for x in cleanArgs if x])

		vsConfig = _getVsConfigName(buildSpec)
		vsPlatformName = platformHandler.GetVisualStudioPlatformName()
		vsBuildTarget = "{}|{}".format(vsConfig, vsPlatformName)

		vsIncludePaths = platformHandler.GetIntellisenseIncludeSearchPaths(project, buildSpec) + \
			sorted({ _constructRelPath(incPath, outputDirPath) for incPath in project.platformIncludePaths[buildSpec] })

		vsDefines = platformHandler.GetIntellisensePreprocessorDefinitions(project, buildSpec) + \
			sorted(set(project.platformDefines[buildSpec])) + \
			["$(NMakePreprocessorDefinitions)"]

		propertyGroupXmlNode = _addXmlNode(rootXmlNode, "PropertyGroup")
		propertyGroupXmlNode.set("Condition", "'$(Configuration)|$(Platform)'=='{}'".format(vsBuildTarget))

		buildCommandXmlNode = _addXmlNode(propertyGroupXmlNode, "NMakeBuildCommandLine")
		buildCommandXmlNode.text = buildArgs

		rebuildCommandXmlNode = _addXmlNode(propertyGroupXmlNode, "NMakeReBuildCommandLine")
		rebuildCommandXmlNode.text = rebuildArgs

		cleanCommandXmlNode = _addXmlNode(propertyGroupXmlNode, "NMakeCleanCommandLine")
		cleanCommandXmlNode.text = cleanArgs

		includePathXmlNode = _addXmlNode(propertyGroupXmlNode, "NMakeIncludeSearchPath")
		includePathXmlNode.text = ";".join([x for x in vsIncludePaths if x])

		preprocessorXmlNode = _addXmlNode(propertyGroupXmlNode, "NMakePreprocessorDefinitions")
		preprocessorXmlNode.text = ";".join([x for x in vsDefines if x])

		if project.subType == VsProjectSubType.Normal:
			buildOutputType = project.platformOutputType[buildSpec]
			buildOutputName = project.platformOutputName[buildSpec]
			buildOutputDirPath = project.platformOutputDirPath[buildSpec]
			buildIntermediateDirPath = project.platformIntermediateDirPath[buildSpec]

			outputExtension = platformHandler.GetOutputExtensionIfDebuggable(buildOutputType)
			additionalOptions = platformHandler.GetIntellisenseAdditionalOptions(project, buildSpec)

			# Only include the NMakeOutput extension if the current project build has a debuggable output type.
			# This is what Visual Studio will look for when attempting to debug.
			if outputExtension:
				outputXmlNode = _addXmlNode(propertyGroupXmlNode, "NMakeOutput")
				outputXmlNode.text = _constructRelPath(os.path.join(buildOutputDirPath, "{}{}".format(buildOutputName, outputExtension)), outputDirPath)

			_addXmlNode(propertyGroupXmlNode, "OutDir").text = _constructRelPath(buildOutputDirPath, outputDirPath)
			_addXmlNode(propertyGroupXmlNode, "IntDir").text = _constructRelPath(buildIntermediateDirPath, outputDirPath)

			if additionalOptions:
				_addXmlNode(propertyGroupXmlNode, "AdditionalOptions").text = additionalOptions

		else:
			_addXmlNode(propertyGroupXmlNode, "OutDir").text = ".out"
			_addXmlNode(propertyGroupXmlNode, "IntDir").text = ".int"

		platformHandler.WriteExtraPropertyGroupBuildNodes(propertyGroupXmlNode, project, buildSpec, vsConfig)

	_makeXmlCommentNode(rootXmlNode, "Import targets")

	# Write the global import targets.
	# MUST be before the "Microsoft.Cpp.targets" import!
	for _, platformHandler in globalPlatformHandlers.items():
		platformHandler.WriteGlobalImportTargets(rootXmlNode, project)

	_makeXmlCommentNode(rootXmlNode, "Final import target; must always be the LAST import target!")

	importXmlNode = _addXmlNode(rootXmlNode, "Import")
	importXmlNode.set("Project", r"$(VCTargetsPath)\Microsoft.Cpp.targets")

	_makeXmlCommentNode(rootXmlNode, "Project footer")

	# Write any trailing information needed by the project.
	for _, platformHandler in globalPlatformHandlers.items():
		platformHandler.WriteGlobalFooter(rootXmlNode, project)

	# Write out the XML file.
	_saveXmlFile(outputFilePath, rootXmlNode)


def _writeFiltersVcxProj(outputRootPath, project):
	outputFilePath = os.path.join(outputRootPath, project.GetVcxProjFilePath(".filters"))
	outputDirPath = os.path.dirname(outputFilePath)

	rootXmlNode = _createRootXmlNode("Project")
	rootXmlNode.set("ToolsVersion", "4.0")
	rootXmlNode.set("xmlns", "http://schemas.microsoft.com/developer/msbuild/2003")

	# Get a complete list of all items in the project.
	flatProjectItems = _buildFlatProjectItemList(project.items)
	if flatProjectItems:
		# Separate the folder items from the file items.
		projectFolderItems = [item for item in flatProjectItems if item.itemType == VsProjectItemType.Folder]
		projectFileItems = [item for item in flatProjectItems if item.itemType == VsProjectItemType.File]
		groupedFileItems = {}

		# Split the file items by XML tag.
		for item in projectFileItems:
			if item.tag not in groupedFileItems:
				groupedFileItems.update({ item.tag: [] })

			groupedFileItems[item.tag].append(item)

		if projectFolderItems:
			itemGroupXmlNode = _addXmlNode(rootXmlNode, "ItemGroup")

			# Write out the filter nodes.
			for item in projectFolderItems:
				filterXmlNode = _addXmlNode(itemGroupXmlNode, "Filter")
				filterXmlNode.set("Include", os.path.join(item.dirPath, item.name))

				uniqueIdXmlNode = _addXmlNode(filterXmlNode, "UniqueIdentifier")
				uniqueIdXmlNode.text = item.guid

		# Go through each item tag.
		for itemTag in sorted(groupedFileItems.keys()):
			fileItems = groupedFileItems[itemTag]

			itemGroupXmlNode = _addXmlNode(rootXmlNode, "ItemGroup")

			# Write out the project file items for the current tag.
			for item in fileItems:
				sourceFileXmlNode = _addXmlNode(itemGroupXmlNode, item.tag)
				sourceFileXmlNode.set("Include", _constructRelPath(os.path.join(item.dirPath, item.name), outputDirPath))

				filterXmlNode = _addXmlNode(sourceFileXmlNode, "Filter")
				filterXmlNode.text = item.GetSegmentPath()

	# Write out the XML file.
	_saveXmlFile(outputFilePath, rootXmlNode)


def _writeUserVcxProj(outputRootPath, project, preserve):
	outputFilePath = os.path.join(outputRootPath, project.GetVcxProjFilePath(".user"))

	# Create the xml document if we're not explicitly preserving the old file or the old file doesn't exist.
	if not preserve or not os.access(outputFilePath, os.F_OK):
		rootXmlNode = _createRootXmlNode("Project")
		rootXmlNode.set("ToolsVersion", "4.0")
		rootXmlNode.set("xmlns", "http://schemas.microsoft.com/developer/msbuild/2003")

		# Write out the user debug settings
		if project.subType == VsProjectSubType.Normal:
			for buildSpec in BUILD_SPECS:
				# Skip build specs that are not supported by the project.
				if buildSpec not in project.supportedBuildSpecs:
					continue

				platformHandler = PLATFORM_HANDLERS[buildSpec]
				platformHandler.WriteUserDebugPropertyGroup(rootXmlNode, project, buildSpec, _getVsConfigName(buildSpec))

		# Write out the XML file.
		_saveXmlFile(outputFilePath, rootXmlNode)

	else:
		# No output file needed.
		log.Build("[SKIPPING] {}".format(outputFilePath))



def _writeProjectFiles(rootProject, outputRootPath, preserveUserFiles):
	flatProjectList = _buildFlatProjectList(rootProject)
	globalPlatformHandlers = {}

	# We'll need a single copy of each platform's handler regardless of VS config.
	# Having this mapping simplifies the lookup when writing the global sections.
	for buildSpec in BUILD_SPECS:
		platformHandler = PLATFORM_HANDLERS[buildSpec]
		vsPlatformName = platformHandler.GetVisualStudioPlatformName()

		if vsPlatformName not in globalPlatformHandlers:
			globalPlatformHandlers.update({ vsPlatformName: platformHandler })

	# Write all the necessary files for each projects.
	for project in flatProjectList:
		if project.projType == VsProjectType.Standard:
			_writeMainVcxProj(outputRootPath, project, globalPlatformHandlers)
			_writeFiltersVcxProj(outputRootPath, project)
			_writeUserVcxProj(outputRootPath, project, preserveUserFiles)


def UpdatePlatformHandlers(handlers): # pylint: disable=missing-docstring
	fixedHandlers = {}

	# Validate the handlers before adding the mappings to the global dictionary.
	for key, cls in handlers:
		if isinstance(key, tuple) and cls is not None:
			key = list(key) # Convert the key to a list so we can modify it if necessary.

			# Discard any tuple keys that don't have at least 3 elements.
			if len(key) < 3:
				log.Warn("Discarding Visual Studio platform handler mapping due to incorrect key format: {}".format(key))
				continue

			# Limit the key tuple to 3 elements.
			key = key[:3]

			# It's valid for the 3rd element to be a string initially, but for the mappings, we'll need it in a list.
			if isinstance(key[2], str):
				key[2] = ( key[2], )

			# Anything else will default to an empty list.
			elif not isinstance(key[2], tuple) or key[2] is None:
				key[2] = tuple()

			# Convert the key back to a tuple for mapping it into the fixed handlers dictionary.
			key = tuple(key)

			fixedHandlers[key] = cls

	PLATFORM_HANDLERS.update(fixedHandlers)


def WriteProjectFiles(outputRootPath, solutionName, generators, vsVersion):
	"""
	Write out the Visual Studio project files.

	:param outputRootPath: Root path for all output files.
	:type outputRootPath: str

	:param solutionName: Name of the output solution file.
	:type solutionName: str

	:param generators: List of project generators.
	:type generators: list[csbuild.tools.project_generators.visual_studio.VsProjectGenerator]

	:param vsVersion: Version of Visual Studio to create projects for.
	:type vsVersion: str
	"""
	vsInstallInfo = FILE_FORMAT_VERSION_INFO.get(vsVersion, None)
	if not vsInstallInfo:
		log.Error("Unknown version of Visual Studio: {}".format(vsVersion))
		return

	log.Build("Creating project files for {}".format(vsInstallInfo.friendlyName))

	generators = _evaluatePlatforms(generators, vsInstallInfo)
	if not generators:
		log.Error("No projects available, cannot generate solution")
		return

	_createRegenerateBatchFile(outputRootPath)

	rootProject = _buildProjectHierarchy(generators)
	preserveUserFiles = True # TODO: This should eventually be set from a command line switch.

	_writeSolutionFile(rootProject, outputRootPath, solutionName, vsInstallInfo)
	_writeProjectFiles(rootProject, outputRootPath, preserveUserFiles)
