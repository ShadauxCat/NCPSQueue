#pragma once

#include <KoganPetrankQueueCHP.hpp>
#include "ConcurrencyFreaksBaseWrapper.hpp"
#include <thread>

#define HAS_KOGANPETRANK

template<typename t_ElementType>
class QueueWrapper<KoganPetrankQueueCHP<t_ElementType>> : public ConcurrencyFreaksBaseWrapper<KoganPetrankQueueCHP, t_ElementType>
{
};
