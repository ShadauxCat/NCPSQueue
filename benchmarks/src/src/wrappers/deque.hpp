#pragma once

#include <deque>
#include <unordered_map>
#include "../QueueWrapper.hpp"

#define HAS_DEQUE

template<typename t_ElementType>
class QueueWrapper<std::deque<t_ElementType>>
{
public:
	void enqueue(size_t nElements, size_t offset)
	{
		for (size_t i = 0; i < nElements; ++i)
		{
			t_ElementType data = t_ElementType(offset + i);
			std::lock_guard<std::mutex> lock(m_mtx);
			m_queue.push_back(data);
		}
	}
	void enqueueMove(size_t nElements)
	{
		for (size_t i = 0; i < nElements; ++i)
		{
			t_ElementType data = t_ElementType();
			std::lock_guard<std::mutex> lock(m_mtx);
			m_queue.push_back(std::move(data));
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
			for (;;)
			{
				std::lock_guard<std::mutex> lock(m_mtx);
				if (m_queue.empty())
				{
					continue;
				}
				data = m_queue.front();
				m_queue.pop_front();
#ifdef VERIFY
				localValues[data] += 1;
#endif
				break;
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
	void dequeueEmpty(size_t nElements)
	{
		t_ElementType data = t_ElementType();
		for (size_t i = 0; i < nElements; ++i)
		{
			std::lock_guard<std::mutex> lock(m_mtx);
			if (m_queue.empty())
			{
				continue;
			}
			data = m_queue.front();
			m_queue.pop_front();
		}
	}
private:
	std::mutex m_mtx;
	std::deque<t_ElementType> m_queue;
};