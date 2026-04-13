#!/usr/bin/env python3

import platform
import csbuild
import glob
import os
import shutil

with csbuild.ToolchainGroup("gnu"):
	csbuild.AddCompilerFlags("-pthread")

csbuild.SetUserData("subdir", platform.system())
csbuild.SetCxxLanguageStandard("c++20")

with csbuild.Toolchain("msvc"):
	csbuild.AddCompilerFlags("/EHsc", "/bigobj")
	csbuild.AddLibraryDirectories("external/tbb/win/lib")

with csbuild.ToolchainGroup("gnu"):
	with csbuild.Platform("Darwin"):
		csbuild.AddLibraryDirectories("external/tbb/mac/{architectureName}")

	with csbuild.Platform("Linux"):
		csbuild.AddLibraries("pthread")
		csbuild.AddLibraryDirectories("external/tbb/linux/{architectureName}")

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

	with csbuild.Toolchain("msvc"):
		with csbuild.Target("debug"):
			csbuild.AddLibraries("tbb12_debug")

		with csbuild.Target("fastdebug", "release"):
			csbuild.AddLibraries("tbb12")

@csbuild.OnBuildFinished
def buildComplete(projects):
	archName = projects[0].architectureName
	libDirName = {
		"Windows": "win/bin",
		"Linux": f"linux/{archName}",
		"Darwin": f"mac/{archName}",
	}.get(platform.system(), None)
	if libDirName:
		for f in glob.glob(f"external/tbb/{libDirName}/*"):
			if os.path.isdir(f):
				continue
			basename = os.path.basename(f)
			dest = os.path.join(projects[0].outputDir, basename)
			if not os.path.exists(dest):
				print("Copying {} to {}".format(f, dest))
				shutil.copyfile(f, dest)

