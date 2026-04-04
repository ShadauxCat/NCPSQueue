#pragma once

// Brings in VERIFY macro to be used by all queue implementations
#include "config.hpp"

enum class TicketType
{
	NONE,
	PERSISTENT,
	EPHEMERAL,
	BATCH
};

template<typename t_QueueType, TicketType t_TicketType = TicketType::NONE, size_t BatchCount = 0>
class QueueWrapper;