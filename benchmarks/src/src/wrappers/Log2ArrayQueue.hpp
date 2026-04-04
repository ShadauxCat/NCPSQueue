#pragma once

#include <array/Log2ArrayQueue.hpp>
#include "../QueueWrapper.hpp"
#include "ConcurrencyFreaksBaseWrapper.hpp"
#include <thread>

#define HAS_LOG2ARRAYQUEUE

template<typename t_ElementType>
class QueueWrapper<Log2ArrayQueue<t_ElementType>> : public ConcurrencyFreaksBaseWrapper<Log2ArrayQueue, t_ElementType>
{
};
