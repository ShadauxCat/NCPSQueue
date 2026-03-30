## **Current test status:**

| **Platform** |                                                                                                                 **Status (develop)**                                                                                                                  |
|:-------------|:-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------:|
| Linux        |   [![TeamCity](https://dev.aegresco.com/teamcity/app/rest/builds/buildType:(id:Csbuild_LinuxPython3),branch:(develop)/statusIcon)](https://dev.aegresco.com/teamcity/viewType.html?buildTypeId=Csbuild_LinuxPython3&branch_Csbuild=develop&guest=1)   |
|              |                                                                                                                                                                                                                                                       |
| macOS        |   [![TeamCity](https://dev.aegresco.com/teamcity/app/rest/builds/buildType:(id:Csbuild_MacOSPython3),branch:(develop)/statusIcon)](https://dev.aegresco.com/teamcity/viewType.html?buildTypeId=Csbuild_MacOSPython3&branch_Csbuild=develop&guest=1)   |
|              |                                                                                                                                                                                                                                                       |
| Windows      | [![TeamCity](https://dev.aegresco.com/teamcity/app/rest/builds/buildType:(id:Csbuild_WindowsPython3),branch:(develop)/statusIcon)](https://dev.aegresco.com/teamcity/viewType.html?buildTypeId=Csbuild_WindowsPython3&branch_Csbuild=develop&guest=1) |

---

CSBuild is a language-agnostic build system focused on maximizing developer iteration time and providing tools for enabling developers to improve their build workflow. Currently, CSBuild is undergoing a complete rewrite to address some core architecture issues with the original iteration. It gets closer every day, but hasn't quite reached feature parity with the original CSBuild.

What it currently can do:
- Build basic C/C++, Java, Objective-C/C++, and Assembly files
- Build on Windows, macOS, BSD, Linux, Android, Xbox 360, PS3, PS4, PS5, and PSVita systems (language support varies by system)
- Be extended with tools to work in any language
- Support macro processing in all strings (i.e., `csbuild.SetOutputDirectory("{toolchainName}/{architectureName}/{targetName}")`)
- Generate project files for Visual Studio from version 2010 up to 2022.
- Dependency graph generation by running with --dg (requires the 'graphviz' Python package to be installed)
  
  <img src="doc_img/depends.gv.png" alt="Dependency Graph" style="zoom:50%;" />

What's still missing that exists in old CSBuild:
- "Chunking" - intelligently combining multiple translation units into one and breaking them back apart to improve build turn-around
- Solution generation for QtCreator
- Build GUI showing the progress of individual files and projects as they're build
- Build profiler to analyze and identify headers and lines of code that are expensive to compile

The core architecture is much more stable and maintainable than old CSBuild's, and tools are easier to implement than they were before. The new architecture also successfully decouples csbuild from the c++ language, allowing it to be truly versatile and language-agnostic. The new csbuild also cuts down considerably on wasted time during initial startup. Now that the majority of the core features have been implemented, we expect feature parity for the tools and target platforms supported by old CSBuild to start coming online very quickly, shortly followed by solution generation, chunking, and the gui tools.

Documentation hasn't been created for the new version of csbuild yet; however, we have created a large suite of tests, so in the short term, a lot of information can be gleaned from looking at the make.py file in each test.

Code for old csbuild, for those interested in it, can be found here: https://github.com/SleepingCatGames/csbuild

---

## Development Notes

Currently, the only dependency necessary for csbuild development is pylint, but that is only needed for running the pylint test.  However, while functional test support is maintained for both Python 2 and Python 3, the pylint test is no longer run for Python 2 because it is no longer supported by pylint and its own dependencies.