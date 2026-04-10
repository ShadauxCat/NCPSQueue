#pragma once

#include <BitNextQueue.hpp>
#include <BitNextLazyHeadQueue.hpp>
#include "ConcurrencyFreaksBaseWrapper.hpp"
#include <thread>

#define HAS_BITNEXT

template<typename t_ElementType, PointerQueuePolicy t_PointerQueuePolicy>
class QueueWrapper<BitNextQueue<t_ElementType>, TicketType::NA, 0, t_PointerQueuePolicy> : public ConcurrencyFreaksBaseWrapper<BitNextQueue, t_ElementType, t_PointerQueuePolicy>
{
};

template<typename t_ElementType, PointerQueuePolicy t_PointerQueuePolicy>
class QueueWrapper<BitNextLazyHeadQueue<t_ElementType>, TicketType::NA, 0, t_PointerQueuePolicy> : public ConcurrencyFreaksBaseWrapper<BitNextLazyHeadQueue, t_ElementType, t_PointerQueuePolicy>
{
};