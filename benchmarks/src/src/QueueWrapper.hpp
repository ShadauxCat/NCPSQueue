#pragma once

// Brings in VERIFY macro to be used by all queue implementations
#include "config.hpp"

#if RUNMODE == MODE_VERIFY
#define VERIFY
std::unordered_map<int, int> values;
std::mutex valueLock;
#endif

enum class TicketType
{
	NA,
	NONE,
	PERSISTENT,
	EPHEMERAL,
	BATCH
};

enum class PointerQueuePolicy
{
	None,
	Preallocate,
	Dynamic
};

template<typename t_QueueType, TicketType t_TicketType = TicketType::NA, size_t t_BatchSize = 0, PointerQueuePolicy t_PointerQueuePolicy = PointerQueuePolicy::None>
class QueueWrapper;

#if defined(_WIN32)
#   define WIN32_LEAN_AND_MEAN
#	define NOMINMAX
#	include <Windows.h>
using ssize_t = SSIZE_T;
#endif