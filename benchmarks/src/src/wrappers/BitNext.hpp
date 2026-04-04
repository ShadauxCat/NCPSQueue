#pragma once

#include <BitNextQueue.hpp>
#include <BitNextLazyHeadQueue.hpp>
#include "../QueueWrapper.hpp"
#include "ConcurrencyFreaksBaseWrapper.hpp"
#include <thread>

#define HAS_BITNEXT

template<typename t_ElementType>
class QueueWrapper<BitNextQueue<t_ElementType>> : public ConcurrencyFreaksBaseWrapper<BitNextQueue, t_ElementType>
{
};

template<typename t_ElementType>
class QueueWrapper<BitNextLazyHeadQueue<t_ElementType>> : public ConcurrencyFreaksBaseWrapper<BitNextLazyHeadQueue, t_ElementType>
{
};