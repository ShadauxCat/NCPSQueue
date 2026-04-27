#pragma once

#include <xenium/ramalhete_queue.hpp>
#include <xenium/reclamation/generic_epoch_based.hpp>
#include "../../QueueWrapper.hpp"
#include <thread>

#define HAS_RAMALHETE

template<typename t_ElementType, PointerQueuePolicy t_PointerQueuePolicy>
class QueueWrapper<
	xenium::ramalhete_queue<t_ElementType*, xenium::policy::reclaimer<xenium::reclamation::epoch_based<>>, xenium::policy::entries_per_node<8192>>,
	TicketType::NA, 0, t_PointerQueuePolicy
>
{
public:
	QueueWrapper()
		: m_queue()
	{
		if constexpr (t_PointerQueuePolicy == PointerQueuePolicy::Preallocate)
		{
			m_ElementsStaticArray = new t_ElementType[benchmarkConfig::numElements<t_ElementType>::value];
			for (size_t i = 0; i < benchmarkConfig::numElements<t_ElementType>::value; ++i)
			{
				m_ElementsStaticArray[i] = t_ElementType(i);
			}
		}
	}
	~QueueWrapper()
	{
		if constexpr (t_PointerQueuePolicy == PointerQueuePolicy::Preallocate)
		{
			delete[] m_ElementsStaticArray;
		}
	}

	void enqueue(size_t nElements, size_t offset, int tid)
	{
		for (size_t i = 0; i < nElements; ++i)
		{
			t_ElementType* data;
			if constexpr (t_PointerQueuePolicy == PointerQueuePolicy::Preallocate)
			{
				data = &m_ElementsStaticArray[offset + i];
			}
			else
			{
				data = new t_ElementType(offset + i);
			}
			m_queue.push(data);
		}
	}
	void dequeue(size_t nElements, int tid)
	{
#ifdef VERIFY
		std::unordered_map<int, int> localValues;
#endif
		t_ElementType* data = nullptr;
		for (size_t i = 0; i < nElements; ++i)
		{
			while (!m_queue.try_pop(data)) {};
#ifdef VERIFY
			localValues[*data] += 1;
#endif
			if constexpr (t_PointerQueuePolicy == PointerQueuePolicy::Dynamic)
			{
				delete data;
			}
		}
#ifdef VERIFY
		{
			std::lock_guard<std::mutex> guard(valueLock);
			for (auto& kvp : localValues)
			{
				values[kvp.first] += kvp.second;
			}
		}
#endif
	}
	void dequeueEmpty(size_t nElements, int tid)
	{
		t_ElementType* data = nullptr;
		for (size_t i = 0; i < nElements; ++i)
		{
			auto _ = m_queue.try_pop(data);
		}
	}
private:
	xenium::ramalhete_queue<t_ElementType*, xenium::policy::reclaimer<xenium::reclamation::epoch_based<>>, xenium::policy::entries_per_node<8192>> m_queue;

	// For the sake of fairness in comparing the algorithms, this is to avoid having dynamic memory allocation...
	t_ElementType* m_ElementsStaticArray;
};
