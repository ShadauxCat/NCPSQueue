#pragma once

#include <CRDoubleLinkQueue.hpp>
#include <CRTurnQueue.hpp>
#include "../QueueWrapper.hpp"
#include "ConcurrencyFreaksBaseWrapper.hpp"
#include <thread>

#define HAS_CR

template<typename t_ElementType>
class QueueWrapper<CRDoubleLinkQueue<t_ElementType>> : public ConcurrencyFreaksBaseWrapper<CRDoubleLinkQueue, t_ElementType>
{
};

template<typename t_ElementType>
class QueueWrapper<CRTurnQueue<t_ElementType>> : public ConcurrencyFreaksBaseWrapper<CRTurnQueue, t_ElementType>
{
};