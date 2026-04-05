#pragma once

#include <array/LinearArrayQueue.hpp>
#include "ConcurrencyFreaksBaseWrapper.hpp"
#include <thread>

#define HAS_LINEARARRAYQUEUE

template<typename t_ElementType>
class QueueWrapper<LinearArrayQueue<t_ElementType>> : public ConcurrencyFreaksBaseWrapper<LinearArrayQueue, t_ElementType>
{
};
