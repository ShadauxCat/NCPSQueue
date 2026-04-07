#pragma once

#include <KoganPetrankQueueCHP.hpp>
#include "ConcurrencyFreaksBaseWrapper.hpp"
#include <thread>

#define HAS_KOGANPETRANK

template<typename t_ElementType, PointerQueuePolicy t_PointerQueuePolicy>
class QueueWrapper<KoganPetrankQueueCHP<t_ElementType>, TicketType::NONE, 0, t_PointerQueuePolicy> : public ConcurrencyFreaksBaseWrapper<KoganPetrankQueueCHP, t_ElementType, t_PointerQueuePolicy>
{
};
