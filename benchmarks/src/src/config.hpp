#pragma once

//#define VERIFY

constexpr size_t NUM_ELEMENTS = 1000000;

#ifdef VERIFY
constexpr int nIters = 1;
#else
constexpr int nIters = 25;
#endif

#define NCORES (std::thread::hardware_concurrency()/2)
#define MIN_PRODUCERS NCORES
#define MIN_CONSUMERS NCORES
#define MAX_PRODUCERS NCORES
#define MAX_CONSUMERS NCORES

#define PIN_THREADS 1

#define BENCHMARK_CHAR 1
#define BENCHMARK_INT64 1
#define BENCHMARK_FIXEDSTRING64BYTES 1

// Included in config.h because this is the easiest way to change which queues are tested via configuration
#include "wrappers/1024Cores.hpp"
#include "wrappers/Boost.hpp"
#include "wrappers/deque.hpp"
#include "wrappers/TBB.hpp"
#include "wrappers/NCPS_Unbounded.hpp"
#include "wrappers/NCPS_Bounded.hpp"
#include "wrappers/BitNext.hpp"
#include "wrappers/CR.hpp"
#include "wrappers/FAAArrayQueue.hpp"
#include "wrappers/KoganPetrank.hpp"
#include "wrappers/LazyIndexArrayQueue.hpp"

// LCRQ depends on embedded assembly and is written in a way that msvc can't process.
#if defined(__x86_64__) || defined(_M_X64)
#ifndef _WIN32
#include "wrappers/LCRQ.hpp"
#endif
#endif

#include "wrappers/LinearArrayQueue.hpp"
#include "wrappers/Log2ArrayQueue.hpp"
#include "wrappers/MichaelScott.hpp"