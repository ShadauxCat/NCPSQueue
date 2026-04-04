#pragma once

#include <LCRQueue.hpp>
#include "../QueueWrapper.hpp"
#include "ConcurrencyFreaksBaseWrapper.hpp"
#include <thread>

#define HAS_LCRQ

template<typename t_ElementType>
class QueueWrapper<LCRQueue<t_ElementType>> : public ConcurrencyFreaksBaseWrapper<LCRQueue, t_ElementType>
{
};
