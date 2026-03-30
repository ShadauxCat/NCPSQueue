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
.. package:: _build
	:synopsis: Logic related to actually running a build
"""

# Import this stuff to appease pylint
from __future__ import unicode_literals, division, print_function

import shutil

import csbuild
import argparse
import os
import sys
import math
import multiprocessing
import time
import threading
import collections

from . import recompile
from . import project_plan, project, input_file
from .. import log, commands, tools, perf_timer
from ..dependency import Dependency
from .._utils import system, shared_globals, thread_pool, terminfo, ordered_set, FormatTime, queue, dag, MultiBreak, PlatformString, settings_manager, module_importer
from .._utils.decorators import TypeChecked
from .._utils.string_abc import String

if sys.version_info[0] >= 3:
	_typeType = type
	_classType = type
else:
	import types
	# pylint: disable=invalid-name
	_typeType = types.TypeType
	_classType = types.ClassType


class _dummy(object):
	def __setattr__(self, key, value):
		pass
	def __getattribute__(self, item):
		return ""

_runningBuilds = 0

def _canRun(tool):
	return tool.maxParallel <= 0 or tool.curParallel < tool.maxParallel

def _enqueueBuild(buildProject, tool, buildInput, pool, projectList, projectsWithCrossProjectDeps, inputExtension, doCompileCheck=False):
	with perf_timer.PerfTimer("Enqueuing build tasks"):
		global _runningBuilds
		_runningBuilds += 1
		tool.curParallel += 1
		shared_globals.totalBuilds += 1
		log.UpdateProgressBar()

		buildProject.toolchain.CreateReachability(tool)

		if tool.exclusive:
			try:
				buildProject.inputFiles[inputExtension].remove(buildInput)
			except KeyError:
				#Wasn't in there so nothing to remove.
				pass

		if buildInput is None:
			buildProject.toolchain.DeactivateTool(tool)
			log.Info("Enqueuing null-input build for {} for project {}", tool.__name__, buildProject)
			pool.AddTask(
				(_logThenRun, tool.Run, tool, buildProject.toolchain, buildProject, None, doCompileCheck),
				(_buildFinished, pool, projectList, projectsWithCrossProjectDeps, buildProject, tool, None, None)
			)
		elif isinstance(buildInput, input_file.InputFile):
			buildInput.AddUsedTool(tool)
			log.Info("Enqueuing build for {} using {} for project {}", buildInput, tool.__name__, buildProject)
			pool.AddTask(
				(_logThenRun, tool.Run, tool, buildProject.toolchain, buildProject, buildInput, doCompileCheck),
				(_buildFinished, pool, projectList, projectsWithCrossProjectDeps, buildProject, tool, inputExtension, [buildInput])
			)
		else:
			for inputFile in buildInput:
				inputFile.AddUsedTool(tool)

			log.Info("Enqueuing multi-build task for {} using {} for project {}", buildProject, buildInput, tool.__name__, buildProject)
			pool.AddTask(
				(_logThenRun, tool.RunGroup, tool, buildProject.toolchain, buildProject, buildInput, doCompileCheck),
				(_buildFinished, pool, projectList, projectsWithCrossProjectDeps, buildProject, tool, None, buildInput)
			)

def _dependenciesMet(buildProject, tool):
	with perf_timer.PerfTimer("Dependency checks"):
		log.Info("Checking if we can enqueue a new build for tool {} for project {}", tool.__name__, buildProject)
		for dependProject in buildProject.dependencies:
			for dependency in tool.crossProjectDependencies:
				if dependProject.toolchain.IsOutputActive(dependency):
					return False

		for dependency in tool.dependencies:
			if buildProject.toolchain.IsOutputActive(dependency):
				return False
		return True

def _getGroupInputFiles(buildProject, tool):
	with perf_timer.PerfTimer("Collecting group inputs"):
		fileList = ordered_set.OrderedSet()
		if tool.crossProjectInputGroups:
			for inputFile in tool.crossProjectInputGroups:
				log.Info("Checking if all cross-project builds for {} are done yet", inputFile)
				if buildProject.toolchain.IsOutputActive(inputFile):
					log.Info("Extension {} is still active, can't build yet.", inputFile)
					return None
				for dep in buildProject.dependencies:
					if dep.toolchain.IsOutputActive(inputFile):
						log.Info("Extension {} is still active in dependent project, can't build yet.", inputFile)
						return None
				log.Info("{} is ok to build.", inputFile)
				fileList.update([x for x in buildProject.inputFiles.get(inputFile, []) if not x.WasToolUsed(tool)])
				for dep in buildProject.dependencies:
					fileList.update(dep.inputFiles.get(inputFile, []))
		else:
			for inputFile in tool.inputGroups:
				log.Info("Checking if all builds for {} are done yet", inputFile)
				if buildProject.toolchain.IsOutputActive(inputFile):
					log.Info("Extension {} is still active, can't build yet.", inputFile)
					return None
				log.Info("{} is ok to build.", inputFile)
				fileList.update([x for x in buildProject.inputFiles.get(inputFile, []) if not x.WasToolUsed(tool)])
		return fileList

def _checkDependenciesPreBuild(checkProject, tool, dependencies):
	with perf_timer.PerfTimer("Dependency checks"):
		log.Info("Checking if we can enqueue a new build for tool {} for project {}", checkProject, tool.__name__, checkProject)
		for dependency in dependencies:
			for checkTool in checkProject.toolchain.GetAllTools():
				if checkTool.inputFiles is None:
					extensionSet = checkTool.inputGroups | checkTool.crossProjectInputGroups
				else:
					extensionSet = checkTool.inputFiles | checkTool.inputGroups | checkTool.crossProjectInputGroups
				hasExtension = False
				for dependentExtension in extensionSet:
					if checkProject.inputFiles.get(dependentExtension):
						hasExtension = True
						break
				if hasExtension and checkProject.toolchain.CanCreateOutput(checkTool, dependency):
					return False
		return True

def _logThenRun(function, buildTool, buildToolchain, buildProject, inputFiles, doCompileCheck):
	"""
	:type buildProject: project.Project
	"""
	if inputFiles is not None:
		forceRebuild = False
		log.Info("Checking whether to recompile {} for tool {} with cross-project dependencies {}", inputFiles, buildTool.__name__, buildTool.crossProjectDependencies)
		for dep in buildTool.crossProjectDependencies:
			log.Info("Checking cross-project dependency '{}'", dep)
			for otherProj in buildProject.dependencies:
				log.Info("Checking up-stream project {}, which has built files of type {} this run", otherProj.name, otherProj.builtThisRun.keys())
				if dep in otherProj.builtThisRun:
					log.Info("Found a cross-project recompile trigger, recompiling")
					forceRebuild = True
					break
			if forceRebuild:
				break
		if not forceRebuild:
			if doCompileCheck:
				with perf_timer.PerfTimer("Recompile checks"):
					if isinstance(inputFiles, ordered_set.OrderedSet):
						extension = os.path.splitext(list(inputFiles)[0].filename)[1]
						fileList = inputFiles
					else:
						extension = os.path.splitext(inputFiles.filename)[1]
						fileList = ordered_set.OrderedSet([inputFiles])

					lastResult = buildProject.GetLastResult(inputFiles)
					if lastResult is not None \
							and not recompile.ShouldRecompile(buildProject, buildProject.toolchain.GetChecker(extension), fileList):
						log.Info("Previous result exists and input has not changed. Returning previous result.")
						return tuple(lastResult), True
			else:
				if isinstance(inputFiles, ordered_set.OrderedSet):
					fileList = inputFiles
				else:
					fileList = ordered_set.OrderedSet([inputFiles])

				lastResult = buildProject.GetLastResult(inputFiles)
				if lastResult is not None:
					filesNeedingBuild = [f for f in fileList if not f.upToDate]
					if not filesNeedingBuild:
						log.Info("Previous result exists and input has not changed. Returning previous result.")
						return tuple(lastResult), True


	with perf_timer.PerfTimer("Tool execution"):
		log.Info("Processing {} with {} for project {}", "null-input build" if inputFiles is None else inputFiles, buildTool.__name__, buildProject)

		with buildToolchain.Use(buildTool):
			return function(buildToolchain, buildProject, inputFiles), False

@TypeChecked(
	pool=thread_pool.ThreadPool,
	projectList=list,
	projectsWithCrossProjectDeps=list,
	buildProject=project.Project,
	toolUsed=(_classType, _typeType),
	inputExtension=(String, type(None)),
	inputFiles=(list, ordered_set.OrderedSet, type(None)),
	outputFiles=(String, tuple),
	upToDate=bool
)
def _buildFinished(pool, projectList, projectsWithCrossProjectDeps, buildProject, toolUsed, inputExtension, inputFiles, outputFiles, upToDate):
	"""
	Build has finished, enqueue another one.

	:param pool: thread pool
	:type pool: thread_pool.ThreadPool
	:param projectList: list of all projects
	:type projectList: list[project.Project]
	:param projectsWithCrossProjectDeps: List of projects that contain cross-project dependencies
	:type projectsWithCrossProjectDeps: list[project.Project]
	:param buildProject: project
	:type buildProject: project.Project
	:param toolUsed: tool used to build it
	:type toolUsed: type
	:param inputExtension: Extension taken as input
	:type inputExtension: str, bytes
	:param inputFiles: inputs used for this build
	:type inputFiles: list[input_file.InputFile]
	:param outputFiles: output generated by the build
	:type outputFiles: tuple, str, bytes
	:param upToDate: Whether or not the file was already up to date. If so, no build was actually performed.
	:type upToDate: bool
	"""
	with perf_timer.PerfTimer("Post-build processing"):
		toolUsed.curParallel -= 1
		global _runningBuilds
		_runningBuilds -= 1
		buildProject.toolchain.ReleaseReachability(toolUsed)

		with perf_timer.PerfTimer("Checking for tool completion"):
			if buildProject.toolchain.IsToolActive(toolUsed):
				done = True

				remainingInputs = [x for x in buildProject.inputFiles.get(inputExtension, []) if not x.WasToolUsed(toolUsed)]

				if not remainingInputs:
					# Technically this will happen before the tool is finished building, so we need the
					# above guard to keep from doing it twice and tossing up exceptions.
					# The important thing here is that this will stop us from doing a lot of logic further
					# down to see if we can build for tools that we know we can't build for.
					if toolUsed.inputFiles is not None:
						for inputFile in toolUsed.inputFiles:
							if buildProject.toolchain.IsOutputActive(inputFile):
								done = False
								break
					if done:
						for inputFile in toolUsed.inputGroups:
							if buildProject.toolchain.IsOutputActive(inputFile):
								done = False
								break
						if done:
							for inputFile in toolUsed.crossProjectInputGroups:
								if buildProject.toolchain.IsOutputActive(inputFile):
									done = False
									break
								if done:
									for dep in buildProject.dependencies:
										if dep.toolchain.IsOutputActive(inputFile):
											done = False
											break
										if not done:
											break
					if done:
						log.Info("Tool {} has finished building for project {}", toolUsed.__name__, buildProject)
						buildProject.toolchain.DeactivateTool(toolUsed)

		if not isinstance(outputFiles, tuple):
			outputFiles = (outputFiles, )

		extensionsToCheck = set()
		for outputFile in outputFiles:
			log.Info(
				"Checking for new tasks created by {}",
				os.path.basename(outputFile)
			)

			with perf_timer.PerfTimer("Processing new inputs"):
				buildProject.AddArtifact(inputFiles, outputFile)

				outputExtension = os.path.splitext(outputFile)[1]
				if not upToDate:
					buildProject.builtThisRun.setdefault(outputExtension, set()).add(outputFile)
				extensionsToCheck.add(outputExtension)

				if inputExtension == outputExtension:
					newInput = input_file.InputFile(outputFile, inputFiles, upToDate=upToDate)
				else:
					newInput = input_file.InputFile(outputFile, upToDate=upToDate)

				buildProject.inputFiles.setdefault(outputExtension, ordered_set.OrderedSet()).add(newInput)

				# Enqueue this file immediately in any tools that take it as a single input, unless they're marked to delay.
				toolList = buildProject.toolchain.GetToolsFor(outputExtension, newInput.toolsUsed)
				for tool in toolList:
					if not buildProject.toolchain.IsToolActive(tool):
						continue

					if not _canRun(tool):
						continue

					if not _dependenciesMet(buildProject, tool):
						continue

					if newInput.WasToolUsed(tool):
						continue

					_enqueueBuild(buildProject, tool, newInput, pool, projectList, projectsWithCrossProjectDeps, outputExtension)

		for outputExtension in extensionsToCheck:
			isActive = buildProject.toolchain.IsOutputActive(outputExtension)
			log.Info("Checking if {} is still active... {}", outputExtension if outputExtension else "<no extension>", "yes" if isActive else "no")

			# If this was the last file being built of its extension, check whether we can pass it and maybe others to relevant group input tools
			if not isActive:
				with perf_timer.PerfTimer("Checking for newly enabled tools"):
					toolList = buildProject.toolchain.GetActiveTools()
					for tool in toolList:
						if not _canRun(tool):
							continue

						if not _dependenciesMet(buildProject, tool):
							continue

						if tool.inputFiles is None:
							if not _canRun(tool):
								continue

							_enqueueBuild(buildProject, tool, None, pool, projectList, projectsWithCrossProjectDeps, None)
						else:
							for ext in tool.inputFiles:
								with perf_timer.PerfTimer("Enqueuing single-input builds"):
									for projectInput in [x for x in buildProject.inputFiles.get(ext, []) if not x.WasToolUsed(tool)]:
										if not _canRun(tool):
											break
										_enqueueBuild(buildProject, tool, projectInput, pool, projectList, projectsWithCrossProjectDeps, ext)

						if not tool.inputGroups and not tool.crossProjectInputGroups:
							continue

						# Check for group inputs that have been freed and queue up if all are free
						fileList = _getGroupInputFiles(buildProject, tool)

						if not fileList:
							continue

						_enqueueBuild(buildProject, tool, fileList, pool, projectList, projectsWithCrossProjectDeps, None)

					# Check to see if we've freed up any pending builds in other projects as well
					with perf_timer.PerfTimer("Cross-project dependency checks"):
						for proj in projectsWithCrossProjectDeps:
							toolList = proj.toolchain.GetActiveTools()
							for tool in toolList:
								if not _canRun(tool):
									continue


								if outputExtension not in tool.crossProjectDependencies and outputExtension not in tool.crossProjectInputGroups:
									continue

								if not _dependenciesMet(proj, tool):
									continue

								if tool.inputFiles is None:
									if not _canRun(tool):
										continue

									_enqueueBuild(proj, tool, None, pool, projectList, projectsWithCrossProjectDeps, None)
								else:
									for ext in tool.inputFiles:
										with perf_timer.PerfTimer("Enqueuing single-input builds"):
											for projectInput in [x for x in proj.inputFiles.get(ext, []) if not x.WasToolUsed(tool)]:
												if not _canRun(tool):
													break
												_enqueueBuild(proj, tool, projectInput, pool, projectList, projectsWithCrossProjectDeps, ext)

								if not tool.inputGroups and not tool.crossProjectInputGroups:
									continue

								fileList = _getGroupInputFiles(proj, tool)

								if not fileList:
									continue

								_enqueueBuild(proj, tool, fileList, pool, projectList, projectsWithCrossProjectDeps, None)

		shared_globals.completedBuilds += 1

		if upToDate:
			logFn = log.Info
		else:
			logFn = log.Build
		mainFileDir = os.path.dirname(sys.modules["__main__"].__file__)
		logFn(
			"Finished building {} => {}",
			"null-input for {} for project {}".format(toolUsed.__name__, buildProject) if inputFiles is None else inputFiles,
			[os.path.relpath(PlatformString(outputFile), mainFileDir).replace("\\", "/") for outputFile in outputFiles]
				if isinstance(outputFiles, tuple) else os.path.relpath(outputFiles, mainFileDir).replace("\\", "/")
		)
		if shared_globals.verbosity > shared_globals.Verbosity.Verbose:
			log.UpdateProgressBar()

		if _runningBuilds == 0:
			# We have no builds running and finishing this build did not spawn a new one
			# Time to exit.
			pool.Stop()


@TypeChecked(numThreads=int, projectBuildList=list, _return=int)
def _build(numThreads, projectBuildList):
	"""
	Run a build.

	:param numThreads: Number of threads
	:type numThreads: int
	:param projectBuildList: List of projects
	:type projectBuildList: list[project.Project]
	:return: Number of failures
	:rtype: int
	"""
	with perf_timer.PerfTimer("Enqueuing initial builds"):
		log.Build("Starting builds")
		buildStart = time.time()
		global _runningBuilds
		callbackQueue = queue.Queue()
		pool = thread_pool.ThreadPool(numThreads, callbackQueue)
		queuedSomething = False
		for buildProject in projectBuildList:
			for tool in buildProject.toolchain.GetAllTools():
				tool.curParallel = 0

		failures = 0
		pool.Start()

		projectsWithCrossProjectDeps = []

		for buildProject in projectBuildList:
			for tool in buildProject.toolchain.GetAllTools():
				if tool.crossProjectDependencies or tool.crossProjectInputGroups:
					projectsWithCrossProjectDeps.append(buildProject)
					break

		for buildProject in projectBuildList:
			for extension, fileList in [(None, None)] + list(buildProject.inputFiles.items()):
				log.Info("Enqueuing tasks for extension {}", extension)
				toolList = buildProject.toolchain.GetToolsFor(extension)
				for tool in toolList:
					try:
						# For the first pass, if ANY tool in the toolchain is capable of producing this output
						# anywhere in its path, AND any inputs exist for that tool, we won't queue up a build
						for dependProject in buildProject.dependencies:
							if not _checkDependenciesPreBuild(dependProject, tool, tool.crossProjectDependencies):
								raise MultiBreak

						if not _checkDependenciesPreBuild(buildProject, tool, tool.dependencies):
							raise MultiBreak

					except MultiBreak:
						continue

					if fileList is None and extension is None:
						if not _canRun(tool):
							continue

						if not buildProject.toolchain.IsToolActive(tool):
							continue

						_enqueueBuild(buildProject, tool, None, pool, projectBuildList, projectsWithCrossProjectDeps, None)
						queuedSomething = True
					else:
						log.Info("Looking at files {}", fileList)
						for inputFile in list(fileList): #Make a list out of this so it doesn't get a modified-during-iteration error
							if not _canRun(tool):
								break
							_enqueueBuild(buildProject, tool, inputFile, pool, projectBuildList, projectsWithCrossProjectDeps, extension, True)
							queuedSomething = True

			toolList = buildProject.toolchain.GetAllTools()
			log.Info("Checking for group inputs we can run already")
			for tool in toolList:
				if not tool.inputGroups and not tool.crossProjectInputGroups:
					continue

				if not _canRun(tool):
					continue

				try:
					for dependProject in buildProject.dependencies:
						if not _checkDependenciesPreBuild(dependProject, tool, tool.crossProjectDependencies):
							raise MultiBreak()

					if not _checkDependenciesPreBuild(buildProject, tool, tool.dependencies):
						raise MultiBreak()

				except MultiBreak:
					continue

				fileList = _getGroupInputFiles(buildProject, tool)

				if not fileList:
					break

				_enqueueBuild(buildProject, tool, fileList, pool, projectBuildList, projectsWithCrossProjectDeps, None, True)
				queuedSomething = True

	if not queuedSomething:
		log.Build("Nothing to build.")
		pool.Stop()
		return 0

	with perf_timer.PerfTimer("Running builds"):
		while True:
			with perf_timer.PerfTimer("Main thread idle"):
				callback = callbackQueue.GetBlocking()

			if callback is thread_pool.ThreadPool.exitEvent:
				break

			toReraise = None
			try:
				callback()
			except thread_pool.ThreadedTaskException as e:
				_runningBuilds -= 1
				if _runningBuilds == 0:
					# We have no builds running and finishing this build did not spawn a new one
					# Time to exit.
					pool.Stop()
				failures += 1
				toReraise = e
			except:
				pool.Abort()
				raise

			if toReraise is not None:
				try:
					toReraise.Reraise()
				except csbuild.BuildFailureException as buildExc:
					log.Error(repr(buildExc))
				except:
					pool.Abort()
					raise

	for buildProject in projectBuildList:
		if buildProject.toolchain.HasAnyReachability():
			log.Error("Project {} did not finish building.", buildProject)
			failures += 1

	log.Build("Build finished. Completed {} tasks in {}", shared_globals.totalBuilds, FormatTime(time.time() - buildStart))
	return failures

@TypeChecked(projectCleanList=list, keepArtifactsAndDirectories=bool)
def _clean(projectCleanList, keepArtifactsAndDirectories):
	"""
	Clean the files built in previous builds.

	:param projectCleanList: List of projects
	:type projectCleanList: list[project.Project]
	:param keepArtifactsAndDirectories: If true, clean will not close the artifacts file and will not delete directories
	:type keepArtifactsAndDirectories: bool
	"""
	with perf_timer.PerfTimer("Cleaning build artifacts"):
		log.Build("Cleaning...")
		def _rmDirIfPossible(dirname):
			with perf_timer.PerfTimer("Removing directories (if possible)"):
				if os.access(dirname, os.F_OK):
					containsOnlyDirs = True
					for _, _, files in os.walk(dirname):
						if files:
							containsOnlyDirs = False
							break
					if containsOnlyDirs:
						log.Build("Removing {}", dirname)
						#If it contains only directories and no files, remove everything
						shutil.rmtree(dirname)
						#Then if its parent directory is empty, remove it and any dirs above it that are also empty
						parentDir = os.path.dirname(dirname)
						if not os.listdir(parentDir):
							os.removedirs(parentDir)

		for cleanProject in projectCleanList:
			log.Info("Cleaning project {}", cleanProject)
			with perf_timer.PerfTimer("Removing artifacts"):
				for artifacts in cleanProject.lastRunArtifacts.values():
					for artifact in artifacts:
						if os.access(artifact, os.F_OK):
							log.Info("Removing {}", artifact)
							os.remove(artifact)
				cleanProject.lastRunArtifacts = collections.OrderedDict()

			if not keepArtifactsAndDirectories:
				_rmDirIfPossible(cleanProject.csbuildDir)
				_rmDirIfPossible(cleanProject.intermediateDir)
				_rmDirIfPossible(cleanProject.outputDir)


def _execfile(filename, glob, loc):
	with perf_timer.PerfTimer("Parsing Makefiles"):
		with open(filename, "r") as f:
			glob["__file__"] = filename
			# pylint: disable=exec-used
			exec(compile(f.read(), filename, "exec"), glob, loc)

def _setupDefaultTargets():
	if csbuild.addDefaultTargets:
		from ..tools.common.tool_traits import HasOptimizationLevel
		OptimizationLevel = HasOptimizationLevel.OptimizationLevel
		from ..tools.common.tool_traits import HasDebugLevel
		DebugLevel = HasDebugLevel.DebugLevel
		#Create the default targets...
		oldPlan = csbuild.currentPlan
		for plan in project_plan.allPlans:
			log.Info("Setting up default targets for {}", plan)
			csbuild.currentPlan = project_plan.allPlans[plan]
			with csbuild.Target("release"):
				log.Info("Setting up target 'release'")
				try:
					csbuild.SetOptimizationLevelIfUnset(OptimizationLevel.Max)
				except AttributeError:
					# ignore toolchains that don't support an optimization level
					pass
				try:
					csbuild.SetDebugLevelIfUnset(DebugLevel.Disabled)
				except AttributeError:
					# ignore toolchains that don't support a debug level
					pass
				try:
					csbuild.SetDebugRuntimeIfUnset(False)
				except AttributeError:
					# ignore toolchains that don't support a debug runtime
					pass
				csbuild.AddDefines("NDEBUG")

			with csbuild.Target("debug"):
				log.Info("Setting up target 'debug'")
				try:
					csbuild.SetOptimizationLevelIfUnset(OptimizationLevel.Disabled)
				except AttributeError:
					# ignore toolchains that don't support an optimization level
					pass
				try:
					csbuild.SetDebugLevelIfUnset(DebugLevel.EmbeddedSymbols)
				except AttributeError:
					# ignore toolchains that don't support a debug level
					pass
				try:
					csbuild.SetDebugRuntimeIfUnset(True)
				except AttributeError:
					# ignore toolchains that don't support a debug runtime
					pass
				csbuild.AddDefines("_DEBUG")

			with csbuild.Target("fastdebug"):
				log.Info("Setting up target 'fastdebug'")
				try:
					csbuild.SetOptimizationLevelIfUnset(OptimizationLevel.Max)
				except AttributeError:
					# ignore toolchains that don't support an optimization level
					pass
				try:
					csbuild.SetDebugLevelIfUnset(DebugLevel.EmbeddedSymbols)
				except AttributeError:
					# ignore toolchains that don't support a debug level
					pass
				try:
					csbuild.SetDebugRuntimeIfUnset(False)
				except AttributeError:
					# ignore toolchains that don't support a debug runtime
					pass
				csbuild.AddDefines("_DEBUG")
				csbuild.AddDefines("_FASTDEBUG")
			log.Info("{}", csbuild.currentPlan.knownTargets)
		csbuild.currentPlan = oldPlan

def Run():
	"""
	Run the build! This is the main entry point for csbuild.
	"""
	shared_globals.startTime = time.time()

	with perf_timer.PerfTimer("Argument Parsing"):
		mainFileDir = ""
		mainFile = sys.modules['__main__'].__file__
		scriptFiles = []
		makefileDict = {}

		tools.InitTools()

		if mainFile is not None:
			mainFileDir = os.path.abspath(os.path.dirname(mainFile))
			if mainFileDir:
				os.chdir(mainFileDir)
				mainFile = os.path.basename(os.path.abspath(mainFile))
			else:
				mainFileDir = os.path.abspath(os.getcwd())
			scriptFiles.append(os.path.join(mainFileDir, mainFile))
			if "-h" in sys.argv or "--help" in sys.argv:
				shared_globals.runMode = csbuild.RunMode.Help
				_execfile(mainFile, makefileDict, makefileDict)
				_setupDefaultTargets()
		else:
			log.Error("csbuild cannot be run from the interactive console.")
			system.Exit(1)

		epilog = "    ------------------------------------------------------------    \n\nProjects available in this makefile (listed in build order):\n\n"

		projtable = [[]]
		i = 1
		j = 0

		maxcols = 4#min(math.floor(len(shared_globals.sortedProjects) / 4), 4)

		for proj in shared_globals.sortedProjects:
			projtable[j].append(proj.name)
			if i < maxcols:
				i += 1
			else:
				projtable.append([])
				i = 1
				j += 1

		if projtable:
			maxlens = [15] * len(projtable[0])
			for col in projtable:
				for subindex, item in enumerate(col):
					maxlens[subindex] = max(maxlens[subindex], len(item))

			for col in projtable:
				for subindex, item in enumerate(col):
					epilog += "  "
					epilog += item
					for _ in range(maxlens[subindex] - len(item)):
						epilog += " "
					epilog += "  "
				epilog += "\n"

		epilog += "\nTargets available in this makefile:\n\n"

		targtable = [[]]
		i = 1
		j = 0

		maxcols = 4#min(math.floor(len(shared_globals.allTargets) / 4), 4)

		for targ in sorted(shared_globals.allTargets):
			if targ == csbuild.currentPlan.defaultTarget:
				targ += " (default)"
			targtable[j].append(targ)
			if i < maxcols:
				i += 1
			else:
				targtable.append([])
				i = 1
				j += 1

		if targtable:
			maxlens = [15] * len(targtable[0])
			for col in targtable:
				for subindex, item in enumerate(col):
					maxlens[subindex] = max(maxlens[subindex], len(item))

			for col in targtable:
				for subindex, item in enumerate(col):
					epilog += "  "
					epilog += item
					for _ in range(maxlens[subindex] - len(item)):
						epilog += " "
					epilog += "  "
				epilog += "\n"

		epilog += "\nAvailable solution generators:\n\n"

		gentable = [[]]
		i = 1
		j = 0

		maxcols = 4#min(math.floor(len(shared_globals.allGenerators) / 4), 4)

		for gen in sorted(shared_globals.allGenerators.keys()):
			gentable[j].append(gen)
			if i < maxcols:
				i += 1
			else:
				gentable.append([])
				i = 1
				j += 1

		if gentable:
			maxlens = [15] * len(gentable[0])
			for col in gentable:
				for subindex, item in enumerate(col):
					maxlens[subindex] = max(maxlens[subindex], len(item))

			for col in gentable:
				for subindex, item in enumerate(col):
					epilog += "  "
					epilog += item
					for _ in range(maxlens[subindex] - len(item)):
						epilog += " "
					epilog += "  "
				epilog += "\n"

		parser = shared_globals.parser = argparse.ArgumentParser(
			prog = mainFile, epilog = epilog, formatter_class = argparse.RawDescriptionHelpFormatter)

		parser.add_argument('--version', action = "store_true", help = "Print version information and exit")

		group = parser.add_mutually_exclusive_group()
		group.add_argument('-t', '--target', action='append', help = 'Target(s) for build. (May be specified multiple times.)', default=[])
		group.add_argument('--at', "--all-targets", action = "store_true", help = "Build all targets")

		parser.add_argument("-p", "--project",
							action="append", help = "Build only the specified project. (May be specified multiple times.)",)

		group = parser.add_mutually_exclusive_group()
		group.add_argument('-o', '--toolchain', help = "Toolchain(s) to use for compiling. (May be specified multiple times.)",
			default=[], action = "append")
		group.add_argument("--ao", '--all-toolchains', help="Build with all toolchains", action = "store_true")

		group = parser.add_mutually_exclusive_group()
		group.add_argument("-a", "--architecture", "--arch", help = 'Architecture(s) to compile for each toolchain. (May be specified multiple times.)', action = "append",)
		group.add_argument("--aa", "--all-architectures", "--all-arch", action = "store_true", help = "Build all architectures supported by this toolchain")

		group = parser.add_mutually_exclusive_group()
		group.add_argument('-c', '--clean', action = "store_true", help = 'Clean the target build')
		#group.add_argument('--install', action = "store_true", help = 'Install the target build')
		#group.add_argument('--install-headers', action = "store_true", help = 'Install only headers for the target build')
		#group.add_argument('--install-output', action = "store_true", help = 'Install only the output for the target build')
		group.add_argument('-r', '--rebuild', action = "store_true", help = 'Clean the target build and then build it')

		group2 = parser.add_mutually_exclusive_group()
		group2.add_argument('-v', '--verbose', action = "store_const", const = 0, dest = "verbosity",
			help = "Verbose. Enables additional INFO-level logging.", default = 1)
		group2.add_argument('-q', '--quiet', action = "store_const", const = 2, dest = "verbosity",
			help = "Quiet. Disables all logging except for WARN and ERROR.", default = 1)
		group2.add_argument('-qq', '--very-quiet', action = "store_const", const = 3, dest = "verbosity",
			help = "Very quiet. Disables all csb-specific logging.", default = 1)

		parser.add_argument("-j", "--jobs", action = "store", dest = "jobs", type = int, help = "Number of simultaneous build processes")

		#parser.add_argument("-g", "--gui", action = "store_true", dest = "gui", help = "Show GUI while building (experimental)")
		#parser.add_argument("--auto-close-gui", action = "store_true", help = "Automatically close the gui on build success (will stay open on failure)")
		#parser.add_argument("--profile", action="store_true", help="Collect detailed line-by-line profiling information on compile time. --gui option required to see this information.")

		parser.add_argument('--show-commands', help = "Show all commands sent to the system.", action = "store_true")
		parser.add_argument('--force-color', help = "Force color on or off.",
			action = "store", choices = ["on", "off"], default = None, const = "on", nargs = "?")
		parser.add_argument('--force-progress-bar', help = "Force progress bar on or off.",
			action = "store", choices = ["on", "off"], default = None, const = "on", nargs = "?")

		#parser.add_argument('--prefix', help = "install prefix (default /usr/local)", action = "store")
		#parser.add_argument('--libdir', help = "install location for libraries (default {prefix}/lib)", action = "store")
		#parser.add_argument('--incdir', help = "install prefix (default {prefix}/include)", action = "store")

		parser.add_argument("--stop-on-error", help = "Stop compilation after the first error is encountered.", action = "store_true")
		#parser.add_argument('--no-precompile', help = "Disable precompiling globally, affects all projects",
		#	action = "store_true")
		#parser.add_argument('--no-chunks', help = "Disable chunking globally, affects all projects",
		#	action = "store_true")

		parser.add_argument('--dg', '--dependency-graph', help="Generate dependency graph", action="store_true")
		parser.add_argument('--dg-stubs', '--dependency-graph-stubs', help="Generate dependency graph with stubs", action="store_true")
		parser.add_argument('--dg-type', '--dependency-graph-type', help="Graphviz engine to use for DG", action="store", default="dot", choices=["dot", "neato", "twopi", "circo", "fdp", "sfdp"])

		parser.add_argument('--clear-cache', help="Removes cached data such as header dependency caches and artifact metadata (note: will trigger a rebuild)", action="store_true")

		parser.add_argument("--perf-report", help="Collect and show perf report at the end of execution",
							action = "store", choices = ["tree", "flat", "html"], default = None, const = "tree", nargs = "?")

		#parser.add_argument("-d", "--define", help = "Add defines to each project being built.", action = "append")

		group = parser.add_argument_group("Solution generation", "Commands to generate a solution")
		group.add_argument('--generate-solution', help = "Generate a solution file for use with the given IDE.",
			action = "store")
		group.add_argument('--solution-path',
			help = "Path to output the solution file (default is ./Solutions/<solutiontype>)", action = "store",
			default = "")
		group.add_argument('--solution-name', help = "Name of solution output file (default is csbuild)", action = "store",
			default = "csbuild")
		group.add_argument('--solution-args', help = 'Arguments passed to the build script executed by the solution',
			action = "store", default = "")

		#TODO: Additional args here
		# for chain in _shared_globals.alltoolchains.items():
		# 	chainInst = chain[1]()
		# 	argfuncs = set()
		# 	for tool in chainInst.tools.values():
		# 		if(
		# 			hasattr(tool.__class__, "AdditionalArgs")
		# 			and tool.__class__.AdditionalArgs != toolchain.compilerBase.AdditionalArgs
		# 			and tool.__class__.AdditionalArgs != toolchain.linkerBase.AdditionalArgs
		# 		):
		# 			argfuncs.add(tool.__class__.AdditionalArgs)
		#
		# 	if argfuncs:
		# 		group = parser.add_argument_group("Options for toolchain {}".format(chain[0]))
		# 		for func in argfuncs:
		# 			func(group)
		#
		# for gen in _shared_globals.allgenerators.items():
		# 	if gen[1].AdditionalArgs != project_generator.project_generator.AdditionalArgs:
		# 		group = parser.add_argument_group("Options for solution generator {}".format(gen[0]))
		# 		gen[1].AdditionalArgs(group)
		#
		# if _options:
		# 	group = parser.add_argument_group("Local makefile options")
		# 	for option in _options:
		# 		group.add_argument(*option[0], **option[1])

		#args, remainder = parser.parse_known_args()
		#args.remainder = remainder
		#TODO: temporary, set runPerfReport to false so unknown flags don't trigger perf report to get printed
		#Once custom options are implemented this will not be needed and will go away.
		perf_timer.EnablePerfTracking(False)
		args = parser.parse_args()

		if args.version:
			shared_globals.runMode = csbuild.RunMode.Version

			print("CSBuild version {}".format(csbuild.__version__))
			print(csbuild.__copyright__)
			print("Code by {}".format(csbuild.__author__))
			print("Additional credits: {}\n".format(", ".join(csbuild.__credits__)))
			print("Maintainer: {} - {}".format(csbuild.__maintainer__, csbuild.__email__))
			return

		csbDir = os.path.join(mainFileDir, ".csbuild")
		shared_globals.settings = settings_manager.SettingsManager(os.path.join(csbDir, "settings"))

		if args.clear_cache:
			shared_globals.settings.Clear()
			args.rebuild = True

		shared_globals.verbosity = args.verbosity
		shared_globals.showCommands = args.show_commands
		if args.perf_report is not None:
			perf_timer.EnablePerfTracking(True)
			if args.perf_report == "tree":
				shared_globals.runPerfReport = perf_timer.ReportMode.TREE
			elif args.perf_report == "flat":
				shared_globals.runPerfReport = perf_timer.ReportMode.FLAT
			else:
				shared_globals.runPerfReport = perf_timer.ReportMode.HTML

		if args.force_color == "on":
			shared_globals.colorSupported = True
		elif args.force_color == "off":
			shared_globals.colorSupported = False
		else:
			shared_globals.colorSupported = terminfo.TermInfo.SupportsColor()

		if args.dg:
			shared_globals.runMode = csbuild.RunMode.GenerateDependencyGraph

		if args.generate_solution:

			shared_globals.runMode = csbuild.RunMode.GenerateSolution
			shared_globals.solutionGeneratorType = args.generate_solution

			if args.solution_path:
				shared_globals.solutionPath = args.solution_path
			else:
				shared_globals.solutionPath = "./Solutions/{}/".format(args.generate_solution)

			shared_globals.solutionPath = os.path.abspath(shared_globals.solutionPath)

			if not os.access(shared_globals.solutionPath, os.F_OK):
				os.makedirs(shared_globals.solutionPath)

			if args.solution_args:
				shared_globals.solutionArgs = args.solution_args

			if args.solution_name:
				solutionName = args.solution_name
			else:
				solutionName = "csbuild"

			@csbuild.OnBuildFinished
			def OnBuildFinished(projectList): # pylint: disable=unused-variable
				"""
				:param projectList: list of projects
				:type projectList: list[project.Project]
				"""
				solutionTool = shared_globals.allGenerators[args.generate_solution].solutionTool
				if not os.access(shared_globals.solutionPath, os.F_OK):
					os.makedirs(shared_globals.solutionPath)
				solutionTool.GenerateSolution(shared_globals.solutionPath, solutionName, projectList)

			for tool in shared_globals.allGeneratorTools:
				csbuild.Toolchain(*shared_globals.allToolchains).AddTool(tool)

		_execfile(mainFile, makefileDict, makefileDict)
		_setupDefaultTargets()

		if args.generate_solution:
			if args.generate_solution not in shared_globals.allGenerators:
				log.Error("No such solution generator: {}", args.generate_solution)
				system.Exit(1)

		if args.at:
			targetList = list(shared_globals.allTargets)
		elif args.target:
			targetList = args.target
		else:
			targetList = [project_plan.useDefault]

		if hasattr(args, "aa") and args.aa:
			archList = list(shared_globals.allArchitectures)
		elif hasattr(args, "architecture") and args.architecture:
			archList = args.architecture
		else:
			archList = [project_plan.useDefault]

		if args.ao:
			toolchainList = list(shared_globals.allToolchains)
		elif args.toolchain:
			toolchainList = args.toolchain
		else:
			toolchainList = [project_plan.useDefault]

		if not args.jobs:
			args.jobs = multiprocessing.cpu_count()

		if args.force_progress_bar == "on":
			shared_globals.columns = 80
		elif args.force_progress_bar == "off":
			shared_globals.columns = 0
		else:
			shared_globals.columns = terminfo.TermInfo.GetNumColumns( )
		shared_globals.clearBar = "\r" +  " " * shared_globals.columns + "\r"

	projectBuildList = []

	preparationStart = time.time()
	shared_globals.startTime = preparationStart

	if args.project:
		projectFilter = set(args.project)
		added = set()
		filteredProjects = dag.DAG(lambda x: x.name)
		for plan in reversed(list(shared_globals.sortedProjects)):
			if plan.name in projectFilter:
				if plan.name not in added:
					added.add(plan.name)
					depends = [dep.name if isinstance(dep, Dependency) else dep for dep in plan.depends]
					projectFilter.update(depends)
					filteredProjects.Add(plan, depends)
		shared_globals.sortedProjects = filteredProjects
		nonexistent = projectFilter - added
		if nonexistent:
			log.Error("No such project(s): {}", ", ".join(nonexistent))
			system.Exit(1)

	# Note:
	# The reason for this bit of code is that the import lock, in the way that CSBuild operates, prevents
	# us from being able to call subprocess.Popen() or any other process execution function other than os.popen().
	# csbuild is replacing the global import lock with its own lock to achieve the same functionality without the hang.
	# We then release the global import lock, but no one using csbuild should ever have to care about that, ever.

	class _importLocker(object):
		"""
		This replaces the global import lock with a new lock to get around a hang in subprocess.Popen() when the lock's held
		"""
		def __init__(self):
			self.lock = threading.RLock()
			self.loader = None

		#pylint: disable=invalid-name
		def find_module(self, fullname, path=None):
			"""
			Find the module loader, always returns self so the load_module will be called and the lock released
			:param fullname: name of module
			:type fullname: str
			:param path: path to look in
			:type path: str
			:return: self
			:rtype: _importBlocker
			"""
			self.lock.acquire()
			sys.meta_path.pop(0)
			self.loader = module_importer.find_module(fullname.rpartition(".")[2], path)
			sys.meta_path.insert(0, self)
			if self.loader is not None:
				return self
			self.lock.release()
			return None

		def load_module(self, name):
			"""
			Load the module from whatever loader we actually found to load it, then release the lock
			:param name: name of module
			:type name: str
			:return: the loaded module
			:rtype: module
			"""
			try:
				return module_importer.load_module(name, *self.loader)
			finally:
				self.lock.release()

	sys.meta_path.insert(0, _importLocker())

	failures = 0

	if module_importer.lock_held():
		module_importer.release_lock()
	log.StartLogThread()

	with perf_timer.PerfTimer("Project plan execution"):
		log.Build("Preparing build...")
		for toolchainName in toolchainList:
			log.Info("Collecting projects for toolchain {}", toolchainName)
			for archName in archList:
				log.Info("-- Architecture {}", archName)
				for targetName in targetList:
					log.Info("---- Target {}", targetName)
					for plan in shared_globals.sortedProjects:
						log.Info("------ Project {}", plan.name)
						proj = plan.ExecutePlan(toolchainName, archName, targetName)
						if proj is None:
							continue
						shared_globals.projectMap.setdefault(proj.toolchainName, {}) \
							.setdefault(proj.architectureName, {}) \
							.setdefault(proj.targetName, {})[plan.name] = proj
						if proj.projectType != csbuild.ProjectType.Stub or csbuild.GetRunMode() == csbuild.RunMode.GenerateSolution or args.dg:
							projectBuildList.append(proj)

	if not projectBuildList:
		log.Error("No projects were found supporting the requested architecture, toolchain, target, and platform combination")
		system.Exit(1)


	with perf_timer.PerfTimer("Dependency resolution"):
		for proj in projectBuildList:
			proj.ResolveDependencies()

	if args.dg:
		builder = 'digraph G {{\n\tlayout="{}";\n\toverlap="false";\n\tsplines="spline";\n\tratio=0.7;\n\trankdir="LR"\n'.format(args.dg_type)
		colors = [
			"#ff0000", "#cc5200", "#b2742d", "#858c23", "#20802d",
			"#00ffcc", "#39c3e6", "#205380", "#003380", "#38008c",
			"#ff40d9", "#e53967", "#f20000", "#7f4620", "#cca300",
			"#66ff00", "#00cc6d", "#36d9ce", "#007a99", "#0061f2",
			"#0000f2", "#cc00ff", "#d9368d", "#7f202d", "#991400",
			"#f28100", "#dae639", "#69bf30", "#269973", "#208079",
			"#00a2f2", "#397ee6", "#0000e6", "#8d29a6", "#990052"
		]
		idx = 0
		projectsInGraph = []
		for buildProj in projectBuildList:
			log.Info(buildProj.name)
			color = colors[idx]
			idx += 1
			if idx == len(colors):
				idx = 0

			if buildProj.projectType == csbuild.ProjectType.Application:
				shape = "doublecircle"
			elif buildProj.projectType == csbuild.ProjectType.Stub:
				if not args.dg_stubs:
					continue
				good = False
				for proj in projectBuildList:
					if buildProj in proj.dependencies:
						good = True
						break
				if not good:
					continue

				shape = "oval"
				color = "#000000"
			else:
				shape = "component"

			projectsInGraph.append(buildProj)

			builder += '\t{0} [shape="{1}" color="{2}" style="filled" fillcolor="{2}30"];\n'.format(buildProj.name.replace("-", "_"), shape, color)
			class _shared:
				topLevelDependencies = set(buildProj.dependencies)

			# pylint: disable=cell-var-from-loop
			def _recurseAndRemove(deps):
				for dep in deps:
					for nextDep in dep.dependencies:
						if nextDep in _shared.topLevelDependencies:
							_shared.topLevelDependencies.remove(nextDep)
					_recurseAndRemove(dep.dependencies)
			_recurseAndRemove(buildProj.dependencies)

			dist = 0
			for otherProj in _shared.topLevelDependencies:
				if otherProj.projectType == csbuild.ProjectType.Stub and not args.dg_stubs:
					continue
				builder += '\t{} -> {} [color="{}";];\n'.format(buildProj.name.replace("-", "_"), otherProj.name, color)
				dist += 1

		applications = [proj for proj in projectsInGraph if proj.projectType == csbuild.ProjectType.Application]
		builder += "\t{{ rank=same; {} }}\n".format("; ".join([proj.name.replace("-", "_") for proj in applications]))

		builder += "}"
		with open("depends.gv", "w") as f:
			f.write(builder)
		log.Build("Wrote depends.gv")
		try:
			# pylint: disable=import-error
			from graphviz import Digraph
		except:
			log.Warn("graphviz library not found. You can open depends.gv with graphviz or a similar dot viewer to view the graph, or install graphviz with pip install graphviz.")
		else:
			graph = Digraph(comment="CSBuild Dependency Graph", format="png", engine=args.dg_type, filename="depends")
			Digraph.source=property(lambda self: builder)
			graph.render("depends.gv", view=True)
			log.Build("Wrote depends.png")
		return

	if not args.clean or args.rebuild:
		with perf_timer.PerfTimer("Project setup"):
			#Now all dependencies have been resolved, so let toolchains do their post-resolution setup
			for proj in projectBuildList:
				for tool in proj.toolchain.GetAllTools():
					proj.toolchain.Tool(tool).SetupForProject(proj)

	shared_globals.projectBuildList = projectBuildList

	totaltime = time.time() - preparationStart
	log.Build("Build preparation took {}".format(FormatTime(totaltime)))

	if args.clean or args.rebuild:
		_clean(projectBuildList, args.rebuild)

	if not args.clean or args.rebuild:
		shared_globals.commandOutputThread = threading.Thread(target=commands.PrintStaggeredRealTimeOutput)
		shared_globals.commandOutputThread.start()

		log.Build("Executing build start hooks")
		for hook in shared_globals.buildStartedHooks:
			hook(projectBuildList)

		failures = _build(args.jobs, projectBuildList)

		log.Build("Executing build completion hooks")
		for hook in shared_globals.buildFinishedHooks:
			hook(projectBuildList)

	with perf_timer.PerfTimer("Waiting on logging to shut down"):
		log.StopLogThread()

	shared_globals.settings.Persist()

	totaltime = time.time() - preparationStart
	log.Build("Total execution took {}".format(FormatTime(totaltime)))
	system.Exit(failures)
