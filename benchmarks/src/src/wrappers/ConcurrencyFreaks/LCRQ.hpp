#pragma once

#include <LCRQueue.hpp>
#include "ConcurrencyFreaksBaseWrapper.hpp"
#include <thread>

#define HAS_LCRQ

template<typename t_ElementType, PointerQueuePolicy t_PointerQueuePolicy>
class QueueWrapper<LCRQueue<t_ElementType>, TicketType::NA, 0, t_PointerQueuePolicy> : public ConcurrencyFreaksBaseWrapper<LCRQueue, t_ElementType, t_PointerQueuePolicy>
{
};
