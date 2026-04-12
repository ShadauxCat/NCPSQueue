#!/usr/bin/env python3
#
# Copyright (c) 2023, Zoe J. Bare
#
# Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated
# documentation files (the "Software"), to deal in the Software without restriction, including without limitation
# the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software,
# and to permit persons to whom the Software is furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all copies or substantial portions
# of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED
# TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL
# THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF
# CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS
# IN THE SOFTWARE.
#

import os
import platform
import shutil
import subprocess
import sys

########################################################################################################################

_ROOT_PATH = os.path.abspath(os.path.dirname(__file__))
_IS_HOST_WSL = "microsoft" in platform.uname().release.lower()

########################################################################################################################

def _runCmd(cmd, failMsg):
	result = subprocess.call(cmd)
	assert \
		result == 0, \
		failMsg

########################################################################################################################

def _getEnvBinPath(envPath):
	pythonBinDirName = {
		"Windows": "Scripts"
	}.get(platform.system(), "bin")
	return os.path.join(envPath, pythonBinDirName)

########################################################################################################################
	
def _getPythonExeName():
	fileExtension = {
		"Windows": ".exe"
	}.get(platform.system(), "")
	return f"python{fileExtension}"

########################################################################################################################

def removeOldBuildEnv(buildPath):
	print("Removing old build environment ...")
	shutil.rmtree(buildPath, ignore_errors=True)

########################################################################################################################

def createVirtualEnv(buildPath):
	pythonExePath = os.path.join(_getEnvBinPath(buildPath), _getPythonExeName())

	print("Building Python virtual environment ...")

	# Create the virtual environment.
	cmd = [
		sys.executable,
		"-m", "venv",
		buildPath,
	]
	_runCmd(cmd, "Failed to create Python virtual environment")

	# Upgrade the core packages in the virtual environment.
	cmd = [
		pythonExePath,
		"-m", "pip",
		"install",
		"-U",
		"pip",
		"wheel",
		"setuptools",
	]
	_runCmd(cmd, "Failed to upgrade Python virtual environment core packages")

########################################################################################################################

def installDependencies(buildPath, externalPath):
	csbuildPath = os.path.join(externalPath, "csbuild")
	pythonExePath = os.path.join(_getEnvBinPath(buildPath), _getPythonExeName())

	# Install csbuild to the virtual environment.
	cmd = [
		pythonExePath,
		"-m", "pip",
		"install", "--use-pep517", "-e",
		csbuildPath,
	]
	_runCmd(cmd, "Failed to install 'csbuild' to Python virtual environment")

########################################################################################################################

def main(rootPath):
	externalPath = os.path.join(rootPath, "external")
	buildPath = os.path.join(rootPath, "_buildenv-wsl" if _IS_HOST_WSL else "_buildenv")
	activateScriptPath = os.path.join(_getEnvBinPath(buildPath), "activate")

	# Setup a local environment that we can use for building the project.
	removeOldBuildEnv(buildPath)
	createVirtualEnv(buildPath)
	installDependencies(buildPath, externalPath)
	
	print(f"\nRun script to activate: {activateScriptPath}")

########################################################################################################################

if __name__ == "__main__":
	main(_ROOT_PATH)
