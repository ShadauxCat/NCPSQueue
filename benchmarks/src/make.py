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
	csbuild.AddCompilerFlags("/EHsc", "/bigobj")
	csbuild.AddCompilerFlags("/std:c++20")
	csbuild.AddLibraryDirectories("external/tbb/win/lib")
	
with csbuild.ToolchainGroup("gnu"):
	csbuild.AddCompilerFlags("-std=c++20", "-pthread")
	csbuild.AddLibraries("pthread")
	csbuild.AddLibraryDirectories("external/tbb/gnu/lib")

with csbuild.Project("QueueTests", "src", []):
	csbuild.SetOutputDirectory("bin")
	csbuild.SetIntermediateDirectory(".csbuild/Intermediate/{userData.subdir}-{architectureName}-{targetName}")
	csbuild.AddLibraries("tbb")
	csbuild.AddIncludeDirectories(
		"external/tbb/include", 
		"external",
		"external/ConcurrencyFreaks/CPP/queues",
		"external/xenium"
	)

	with csbuild.Target("debug"):
		csbuild.AddLibraries("tbb12_debug")

	with csbuild.Target("fastdebug", "release"):
		csbuild.AddLibraries("tbb12")


	@csbuild.OnBuildFinished
	def buildComplete(projects):
		for f in glob.glob("external/tbb/win/bin/*".format(project=projects[0])):
			if os.path.isdir(f):
				continue
			basename = os.path.basename(f)
			dest = os.path.join(projects[0].outputDir, basename)
			if not os.path.exists(dest):
				print("Copying {} to {}".format(f, dest))
				shutil.copyfile(f, dest)
	
