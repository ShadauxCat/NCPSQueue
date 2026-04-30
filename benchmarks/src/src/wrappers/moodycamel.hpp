#pragma once
#include <concurrentqueue/concurrentqueue.h>


#include "../QueueWrapper.hpp"

#define HAS_MOODYCAMEL

template<typename t_ElementType, size_t t_Size>
struct MoodyCamelWithSize
{
};

template<typename t_ElementType, TicketType t_TicketType>
class QueueWrapper<moodycamel::ConcurrentQueue<t_ElementType>, t_TicketType>
{
public:
	QueueWrapper()
		: m_queue(benchmarkConfig::numElements<t_ElementType>::value)
	{
	}

	void enqueue(size_t nElements, size_t offset, int tid)
	{
		moodycamel::ProducerToken ptok(m_queue);

		for (size_t i = 0; i < nElements; ++i)
		{
			t_ElementType data = t_ElementType(offset + i);
			while (!m_queue.try_enqueue(ptok, data)) {};
		}
	}
	void dequeue(size_t nElements, int tid)
	{
#ifdef VERIFY
		std::unordered_map<int, int> localValues;
#endif
		moodycamel::ConsumerToken ctok(m_queue);

		t_ElementType data = t_ElementType();
		for (size_t i = 0; i < nElements; ++i)
		{
			while (!m_queue.try_dequeue(ctok, data)) {};
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
		moodycamel::ConsumerToken ctok(m_queue);

		t_ElementType data = t_ElementType();
		for (size_t i = 0; i < nElements; ++i)
		{
			m_queue.try_dequeue(ctok, data);
		}
	}
private:
	moodycamel::ConcurrentQueue<t_ElementType> m_queue;
};

template<typename t_ElementType, TicketType t_TicketType, size_t t_Size>
class QueueWrapper<MoodyCamelWithSize<t_ElementType, t_Size>, t_TicketType>
{
public:
	QueueWrapper()
		: m_queue(t_Size)
	{
	}

	void enqueue(size_t nElements, size_t offset, int tid)
	{
		moodycamel::ProducerToken ptok(m_queue);

		for (size_t i = 0; i < nElements; ++i)
		{
			t_ElementType data = t_ElementType(offset + i);
			while (!m_queue.enqueue(ptok, data)) {};
		}
	}
	void dequeue(size_t nElements, int tid)
	{
#ifdef VERIFY
		std::unordered_map<int, int> localValues;
#endif
		moodycamel::ConsumerToken ctok(m_queue);

		t_ElementType data = t_ElementType();
		for (size_t i = 0; i < nElements; ++i)
		{
			while (!m_queue.try_dequeue(ctok, data)) {};
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
		moodycamel::ConsumerToken ctok(m_queue);

		t_ElementType data = t_ElementType();
		for (size_t i = 0; i < nElements; ++i)
		{
			m_queue.try_dequeue(ctok, data);
		}
	}
private:
	moodycamel::ConcurrentQueue<t_ElementType> m_queue;
};

template<typename t_ElementType>
class QueueWrapper<moodycamel::ConcurrentQueue<t_ElementType>, TicketType::NONE>
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
			while (!m_queue.try_enqueue(data)) {};
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
			while (!m_queue.try_dequeue(data)) {};
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
			m_queue.try_dequeue(data);
		}
	}
private:
	moodycamel::ConcurrentQueue<t_ElementType> m_queue;
};

template<typename t_ElementType, size_t t_Size>
class QueueWrapper<MoodyCamelWithSize<t_ElementType, t_Size>, TicketType::NONE>
{
public:
	QueueWrapper()
		: m_queue(t_Size)
	{
	}

	void enqueue(size_t nElements, size_t offset, int tid)
	{
		for (size_t i = 0; i < nElements; ++i)
		{
			t_ElementType data = t_ElementType(offset + i);
			while (!m_queue.enqueue(data)) {};
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
			while (!m_queue.try_dequeue(data)) {};
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
			m_queue.try_dequeue(data);
		}
	}
private:
	moodycamel::ConcurrentQueue<t_ElementType> m_queue;
};

template<typename t_ElementType, size_t t_BatchSize, size_t t_Size>
class QueueWrapper<MoodyCamelWithSize<t_ElementType, t_Size>, TicketType::BATCH, t_BatchSize>
{
public:
	QueueWrapper()
		: m_queue(t_Size)
	{
	}

	void enqueue(size_t nElements, size_t offset, int tid)
	{
		ssize_t numWritten = 0;
		t_ElementType items[t_BatchSize];
		while (numWritten < nElements)
		{
			ssize_t thisBatchSize = std::min(ssize_t(t_BatchSize), (ssize_t)nElements - numWritten);
			for (ssize_t i = 0; i < thisBatchSize; ++i)
			{
				items[i] = t_ElementType(offset + numWritten);
			}
			m_queue.enqueue_bulk(items, thisBatchSize);
			numWritten += thisBatchSize;
		}
		}

	void dequeue(size_t nElements, int tid)
	{
#ifdef VERIFY
		std::unordered_map<int, int> localValues;
#endif
		size_t totalRemaining = nElements;
		t_ElementType items[t_BatchSize];
		while (totalRemaining > 0)
		{
			size_t count = m_queue.try_dequeue_bulk(items, std::min(t_BatchSize, totalRemaining));
#ifdef VERIFY
			for (size_t i = 0; i < count; ++i)
			{
				t_ElementType data = items[i];
				localValues[data] += 1;
			}
#endif
			totalRemaining -= count;
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
		t_ElementType items[t_BatchSize];
		for (size_t i = 0; i < nElements; ++i)
		{
			m_queue.try_dequeue_bulk(items, t_BatchSize);
		}
	}
private:
	moodycamel::ConcurrentQueue<t_ElementType> m_queue;
};

template<typename t_ElementType, size_t t_BatchSize>
class QueueWrapper<moodycamel::ConcurrentQueue<t_ElementType>, TicketType::BATCH, t_BatchSize>
{
public:
	QueueWrapper()
		: m_queue(benchmarkConfig::numElements<t_ElementType>::value)
	{}

	void enqueue(size_t nElements, size_t offset, int tid)
	{
		ssize_t numWritten = 0;
		t_ElementType items[t_BatchSize];
		while (numWritten < nElements)
		{
			ssize_t thisBatchSize = std::min(ssize_t(t_BatchSize), (ssize_t)nElements - numWritten);
			for (ssize_t i = 0; i < thisBatchSize; ++i)
			{
				items[i] = t_ElementType(offset + numWritten);
			}
			m_queue.enqueue_bulk(items, thisBatchSize);
			numWritten += thisBatchSize;
		}
	}

	void dequeue(size_t nElements, int tid)
	{
#ifdef VERIFY
		std::unordered_map<int, int> localValues;
#endif
		size_t totalRemaining = nElements;
		t_ElementType items[t_BatchSize];
		while (totalRemaining > 0)
		{
			size_t count = m_queue.try_dequeue_bulk(items, std::min(t_BatchSize, totalRemaining));
#ifdef VERIFY
			for(size_t i = 0; i < count; ++i)
			{
				t_ElementType data = items[i];
				localValues[data] += 1;
			}
#endif
			totalRemaining -= count;
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
		t_ElementType items[t_BatchSize];
		for (size_t i = 0; i < nElements; ++i)
		{
			m_queue.try_dequeue_bulk(items, t_BatchSize);
		}
	}
private:
	moodycamel::ConcurrentQueue<t_ElementType> m_queue;
};
