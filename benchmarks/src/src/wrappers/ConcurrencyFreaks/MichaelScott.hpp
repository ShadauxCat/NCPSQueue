#pragma once

#include <MichaelScottQueue.hpp>
#include "ConcurrencyFreaksBaseWrapper.hpp"
#include <thread>

#define HAS_MICHAELSCOTTQUEUE

template<typename t_ElementType, PointerQueuePolicy t_PointerQueuePolicy>
class QueueWrapper<MichaelScottQueue<t_ElementType>, TicketType::NA, 0, t_PointerQueuePolicy> : public ConcurrencyFreaksBaseWrapper<MichaelScottQueue, t_ElementType, t_PointerQueuePolicy>
{
};
