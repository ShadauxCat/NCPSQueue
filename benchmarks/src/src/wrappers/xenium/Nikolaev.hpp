#pragma once

#include <xenium/nikolaev_bounded_queue.hpp>
#include <xenium/nikolaev_queue.hpp>
#include <xenium/reclamation/generic_epoch_based.hpp>
#include "../../QueueWrapper.hpp"
#include <thread>

#define HAS_NIKOLAEV

template<typename t_ElementType>
class QueueWrapper<xenium::nikolaev_bounded_queue<t_ElementType, xenium::policy::reclaimer<xenium::reclamation::epoch_based<>>, xenium::policy::entries_per_node<8192>>>
{
public:
	QueueWrapper()
		: m_queue(benchmarkConfig::numElements<t_ElementType>::value)
	{
	}

	void enqueue(size_t nElements, size_t offset, int tid)
	{
		for (size_t i = 0; i < nElements; ++i)
		{
			t_ElementType data = t_ElementType(offset + i);
			while (!m_queue.try_push(data)) {}
		}
	}
	void dequeue(size_t nElements, int tid)
	{
#ifdef VERIFY
		std::unordered_map<int, int> localValues;
#endif
		t_ElementType data = t_ElementType();
		for (size_t i = 0; i < nElements; ++i)
		{
			while (!m_queue.try_pop(data)) {};
#ifdef VERIFY
			localValues[data] += 1;
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
	void dequeueEmpty(size_t nElements, int tid)
	{
		t_ElementType data = t_ElementType();
		for (size_t i = 0; i < nElements; ++i)
		{
			auto _ = m_queue.try_pop(data);
		}
	}
private:
	xenium::nikolaev_bounded_queue<t_ElementType, xenium::policy::reclaimer<xenium::reclamation::epoch_based<>>, xenium::policy::entries_per_node<8192>> m_queue;
};

template<typename t_ElementType>
class QueueWrapper<xenium::nikolaev_queue<t_ElementType, xenium::policy::reclaimer<xenium::reclamation::epoch_based<>>, xenium::policy::entries_per_node<8192>>>
{
public:
	QueueWrapper()
		: m_queue()
	{
	}

	void enqueue(size_t nElements, size_t offset)
	{
		for (size_t i = 0; i < nElements; ++i)
		{
			t_ElementType data = t_ElementType(offset + i);
			m_queue.push(data);
		}
	}
	void dequeue(size_t nElements)
	{
#ifdef VERIFY
		std::unordered_map<int, int> localValues;
#endif
		t_ElementType data = t_ElementType();
		for (size_t i = 0; i < nElements; ++i)
		{
			while (!m_queue.try_pop(data)) {};
#ifdef VERIFY
			localValues[data] += 1;
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
	void dequeueEmpty(size_t nElements, int tid)
	{
		t_ElementType data = t_ElementType();
		for (size_t i = 0; i < nElements; ++i)
		{
			auto _ = m_queue.try_pop(data);
		}
	}
private:
	xenium::nikolaev_queue<t_ElementType, xenium::policy::reclaimer<xenium::reclamation::epoch_based<>>, xenium::policy::entries_per_node<8192>> m_queue;
};