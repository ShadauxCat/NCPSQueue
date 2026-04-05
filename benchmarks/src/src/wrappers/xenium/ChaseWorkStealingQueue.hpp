#pragma once

#include <xenium/chase_work_stealing_deque.hpp>
#include <xenium/reclamation/generic_epoch_based.hpp>
#include "../../QueueWrapper.hpp"
#include <thread>

#define HAS_CHASEWORKSTEALINGDEQUE

template<typename t_ElementType>
class QueueWrapper<xenium::chase_work_stealing_deque<t_ElementType, xenium::policy::reclaimer<xenium::reclamation::epoch_based<>>, xenium::policy::entries_per_node<8192>>>
{
public:
	QueueWrapper()
		: m_queue()
	{
		m_ElementsStaticArray = new t_ElementType[NUM_ELEMENTS];
		for (size_t i = 0; i < NUM_ELEMENTS; ++i)
		{
			m_ElementsStaticArray[i] = t_ElementType(i);
		}
	}
	~QueueWrapper()
	{
		delete[] m_ElementsStaticArray;
	}

	void enqueue(size_t nElements, size_t offset)
	{
		for (size_t i = 0; i < nElements; ++i)
		{
			t_ElementType* data = &m_ElementsStaticArray[offset + i];
			while (!m_queue.try_push(data)) {}
		}
	}
	void dequeue(size_t nElements)
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
	void dequeueEmpty(size_t nElements)
	{
		t_ElementType* data = nullptr;
		for (size_t i = 0; i < nElements; ++i)
		{
			auto _ = m_queue.try_pop(data);
		}
	}
private:
	xenium::chase_work_stealing_deque<t_ElementType, xenium::policy::reclaimer<xenium::reclamation::epoch_based<>>, xenium::policy::entries_per_node<8192>> m_queue;

	// For the sake of fairness in comparing the algorithms, this is to avoid having dynamic memory allocation...
	t_ElementType* m_ElementsStaticArray;
};
