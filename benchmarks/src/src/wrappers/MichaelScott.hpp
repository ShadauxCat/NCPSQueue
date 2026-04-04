#pragma once

#include <MichaelScottQueue.hpp>
#include "../QueueWrapper.hpp"
#include "ConcurrencyFreaksBaseWrapper.hpp"
#include <thread>

#define HAS_MICHAELSCOTTQUEUE

template<typename t_ElementType>
class QueueWrapper<MichaelScottQueue<t_ElementType>> : public ConcurrencyFreaksBaseWrapper<MichaelScottQueue, t_ElementType>
{
};
