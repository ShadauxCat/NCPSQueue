#!/usr/bin/python

import platform
import csbuild
import glob
import os
import shutil

with csbuild.ToolchainGroup("gnu"):
	csbuild.AddCompilerFlags("-pthread")
		
csbuild.SetUserData("subdir", platform.system())


with csbuild.Toolchain("msvc"):
	csbuild.AddCompilerFlags("/EHsc")
	
with csbuild.ToolchainGroup("gnu"):
	csbuild.AddCompilerFlags("-std=c++11")

with csbuild.Project("QueueTests", ".", [], autoDiscoverSourceFiles=False):
	csbuild.SetOutputDirectory(".")
	csbuild.SetIntermediateDirectory(".csbuild/Intermediate/{userData.subdir}-{architectureName}-{targetName}")
	csbuild.AddSourceFiles("main.cpp")
	csbuild.AddIncludeDirectories("ext/include")
	csbuild.AddLibraryDirectories("ext/lib/{userData.subdir}-{architectureName}")
	csbuild.AddExcludeDirectories("ext")
	csbuild.AddLibraries("tbb")

	@csbuild.OnBuildFinished
	def buildComplete(projects):
		for f in glob.glob("ext/lib/{project.userData.subdir}-{project.architectureName}/*".format(project=projects[0])):
			basename = os.path.basename(f)
			dest = os.path.join(projects[0].outputDir, basename)
			if not os.path.exists(dest):
				print("Copying {} to {}".format(f, dest))
				shutil.copyfile(f, dest)
	