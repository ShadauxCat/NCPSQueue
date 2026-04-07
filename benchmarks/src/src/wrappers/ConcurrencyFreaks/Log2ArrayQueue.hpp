#pragma once

#include <array/Log2ArrayQueue.hpp>
#include "ConcurrencyFreaksBaseWrapper.hpp"
#include <thread>

#define HAS_LOG2ARRAYQUEUE

template<typename t_ElementType, PointerQueuePolicy t_PointerQueuePolicy>
class QueueWrapper<Log2ArrayQueue<t_ElementType>, TicketType::NONE, 0, t_PointerQueuePolicy> : public ConcurrencyFreaksBaseWrapper<Log2ArrayQueue, t_ElementType, t_PointerQueuePolicy>
{
};
