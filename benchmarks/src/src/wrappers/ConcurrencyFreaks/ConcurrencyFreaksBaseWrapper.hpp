#pragma once

#include "../../config.hpp"
#include "../../QueueWrapper.hpp"
#include <thread>
#include <atomic>

template<template<typename> typename t_QueueType, typename t_ElementType>
class ConcurrencyFreaksBaseWrapper
{
public:

	ConcurrencyFreaksBaseWrapper()
		: m_queue(std::thread::hardware_concurrency())
	{
		m_ElementsStaticArray = new t_ElementType[NUM_ELEMENTS];
		for (size_t i = 0; i < NUM_ELEMENTS; ++i)
		{
			m_ElementsStaticArray[i] = t_ElementType(i);
		}
	}

	~ConcurrencyFreaksBaseWrapper()
	{
		delete[] m_ElementsStaticArray;
	}

	void enqueue(size_t nElements, size_t offset)
	{
		int tid = m_tid.fetch_add(1);
		for (size_t i = 0; i < nElements; ++i)
		{
			t_ElementType* data = &m_ElementsStaticArray[offset + i];
			m_queue.enqueue(data, tid);
		}
	}
	void dequeue(size_t nElements)
	{
		int tid = m_tid.fetch_add(1);

#ifdef VERIFY
		std::unordered_map<int, int> localValues;
#endif
		t_ElementType* data;
		for (size_t i = 0; i < nElements; ++i)
		{
			while ((data = m_queue.dequeue(tid)) == nullptr) {};
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
		int tid = m_tid.fetch_add(1);
		t_ElementType* data;
		for (size_t i = 0; i < nElements; ++i)
		{
			data = m_queue.dequeue(tid);
		}
	}

private:
	t_QueueType<t_ElementType> m_queue;

	// For the sake of fairness in comparing the algorithms, this is to avoid having dynamic memory allocation...
	t_ElementType* m_ElementsStaticArray;
	std::atomic<int> m_tid{ 0 };
};