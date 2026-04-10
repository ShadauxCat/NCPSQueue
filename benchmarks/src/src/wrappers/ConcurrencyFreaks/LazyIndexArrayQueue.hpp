#pragma once

#include <array/LazyIndexArrayQueue.hpp>
#include "ConcurrencyFreaksBaseWrapper.hpp"
#include <thread>

#define HAS_LAZYINDEXARRAYQUEUE

template<typename t_ElementType, PointerQueuePolicy t_PointerQueuePolicy>
class QueueWrapper<LazyIndexArrayQueue<t_ElementType>, TicketType::NA, 0, t_PointerQueuePolicy> : public ConcurrencyFreaksBaseWrapper<LazyIndexArrayQueue, t_ElementType, t_PointerQueuePolicy>
{
};
