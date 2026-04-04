#pragma once

#include <tbb/concurrent_queue.h>
#include "../QueueWrapper.hpp"

#define HAS_TBB

template<typename t_ElementType>
class QueueWrapper<tbb::concurrent_bounded_queue<t_ElementType>>
{
public:
	QueueWrapper()
		: m_queue()
	{
		m_queue.set_capacity(NUM_ELEMENTS);
	}

	void enqueue(size_t nElements, size_t offset)
	{
		for (size_t i = 0; i < nElements; ++i)
		{
			t_ElementType data = t_ElementType(offset + i);
			m_queue.push(data);
		}
	}
	void enqueueMove(size_t nElements)
	{
		for (size_t i = 0; i < nElements; ++i)
		{
			t_ElementType data = t_ElementType();
			m_queue.push(std::move(data));
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
	void dequeueEmpty(size_t nElements)
	{
		t_ElementType data = t_ElementType();
		for (size_t i = 0; i < nElements; ++i)
		{
			m_queue.try_pop(data);
		}
	}
private:
	tbb::concurrent_bounded_queue<t_ElementType> m_queue;
};

template<typename t_ElementType>
class QueueWrapper<tbb::concurrent_queue<t_ElementType>>
{
public:
	void enqueue(size_t nElements, size_t offset)
	{
		for (size_t i = 0; i < nElements; ++i)
		{
			t_ElementType data = t_ElementType(offset + i);
			m_queue.push(data);
		}
	}
	void enqueueMove(size_t nElements)
	{
		for (size_t i = 0; i < nElements; ++i)
		{
			t_ElementType data = t_ElementType();
			m_queue.push(std::move(data));
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
	void dequeueEmpty(size_t nElements)
	{
		t_ElementType data = t_ElementType();
		for (size_t i = 0; i < nElements; ++i)
		{
			m_queue.try_pop(data);
		}
	}
private:
	tbb::concurrent_queue<t_ElementType> m_queue;
};