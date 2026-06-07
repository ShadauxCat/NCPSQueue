#pragma once
#ifdef _WIN32
#	define NOMINMAX
#endif

#define MODE_BENCHMARK 0
#define MODE_VERIFY 1

#define RUNMODE MODE_BENCHMARK

// Quick config sets:
// Default values: qacFullSet = false, moodyCamelFullSet64k = false, symmetricThreadsOnly = false, QAC_AND_MOODYCAMEL_ONLY not defined
// char = true, int64 = true, FixedString64Bytes = true
// This is used to compute full matrix benchmarks.
#define CONFIG_FULLMATRIX 0
// Default values: qacFullSet = true, moodyCamelFullSet64k = true, symmetricThreadsOnly = true, QAC_AND_MOODYCAMEL_ONLY defined
// char = false, int64 = true, FixedString64Bytes = false
// This is used to compare the impacts of various different configurations.
#define CONFIG_SYMMETRICAL_COMPS 1

#define TEST_CONFIG CONFIG_SYMMETRICAL_COMPS

#include "util/FixedStaticString.hpp"

enum TestType
{
	Single = 0x1,
	Batch = 0x2,
	Both = Single | Batch
};

namespace benchmarkConfig
{
	template<typename t_ElementType>
	class numElements
	{
	public:
		static constexpr size_t valueSingle = 10000000;
		static constexpr size_t valueBatch = 25000000;
	};

	// More than this and the bounded queue creates a compile error for the static array being too large.
	template<>
	class numElements<FixedStaticString<64>>
	{
	public:
		static constexpr size_t valueSingle = 5000000;
		static constexpr size_t valueBatch = 10000000;
	};

#if RUNMODE == MODE_VERIFY
	static constexpr int nIters = 1;
	static constexpr bool qacFullSet = true;
	static constexpr bool moodyCamelFullSet = true;
#else
	static constexpr int nIters = 10;

#if TEST_CONFIG == CONFIG_SYMMETRICAL_COMPS
	static constexpr bool qacFullSet = true;
	static constexpr bool moodyCamelFullSet64k = true;
#else
	static constexpr bool qacFullSet = false;
	static constexpr bool moodyCamelFullSet64k = false;
#endif

	static constexpr bool moodyCamelFullSet = false;
#endif

	static constexpr bool pinThreads = false;

	static constexpr TestType testType = TestType::Both;

#if TEST_CONFIG == CONFIG_SYMMETRICAL_COMPS
	// If true, the test will only use MIN_PRODUCERS and MAX_PRODUCERS
	// MIN_CONSUMERS and MAX_CONSUMERS will be ignored
	static constexpr bool symmetricThreadsOnly = true;
#else
	static constexpr bool symmetricThreadsOnly = true;
#endif

}

// Can't use constexpr here because hardware_concurrency() isn't constexpr
#define NCORES (std::thread::hardware_concurrency())
#define MIN_PRODUCERS 1
#define MIN_CONSUMERS 1
#define MAX_PRODUCERS NCORES
#define MAX_CONSUMERS NCORES

namespace benchmarkTypes
{
#if TEST_CONFIG == CONFIG_SYMMETRICAL_COMPS
	constexpr bool Char = false;
	constexpr bool Int64 = true;
	constexpr bool FixedString64Bytes = false;
#else
	constexpr bool Char = true;
	constexpr bool Int64 = true;
	constexpr bool FixedString64Bytes = true;
#endif
}

namespace benchmarkTests
{
	constexpr bool EnqueueOnly = true;
	constexpr bool DequeueOnly = true;
	constexpr bool Concurrent = true;
	constexpr bool DequeueFromEmpty = true;
	constexpr bool LatencyPingPong = true;
}

//#define QAC_ONLY

#if TEST_CONFIG == CONFIG_SYMMETRICAL_COMPS
#define QAC_AND_MOODYCAMEL_ONLY
#endif

#ifndef QAC_ONLY
#ifndef QAC_AND_MOODYCAMEL_ONLY
// Commenting out any of the below #include directives will disable the tests on it.
// std::deque + std::mutex
#include "wrappers/deque.hpp"
// 1024Cores
#include "wrappers/1024Cores.hpp"
// TBB
#include "wrappers/TBB.hpp"

// The following queues don't work correctly on ARM.
#if !defined(__aarch64__) && !defined(_M_ARM64) && 0
// Queues from ConcurrencyFreaks

#include "wrappers/ConcurrencyFreaks/BitNext.hpp"
#include "wrappers/ConcurrencyFreaks/CR.hpp"
#include "wrappers/ConcurrencyFreaks/FAAArrayQueue.hpp"
#include "wrappers/ConcurrencyFreaks/KoganPetrank.hpp"
#include "wrappers/ConcurrencyFreaks/LazyIndexArrayQueue.hpp"

// LCRQ depends on embedded assembly and is written in a way that msvc can't process.
#if defined(__x86_64__) || defined(_M_X64)
#ifndef _WIN32
#include "wrappers/ConcurrencyFreaks/LCRQ.hpp"
#endif
#endif

#include "wrappers/ConcurrencyFreaks/LinearArrayQueue.hpp"
#include "wrappers/ConcurrencyFreaks/Log2ArrayQueue.hpp"
#include "wrappers/ConcurrencyFreaks/MichaelScott.hpp"

// Queues from Xenium
// Crashes even on x86
//#include "wrappers/xenium/ChaseWorkStealingQueue.hpp"
#include "wrappers/xenium/Kirsch.hpp"
#endif

// Excluded because it's incredibly slow and leaks memory.
//#include "wrappers/xenium/MichaelScott.hpp"
#include "wrappers/xenium/Nikolaev.hpp"
#include "wrappers/xenium/RamalheteQueue.hpp"
// Excluded because the 1024Cores queue above is the original canonical version of this algorithm.
//#include "wrappers/xenium/VyukovBoundedQueue.hpp"
#endif

// moodycamel
#include "wrappers/moodycamel.hpp"
#endif

// QAC
#include "wrappers/QAC_Unbounded.hpp"
#include "wrappers/QAC_Bounded.hpp"
