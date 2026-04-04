#pragma once

#include <array/LazyIndexArrayQueue.hpp>
#include "../QueueWrapper.hpp"
#include "ConcurrencyFreaksBaseWrapper.hpp"
#include <thread>

#define HAS_LAZYINDEXARRAYQUEUE

template<typename t_ElementType>
class QueueWrapper<LazyIndexArrayQueue<t_ElementType>> : public ConcurrencyFreaksBaseWrapper<LazyIndexArrayQueue, t_ElementType>
{
};
