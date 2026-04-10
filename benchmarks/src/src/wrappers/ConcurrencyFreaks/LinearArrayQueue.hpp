#pragma once

#include <array/LinearArrayQueue.hpp>
#include "ConcurrencyFreaksBaseWrapper.hpp"
#include <thread>

#define HAS_LINEARARRAYQUEUE

template<typename t_ElementType, PointerQueuePolicy t_PointerQueuePolicy>
class QueueWrapper<LinearArrayQueue<t_ElementType>, TicketType::NA, 0, t_PointerQueuePolicy> : public ConcurrencyFreaksBaseWrapper<LinearArrayQueue, t_ElementType, t_PointerQueuePolicy>
{
};
