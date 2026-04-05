#pragma once

#include "../../../../include/BEFAST/ConcurrentQueue.hpp"
#include "../QueueWrapper.hpp"

#define HAS_BEFAST_BOUNDED

template<typename t_ElementType, TicketType t_TicketType, size_t t_NumElements, bool t_EnableBatch>
class QueueWrapper<BEFAST::ConcurrentBoundedQueue<t_ElementType, t_NumElements, t_EnableBatch>, t_TicketType>
{
public:
	QueueWrapper()
		: m_queue(new BEFAST::ConcurrentBoundedQueue<t_ElementType, t_NumElements, t_EnableBatch>())
	{}

	~QueueWrapper()
	{
		delete m_queue;
	}

	void enqueue(size_t nElements, size_t offset)
	{
		BEFAST::BoundedWriteReservationTicket<t_ElementType> ticket;

		for (size_t i = 0; i < nElements; ++i)
		{
			t_ElementType data = t_ElementType(offset + i);
			m_queue->Enqueue(data, ticket);
		}
	}
	void enqueueMove(size_t nElements)
	{
		BEFAST::BoundedWriteReservationTicket<t_ElementType> ticket;

		for (size_t i = 0; i < nElements; ++i)
		{
			t_ElementType data = t_ElementType();
			m_queue->Enqueue(std::move(data), ticket);
		}
	}
	void dequeue(size_t nElements)
	{
#ifdef VERIFY
		std::unordered_map<int, int> localValues;
#endif
		BEFAST::BoundedReadReservationTicket<t_ElementType> ticket;

		t_ElementType data = t_ElementType();
		for (size_t i = 0; i < nElements; ++i)
		{
			while (!m_queue->Dequeue(data, ticket)) {};
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
		BEFAST::BoundedReadReservationTicket<t_ElementType> ticket;

		t_ElementType data = t_ElementType();
		for (size_t i = 0; i < nElements; ++i)
		{
			m_queue->Dequeue(data, ticket);
		}
	}
private:
	BEFAST::ConcurrentBoundedQueue<t_ElementType, t_NumElements, t_EnableBatch>* m_queue;
};


template<typename t_ElementType, size_t t_NumElements>
class QueueWrapper<BEFAST::ConcurrentBoundedQueue<t_ElementType, t_NumElements>, TicketType::NONE>
{
public:
	QueueWrapper()
		: m_queue(new BEFAST::ConcurrentBoundedQueue<t_ElementType, t_NumElements>(1024, 1024))
	{}

	~QueueWrapper()
	{
		delete m_queue;
	}

	void enqueue(size_t nElements, size_t offset)
	{
		for (size_t i = 0; i < nElements; ++i)
		{
			t_ElementType data = t_ElementType(offset + i);
			m_queue->Enqueue(data);
		}
	}
	void enqueueMove(size_t nElements)
	{
		for (size_t i = 0; i < nElements; ++i)
		{
			t_ElementType data = t_ElementType();
			m_queue->Enqueue(std::move(data));
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
			while (!m_queue->Dequeue(data)) {};
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
			m_queue->Dequeue(data);
		}
	}
private:
	BEFAST::ConcurrentBoundedQueue<t_ElementType, t_NumElements>* m_queue;
};

template<typename t_ElementType, size_t t_NumElements, size_t t_BatchSize>
class QueueWrapper<BEFAST::ConcurrentBoundedQueue<t_ElementType, t_NumElements, true>, TicketType::BATCH, t_BatchSize>
{
	std::atomic<int> totalRemaining{ 0 };
public:
	QueueWrapper()
		: m_queue(new BEFAST::ConcurrentBoundedQueue<t_ElementType, t_NumElements, true>(1024, 1024))
	{}

	~QueueWrapper()
	{
		delete m_queue;
	}

	void enqueue(size_t nElements, size_t offset)
	{
		typename BEFAST::ConcurrentBoundedQueue<t_ElementType, t_NumElements, true>::BatchEnqueueList batch = m_queue->CreateEnqueueList();
		ssize_t numWritten = 0;
		while (numWritten < nElements)
		{
			m_queue->EnqueueBatch(batch, std::min(ssize_t(t_BatchSize), (ssize_t)nElements - numWritten));
			while (batch.More())
			{
				t_ElementType data = t_ElementType(offset + numWritten);
				while (!batch.WriteNext(data))
				{

				}
				++numWritten;
			}
		}
	}

	void dequeue(size_t nElements)
	{
#ifdef VERIFY
		std::unordered_map<int, int> localValues;
#endif
		typename BEFAST::ConcurrentBoundedQueue<t_ElementType, t_NumElements, true>::BatchDequeueList batch = m_queue->CreateDequeueList();

		totalRemaining += nElements;
		while (totalRemaining.load() > 0)
		{
			m_queue->DequeueBatch(batch, t_BatchSize);
			while (batch.More())
			{
				t_ElementType data;
				while (!batch.Next(data))
				{
				}
#ifdef VERIFY
				localValues[data] += 1;
#endif
				--totalRemaining;
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
		typename BEFAST::ConcurrentBoundedQueue<t_ElementType, t_NumElements, true>::BatchDequeueList batch = m_queue->CreateDequeueList();

		for (size_t i = 0; i < nElements; ++i)
		{
			m_queue->DequeueBatch(batch, t_BatchSize);
		}
	}
private:
	BEFAST::ConcurrentBoundedQueue<t_ElementType, t_NumElements, true>* m_queue;
};