#pragma once

#include "../../../../include/NCPS/ConcurrentQueue.hpp"
#include "../QueueWrapper.hpp"
#include <thread>

#define HAS_NCPS_UNBOUNDED

#if defined(_WIN32)
using ssize_t = SSIZE_T;
#endif

template<typename t_ElementType, ssize_t t_BlockSize, bool t_EnableBatch>
class QueueWrapper<NCPS::ConcurrentQueue<t_ElementType, t_BlockSize, t_EnableBatch>, TicketType::PERSISTENT>
{
public:
	void enqueue(size_t nElements, size_t offset)
	{
		for (size_t i = 0; i < nElements; ++i)
		{
			t_ElementType data = t_ElementType(offset + i);
			m_queue.Enqueue(data);
		}
	}
	void enqueueMove(size_t nElements)
	{
		for (size_t i = 0; i < nElements; ++i)
		{
			t_ElementType data = t_ElementType();
			m_queue.Enqueue(std::move(data));
		}
	}
	void dequeue(size_t nElements)
	{
#ifdef VERIFY
		std::unordered_map<int, int> localValues;
#endif
		typename NCPS::ConcurrentQueue<t_ElementType, t_BlockSize, t_EnableBatch>::ReadReservationTicket ticket;
		m_queue.InitializeReservationTicket(ticket);

		t_ElementType data = t_ElementType();
		for (size_t i = 0; i < nElements; ++i)
		{
			while (!m_queue.Dequeue(data, ticket)) {}
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
		typename NCPS::ConcurrentQueue<t_ElementType, t_BlockSize, t_EnableBatch>::ReadReservationTicket ticket;
		m_queue.InitializeReservationTicket(ticket);

		t_ElementType data = t_ElementType();
		for (size_t i = 0; i < nElements; ++i)
		{
			m_queue.Dequeue(data, ticket);
		}
	}
private:
	NCPS::ConcurrentQueue<t_ElementType, t_BlockSize, t_EnableBatch> m_queue;
};

template<typename t_ElementType, ssize_t t_BlockSize, bool t_EnableBatch, size_t t_BatchSize>
class QueueWrapper<NCPS::ConcurrentQueue<t_ElementType, t_BlockSize, t_EnableBatch>, TicketType::BATCH, t_BatchSize>
{
	std::atomic<int> totalRemaining{ 0 };
public:
	void enqueue(size_t nElements, size_t offset)
	{
		size_t remaining = nElements;
		while (remaining > 0)
		{
			size_t batchSize = remaining < t_BatchSize ? remaining : t_BatchSize;
			t_ElementType data[t_BatchSize];
			for (size_t j = 0; j < batchSize; ++j)
			{
				data[j] = t_ElementType(offset + (nElements - remaining) + j);
			}
			m_queue.EnqueueBatch(data, batchSize);
			remaining -= batchSize;
		}
	}
	void dequeue(size_t nElements)
	{
#ifdef VERIFY
		std::unordered_map<int, int> localValues;
#endif
		typename NCPS::ConcurrentQueue<t_ElementType, t_BlockSize, t_EnableBatch>::BatchDequeueList batch = m_queue.CreateDequeueList();

		totalRemaining += nElements;
		while (totalRemaining.load() > 0)
		{
			m_queue.DequeueBatch(batch, t_BatchSize);
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
		typename NCPS::ConcurrentQueue<t_ElementType, t_BlockSize, t_EnableBatch>::BatchDequeueList batch = m_queue.CreateDequeueList();

		for (size_t i = 0; i < nElements; ++i)
		{
			m_queue.DequeueBatch(batch, t_BatchSize);
		}
	}
private:
	NCPS::ConcurrentQueue<t_ElementType, t_BlockSize, t_EnableBatch> m_queue;
};

template<typename t_ElementType, ssize_t t_BlockSize, bool t_EnableBatch>
class QueueWrapper<NCPS::ConcurrentQueue<t_ElementType, t_BlockSize, t_EnableBatch>, TicketType::EPHEMERAL>
{
public:
	void enqueue(size_t nElements, size_t offset)
	{
		for (size_t i = 0; i < nElements; ++i)
		{
			t_ElementType data = t_ElementType(offset + i);
			m_queue.Enqueue(data);
		}
	}
	void enqueueMove(size_t nElements)
	{
		for (size_t i = 0; i < nElements; ++i)
		{
			t_ElementType data = t_ElementType();
			m_queue.Enqueue(std::move(data));
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
			typename NCPS::ConcurrentQueue<t_ElementType, t_BlockSize, t_EnableBatch>::ReadReservationTicket ticket;
			m_queue.InitializeReservationTicket(ticket);
			while (!m_queue.Dequeue(data, ticket)) {};
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
		typename NCPS::ConcurrentQueue<t_ElementType, t_BlockSize, t_EnableBatch>::ReadReservationTicket ticket;
		m_queue.InitializeReservationTicket(ticket);

		t_ElementType data = t_ElementType();
		for (size_t i = 0; i < nElements; ++i)
		{
			m_queue.Dequeue(data, ticket);
		}
	}
private:
	NCPS::ConcurrentQueue<t_ElementType, t_BlockSize, t_EnableBatch> m_queue;
};

template<typename t_ElementType, ssize_t t_BlockSize, bool t_EnableBatch>
class QueueWrapper<NCPS::ConcurrentQueue<t_ElementType, t_BlockSize, t_EnableBatch>, TicketType::NONE>
{
public:
	QueueWrapper()
		: m_queue(std::thread::hardware_concurrency())
	{}

	void enqueue(size_t nElements, size_t offset)
	{
		for (size_t i = 0; i < nElements; ++i)
		{
			t_ElementType data = t_ElementType(offset + i);
			m_queue.Enqueue(data);
		}
	}
	void enqueueMove(size_t nElements)
	{
		for (size_t i = 0; i < nElements; ++i)
		{
			t_ElementType data = t_ElementType();
			m_queue.Enqueue(std::move(data));
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
			while (!m_queue.Dequeue(data)) {};
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
			m_queue.Dequeue(data);
		}
	}
private:
	NCPS::ConcurrentQueue<t_ElementType, t_BlockSize, t_EnableBatch> m_queue;
};
