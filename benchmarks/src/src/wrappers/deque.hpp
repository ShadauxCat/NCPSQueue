#pragma once

#include <deque>
#include <unordered_map>
#include "../QueueWrapper.hpp"

#define HAS_DEQUE

template<typename t_ElementType>
class QueueWrapper<std::deque<t_ElementType>>
{
public:
	void enqueue(size_t nElements, size_t offset, int tid)
	{
		for (size_t i = 0; i < nElements; ++i)
		{
			t_ElementType data = t_ElementType(offset + i);
			std::lock_guard<std::mutex> lock(m_mtx);
			m_queue.push_back(data);
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
	void dequeueEmpty(size_t nElements, int tid)
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

template<typename t_ElementType, size_t t_BatchSize>
class QueueWrapper<std::deque<t_ElementType>, TicketType::BATCH, t_BatchSize, PointerQueuePolicy::None>
{
public:
	void enqueue(size_t nElements, size_t offset, int tid)
	{
		for (size_t i = 0; i < nElements; i += t_BatchSize)
		{
			t_ElementType elements[t_BatchSize];
			for (size_t j = 0; j < t_BatchSize; ++j)
			{
				elements[j] = t_ElementType(offset + i * t_BatchSize + j);
			}
			std::lock_guard<std::mutex> lock(m_mtx);
			m_queue.insert(m_queue.end(), std::begin(elements), std::end(elements));
		}
	}
	void dequeue(size_t nElements, int tid)
	{
#ifdef VERIFY
		std::unordered_map<int, int> localValues;
#endif
		t_ElementType data = t_ElementType();
		size_t totalRemaining = nElements;
		std::vector<t_ElementType> poppedItems;
		poppedItems.reserve(t_BatchSize);
		while (totalRemaining > 0)
		{
			poppedItems.clear();
			{
				std::lock_guard<std::mutex> lock(m_mtx);
				poppedItems.insert(poppedItems.end(), m_queue.begin(), m_queue.begin() + std::min(t_BatchSize, std::min(totalRemaining, m_queue.size())));
				m_queue.erase(m_queue.begin(), m_queue.begin() + std::min(t_BatchSize, std::min(totalRemaining, m_queue.size())));
			}
			for (size_t j = 0; j < poppedItems.size(); ++j)
			{
				data = poppedItems[j];
				--totalRemaining;
#ifdef VERIFY
				localValues[data] += 1;
#endif
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