#pragma once

#include "../../../../include/QAC/ConcurrentQueue.hpp"
#include "../QueueWrapper.hpp"

#define HAS_QAC_BOUNDED

template<typename t_ElementType, TicketType t_TicketType, size_t t_NumElements, bool t_EnableBatch, bool t_EnableIdleSleep>
class QueueWrapper<QAC::ConcurrentBoundedQueue<t_ElementType, t_NumElements, t_EnableBatch, t_EnableIdleSleep>, t_TicketType>
{
public:
	QueueWrapper()
		: m_queue(new QAC::ConcurrentBoundedQueue<t_ElementType, t_NumElements, t_EnableBatch, t_EnableIdleSleep>())
	{}

	~QueueWrapper()
	{
		delete m_queue;
	}

	void enqueue(size_t nElements, size_t offset, int tid)
	{
		QAC::BoundedWriteReservationTicket<t_ElementType> ticket;

		for (size_t i = 0; i < nElements; ++i)
		{
			t_ElementType data = t_ElementType(offset + i);
			while (!m_queue->TryPush(data, ticket)) {};
		}
	}
	void dequeue(size_t nElements, int tid)
	{
#ifdef VERIFY
		std::unordered_map<int, int> localValues;
#endif
		QAC::BoundedReadReservationTicket<t_ElementType> ticket;

		t_ElementType data = t_ElementType();
		for (size_t i = 0; i < nElements; ++i)
		{
			while (!m_queue->TryPop(data, ticket)) {};
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
		QAC::BoundedReadReservationTicket<t_ElementType> ticket;

		t_ElementType data = t_ElementType();
		for (size_t i = 0; i < nElements; ++i)
		{
			m_queue->TryPop(data, ticket);
		}
	}
private:
	QAC::ConcurrentBoundedQueue<t_ElementType, t_NumElements, t_EnableBatch, t_EnableIdleSleep>* m_queue;
};

template<typename t_ElementType, size_t t_NumElements, bool t_EnableBatch, bool t_EnableIdleSleep>
class QueueWrapper<QAC::ConcurrentBoundedQueue<t_ElementType, t_NumElements, t_EnableBatch, t_EnableIdleSleep>, TicketType::NONE>
{
public:
	QueueWrapper()
		: m_queue(new QAC::ConcurrentBoundedQueue<t_ElementType, t_NumElements, t_EnableBatch, t_EnableIdleSleep>(std::thread::hardware_concurrency(), std::thread::hardware_concurrency()))
	{}

	~QueueWrapper()
	{
		delete m_queue;
	}

	void enqueue(size_t nElements, size_t offset, int tid)
	{
		for (size_t i = 0; i < nElements; ++i)
		{
			t_ElementType data = t_ElementType(offset + i);
			while (!m_queue->TryPush(data)) {};
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
			while (!m_queue->TryPop(data)) {};
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
			m_queue->TryPop(data);
		}
	}
private:
	QAC::ConcurrentBoundedQueue<t_ElementType, t_NumElements, t_EnableBatch, t_EnableIdleSleep>* m_queue;
};

template<typename t_ElementType, size_t t_NumElements, bool t_EnableBatch, bool t_EnableIdleSleep>
class QueueWrapper<QAC::ConcurrentBoundedQueue<t_ElementType, t_NumElements, t_EnableBatch, t_EnableIdleSleep>, TicketType::WAIT>
{
public:
	QueueWrapper()
		: m_queue(new QAC::ConcurrentBoundedQueue<t_ElementType, t_NumElements, t_EnableBatch, t_EnableIdleSleep>(std::thread::hardware_concurrency(), std::thread::hardware_concurrency()))
	{}

	~QueueWrapper()
	{
		delete m_queue;
	}

	void enqueue(size_t nElements, size_t offset, int tid)
	{
		for (size_t i = 0; i < nElements; ++i)
		{
			t_ElementType data = t_ElementType(offset + i);
			m_queue->PushWait(data);
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
			m_queue->PopWait(data);
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
		QAC::BoundedReadReservationTicket<t_ElementType> ticket;

		t_ElementType data = t_ElementType();
		for (size_t i = 0; i < nElements; ++i)
		{
			m_queue->TryPop(data, ticket);
		}
	}
private:
	QAC::ConcurrentBoundedQueue<t_ElementType, t_NumElements, t_EnableBatch, t_EnableIdleSleep>* m_queue;
};

template<typename t_ElementType, size_t t_NumElements, size_t t_BatchSize, bool t_EnableBatch, bool t_EnableIdleSleep>
class QueueWrapper<QAC::ConcurrentBoundedQueue<t_ElementType, t_NumElements, t_EnableBatch, t_EnableIdleSleep>, TicketType::BATCH, t_BatchSize>
{
public:
	QueueWrapper()
		: m_queue(new QAC::ConcurrentBoundedQueue<t_ElementType, t_NumElements, t_EnableBatch, t_EnableIdleSleep>(0, 0))
	{}

	~QueueWrapper()
	{
		delete m_queue;
	}

	void enqueue(size_t nElements, size_t offset, int tid)
	{
		typename QAC::ConcurrentBoundedQueue<t_ElementType, t_NumElements, t_EnableBatch, t_EnableIdleSleep>::BatchPushList batch = m_queue->CreatePushList();
		ssize_t numWritten = 0;
		while (numWritten < nElements)
		{
			m_queue->PushBatch(batch, std::min(ssize_t(t_BatchSize), (ssize_t)nElements - numWritten));
			while (batch.More())
			{
				t_ElementType data = t_ElementType(offset + numWritten);
				while (!batch.TryWriteNext(data))
				{

				}
				++numWritten;
			}
		}
	}

	void dequeue(size_t nElements, int tid)
	{
#ifdef VERIFY
		std::unordered_map<int, int> localValues;
#endif
		typename QAC::ConcurrentBoundedQueue<t_ElementType, t_NumElements, t_EnableBatch, t_EnableIdleSleep>::BatchPopList batch = m_queue->CreatePopList();

		size_t totalRemaining = nElements;
		while (totalRemaining > 0)
		{
			m_queue->PopBatch(batch, std::min(t_BatchSize, totalRemaining));
			while (batch.More())
			{
				t_ElementType data;
				while (!batch.TryReadNext(data))
				{
				}
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
		typename QAC::ConcurrentBoundedQueue<t_ElementType, t_NumElements, t_EnableBatch, t_EnableIdleSleep>::BatchPopList batch = m_queue->CreatePopList();

		for (size_t i = 0; i < nElements; ++i)
		{
			m_queue->PopBatch(batch, t_BatchSize);
		}
	}
private:
	QAC::ConcurrentBoundedQueue<t_ElementType, t_NumElements, t_EnableBatch, t_EnableIdleSleep>* m_queue;
};


template<typename t_ElementType, size_t t_NumElements, size_t t_BatchSize, bool t_EnableBatch, bool t_EnableIdleSleep>
class QueueWrapper<QAC::ConcurrentBoundedQueue<t_ElementType, t_NumElements, t_EnableBatch, t_EnableIdleSleep>, TicketType::BATCHWAIT, t_BatchSize>
{
public:
	QueueWrapper()
		: m_queue(new QAC::ConcurrentBoundedQueue<t_ElementType, t_NumElements, t_EnableBatch, t_EnableIdleSleep>(0, 0))
	{}

	~QueueWrapper()
	{
		delete m_queue;
	}

	void enqueue(size_t nElements, size_t offset, int tid)
	{
		typename QAC::ConcurrentBoundedQueue<t_ElementType, t_NumElements, t_EnableBatch, t_EnableIdleSleep>::BatchPushList batch = m_queue->CreatePushList();
		ssize_t numWritten = 0;
		while (numWritten < nElements)
		{
			m_queue->PushBatchWait(batch, std::min(ssize_t(t_BatchSize), (ssize_t)nElements - numWritten));
			while (batch.More())
			{
				t_ElementType data = t_ElementType(offset + numWritten);
				batch.WriteNextWait(data);
				++numWritten;
			}
		}
	}

	void dequeue(size_t nElements, int tid)
	{
#ifdef VERIFY
		std::unordered_map<int, int> localValues;
#endif
		typename QAC::ConcurrentBoundedQueue<t_ElementType, t_NumElements, t_EnableBatch, t_EnableIdleSleep>::BatchPopList batch = m_queue->CreatePopList();

		size_t totalRemaining = nElements;
		while (totalRemaining > 0)
		{
			m_queue->PopBatchWait(batch, std::min(t_BatchSize, totalRemaining));
			while (batch.More())
			{
				t_ElementType data;
				batch.ReadNextWait(data);
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
		typename QAC::ConcurrentBoundedQueue<t_ElementType, t_NumElements, t_EnableBatch, t_EnableIdleSleep>::BatchPopList batch = m_queue->CreatePopList();

		for (size_t i = 0; i < nElements; ++i)
		{
			m_queue->PopBatch(batch, t_BatchSize);
		}
	}
private:
	QAC::ConcurrentBoundedQueue<t_ElementType, t_NumElements, t_EnableBatch, t_EnableIdleSleep>* m_queue;
};