#pragma once

#define DO_VERIFICATION 0

constexpr size_t NUM_ELEMENTS = 1000000;

#if DO_VERIFICATION
constexpr int nIters = 1;
#else
constexpr int nIters = 25;
#endif

// Can't use constexpr here because hardware_concurrency() isn't constexpr
#define NCORES (std::thread::hardware_concurrency())
#define MIN_PRODUCERS 1
#define MIN_CONSUMERS 1
#define MAX_PRODUCERS NCORES
#define MAX_CONSUMERS NCORES

constexpr bool PIN_THREADS = true;

constexpr bool BENCHMARK_CHAR = true;
constexpr bool BENCHMARK_INT64 = true;
constexpr bool BENCHMARK_FIXEDSTRING64BYTES = true;

// Commenting out any of the below #include directives will disable the tests on it.


// std::deque + std::mutex
#include "wrappers/deque.hpp"
// 10204Cores
#include "wrappers/1024Cores.hpp"
// Boost
#include "wrappers/Boost.hpp"
// TBB
#include "wrappers/TBB.hpp"

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
// Crashes
//#include "wrappers/xenium/ChaseWorkStealingQueue.hpp"
#include "wrappers/xenium/Kirsch.hpp"
#include "wrappers/xenium/MichaelScott.hpp"
#include "wrappers/xenium/Nikolaev.hpp"
#include "wrappers/xenium/RamalheteQueue.hpp"
#include "wrappers/xenium/VyukovBoundedQueue.hpp"

// BEFAST
#include "wrappers/BEFAST_Unbounded.hpp"
#include "wrappers/BEFAST_Bounded.hpp"
