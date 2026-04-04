#pragma once

#include <array/FAAArrayQueue.hpp>
#include "../QueueWrapper.hpp"
#include "ConcurrencyFreaksBaseWrapper.hpp"
#include <thread>

#define HAS_FAAARRAYQUEUE

template<typename t_ElementType>
class QueueWrapper<FAAArrayQueue<t_ElementType>> : public ConcurrencyFreaksBaseWrapper<FAAArrayQueue, t_ElementType>
{
};
