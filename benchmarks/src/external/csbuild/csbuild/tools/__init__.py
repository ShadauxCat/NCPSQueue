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
.. package:: tools
	:synopsis: Set of built-in tools that ship with csbuild

.. moduleauthor:: Jaedyn K. Draper
"""

from __future__ import unicode_literals, division, print_function

import csbuild
import platform

from .assemblers import AsmCompileChecker
from .cpp_compilers import CppCompileChecker

from .assemblers.android_clang_assembler import AndroidClangAssembler
from .assemblers.android_gcc_assembler import AndroidGccAssembler
from .assemblers.clang_assembler import ClangAssembler
from .assemblers.gcc_assembler import GccAssembler
from .assemblers.msvc_assembler import MsvcAssembler
from .assemblers.msvc_uwp_assembler import MsvcUwpAssembler
from .assemblers.ps3_assembler import Ps3Assembler
from .assemblers.ps4_assembler import Ps4Assembler
from .assemblers.ps5_assembler import Ps5Assembler
from .assemblers.psvita_assembler import PsVitaAssembler
from .assemblers.xbox_360_assembler import Xbox360Assembler

from .common.sony_tool_base import Ps3SpuConverter
from .common.xbox_360_tool_base import Xbox360ImageXexTool

from .cpp_compilers.android_clang_cpp_compiler import AndroidClangCppCompiler
from .cpp_compilers.android_gcc_cpp_compiler import AndroidGccCppCompiler
from .cpp_compilers.clang_cpp_compiler import ClangCppCompiler
from .cpp_compilers.gcc_cpp_compiler import GccCppCompiler
from .cpp_compilers.mac_os_clang_cpp_compiler import MacOsClangCppCompiler
from .cpp_compilers.msvc_cpp_compiler import MsvcCppCompiler
from .cpp_compilers.msvc_uwp_cpp_compiler import MsvcUwpCppCompiler
from .cpp_compilers.ps3_cpp_compiler import Ps3CppCompiler
from .cpp_compilers.ps4_cpp_compiler import Ps4CppCompiler
from .cpp_compilers.ps5_cpp_compiler import Ps5CppCompiler
from .cpp_compilers.psvita_cpp_compiler import PsVitaCppCompiler
from .cpp_compilers.xbox_360_cpp_compiler import Xbox360CppCompiler

from .java_archivers.oracle_java_archiver import OracleJavaArchiver

from .java_compilers.oracle_java_compiler import OracleJavaCompiler

from .linkers.android_clang_linker import AndroidClangLinker
from .linkers.android_gcc_linker import AndroidGccLinker
from .linkers.clang_linker import ClangLinker
from .linkers.gcc_linker import GccLinker
from .linkers.mac_os_clang_linker import MacOsClangLinker
from .linkers.msvc_linker import MsvcLinker
from .linkers.msvc_uwp_linker import  MsvcUwpLinker
from .linkers.ps3_linker import Ps3Linker
from .linkers.ps4_linker import Ps4Linker
from .linkers.ps5_linker import Ps5Linker
from .linkers.psvita_linker import PsVitaLinker
from .linkers.xbox_360_linker import Xbox360Linker

from .project_generators.visual_studio import (
	VsProjectGenerator,
	VsSolutionGenerator2010,
	VsSolutionGenerator2012,
	VsSolutionGenerator2013,
	VsSolutionGenerator2015,
	VsSolutionGenerator2017,
	VsSolutionGenerator2019,
	VsSolutionGenerator2022,
)

from ..toolchain import CompileChecker

def _createCheckers(inputMappings):
	checkers = {}

	for checkerObj, extensions in inputMappings.items():
		for ext in extensions:
			checkers[ext] = checkerObj

	return checkers

def InitTools():
	"""
	Initialize the built-in csbuild tools
	"""
	systemArchitecture = csbuild.GetSystemArchitecture()

	# Get either the platform-specific clang tools or the default clang tools.
	clangCompiler, clangLinker = {
		"Darwin": (MacOsClangCppCompiler, MacOsClangLinker),
	}.get(platform.system(), (ClangCppCompiler, ClangLinker))

	# Register C/C++ toolchains.
	for name, compiler, linker, assembler in [
		( "gcc", GccCppCompiler, GccLinker, GccAssembler ),
		( "clang", clangCompiler, clangLinker, ClangAssembler ),
		( "msvc", MsvcCppCompiler, MsvcLinker, MsvcAssembler ),
		( "msvc-uwp", MsvcUwpCppCompiler, MsvcUwpLinker, MsvcUwpAssembler ),
		( "mac-clang", MacOsClangCppCompiler, MacOsClangLinker, ClangAssembler ),
		( "android-gcc", AndroidGccCppCompiler, AndroidGccLinker, AndroidGccAssembler ),
		( "android-clang", AndroidClangCppCompiler, AndroidClangLinker, AndroidClangAssembler ),
	]:
		checkers = _createCheckers({
			CppCompileChecker(compiler): compiler.inputFiles,
			AsmCompileChecker(assembler): assembler.inputFiles,
		})

		csbuild.RegisterToolchain(name, systemArchitecture, compiler, linker, assembler, checkers=checkers)

	# Register Java toolchains.
	for name, compiler, archiver in [
		( "oracle-java", OracleJavaCompiler, OracleJavaArchiver ),
	]:
		checkers = _createCheckers({
			CompileChecker(): compiler.inputFiles,
		})

		csbuild.RegisterToolchain(name, systemArchitecture, compiler, archiver, checkers=checkers)

	ps3Checkers = _createCheckers({
		CppCompileChecker(Ps3CppCompiler): Ps3CppCompiler.inputFiles,
		AsmCompileChecker(Ps3Assembler): Ps3Assembler.inputFiles,
	})

	ps4Checkers = _createCheckers({
		CppCompileChecker(Ps4CppCompiler): Ps4CppCompiler.inputFiles,
		AsmCompileChecker(Ps4Assembler): Ps4Assembler.inputFiles,
	})

	ps5Checkers = _createCheckers({
		CppCompileChecker(Ps5CppCompiler): Ps5CppCompiler.inputFiles,
		AsmCompileChecker(Ps5Assembler): Ps5Assembler.inputFiles,
	})

	psVitaCheckers = _createCheckers({
		CppCompileChecker(PsVitaCppCompiler): PsVitaCppCompiler.inputFiles,
		AsmCompileChecker(PsVitaAssembler): PsVitaAssembler.inputFiles,
	})

	# Register the Sony platform toolchains.
	csbuild.RegisterToolchain("ps3", "cell", Ps3CppCompiler, Ps3Linker, Ps3Assembler, Ps3SpuConverter, checkers=ps3Checkers)
	csbuild.RegisterToolchain("ps4", "x64", Ps4CppCompiler, Ps4Linker, Ps4Assembler, checkers=ps4Checkers)
	csbuild.RegisterToolchain("ps5", "x64", Ps5CppCompiler, Ps5Linker, Ps5Assembler, checkers=ps5Checkers)
	csbuild.RegisterToolchain("psvita", "arm", PsVitaCppCompiler, PsVitaLinker, PsVitaAssembler, checkers=psVitaCheckers)

	xbox360Checkers = _createCheckers({
		CppCompileChecker(Xbox360CppCompiler): Xbox360CppCompiler.inputFiles,
		AsmCompileChecker(Xbox360Assembler): Xbox360Assembler.inputFiles,
	})

	# Register the Xbox platform toolchains.
	csbuild.RegisterToolchain("xbox360", "xcpu", Xbox360CppCompiler, Xbox360Linker, Xbox360Assembler, Xbox360ImageXexTool, checkers=xbox360Checkers)

	# Register toolchain groups.
	csbuild.RegisterToolchainGroup("msvc", "msvc", "msvc-uwp")
	csbuild.RegisterToolchainGroup("gnu", "gcc", "clang")
	csbuild.RegisterToolchainGroup("android", "android-gcc", "android-clang")
	csbuild.RegisterToolchainGroup("sony", "ps3", "ps4", "ps5", "psvita")

	# Register default project generators.
	csbuild.RegisterProjectGenerator("visual-studio-2010", [VsProjectGenerator], VsSolutionGenerator2010)
	csbuild.RegisterProjectGenerator("visual-studio-2012", [VsProjectGenerator], VsSolutionGenerator2012)
	csbuild.RegisterProjectGenerator("visual-studio-2013", [VsProjectGenerator], VsSolutionGenerator2013)
	csbuild.RegisterProjectGenerator("visual-studio-2015", [VsProjectGenerator], VsSolutionGenerator2015)
	csbuild.RegisterProjectGenerator("visual-studio-2017", [VsProjectGenerator], VsSolutionGenerator2017)
	csbuild.RegisterProjectGenerator("visual-studio-2019", [VsProjectGenerator], VsSolutionGenerator2019)
	csbuild.RegisterProjectGenerator("visual-studio-2022", [VsProjectGenerator], VsSolutionGenerator2022)
