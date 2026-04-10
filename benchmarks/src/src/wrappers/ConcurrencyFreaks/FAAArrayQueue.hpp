#pragma once

#include <array/FAAArrayQueue.hpp>
#include "ConcurrencyFreaksBaseWrapper.hpp"
#include <thread>

#define HAS_FAAARRAYQUEUE

template<typename t_ElementType, PointerQueuePolicy t_PointerQueuePolicy>
class QueueWrapper<FAAArrayQueue<t_ElementType>, TicketType::NA, 0, t_PointerQueuePolicy> : public ConcurrencyFreaksBaseWrapper<FAAArrayQueue, t_ElementType, t_PointerQueuePolicy>
{
};
