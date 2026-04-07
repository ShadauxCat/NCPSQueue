#pragma once

#include "../impl/1024Cores.hpp"
#include "../QueueWrapper.hpp"

#define HAS_1024CORES

template<typename t_ElementType>
class QueueWrapper<ext_1024cores::mpmc_bounded_queue<t_ElementType>>
{
public:
	QueueWrapper()
		: m_queue(pow(2, ceil(log(benchmarkConfig::numElements) / log(2))))
	{

	}

	void enqueue(size_t nElements, size_t offset, int tid)
	{
		for (size_t i = 0; i < nElements; ++i)
		{
			t_ElementType data = t_ElementType(offset + i);
			m_queue.enqueue(data);
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
			while (!m_queue.dequeue(data)) {};
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
			m_queue.dequeue(data);
		}
	}

private:
	ext_1024cores::mpmc_bounded_queue<t_ElementType> m_queue;
};