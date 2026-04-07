#pragma once

#include <CRDoubleLinkQueue.hpp>
#include <CRTurnQueue.hpp>
#include "ConcurrencyFreaksBaseWrapper.hpp"
#include <thread>

#define HAS_CR

template<typename t_ElementType, PointerQueuePolicy t_PointerQueuePolicy>
class QueueWrapper<CRDoubleLinkQueue<t_ElementType>, TicketType::NONE, 0, t_PointerQueuePolicy> : public ConcurrencyFreaksBaseWrapper<CRDoubleLinkQueue, t_ElementType, t_PointerQueuePolicy>
{
};

template<typename t_ElementType, PointerQueuePolicy t_PointerQueuePolicy>
class QueueWrapper<CRTurnQueue<t_ElementType>, TicketType::NONE, 0, t_PointerQueuePolicy> : public ConcurrencyFreaksBaseWrapper<CRTurnQueue, t_ElementType, t_PointerQueuePolicy>
{
};