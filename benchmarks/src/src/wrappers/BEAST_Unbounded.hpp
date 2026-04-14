#pragma once

#include "../../../../include/BEAST/ConcurrentQueue.hpp"
#include "../QueueWrapper.hpp"
#include <thread>

#define HAS_BEAST_UNBOUNDED

template<typename t_ElementType, size_t t_BlockSize, bool t_EnableBatch, template<typename> typename t_AllocatorType>
class QueueWrapper<BEAST::ConcurrentQueue<t_ElementType, t_BlockSize, t_EnableBatch, t_AllocatorType>, TicketType::PERSISTENT, 0, PointerQueuePolicy::None>
{
public:
	void enqueue(size_t nElements, size_t offset, int tid)
	{
		for (size_t i = 0; i < nElements; ++i)
		{
			t_ElementType data = t_ElementType(offset + i);
			m_queue.Enqueue(data);
		}
	}
	void dequeue(size_t nElements, int tid)
	{
#ifdef VERIFY
		std::unordered_map<int, int> localValues;
#endif
		typename BEAST::ConcurrentQueue<t_ElementType, t_BlockSize, t_EnableBatch>::ReadReservationTicket ticket;
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
	void dequeueEmpty(size_t nElements, int tid)
	{
		typename BEAST::ConcurrentQueue<t_ElementType, t_BlockSize, t_EnableBatch>::ReadReservationTicket ticket;
		m_queue.InitializeReservationTicket(ticket);

		t_ElementType data = t_ElementType();
		for (size_t i = 0; i < nElements; ++i)
		{
			m_queue.Dequeue(data, ticket);
		}
	}
private:
	BEAST::ConcurrentQueue<t_ElementType, t_BlockSize, t_EnableBatch> m_queue;
};

template<typename t_ElementType, size_t t_BlockSize, bool t_EnableBatch, size_t t_BatchSize, template<typename> typename t_AllocatorType>
class QueueWrapper<BEAST::ConcurrentQueue<t_ElementType, t_BlockSize, t_EnableBatch, t_AllocatorType>, TicketType::BATCH, t_BatchSize, PointerQueuePolicy::None>
{
public:
	void enqueue(size_t nElements, size_t offset, int tid)
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
	void dequeue(size_t nElements, int tid)
	{
#ifdef VERIFY
		std::unordered_map<int, int> localValues;
#endif
		typename BEAST::ConcurrentQueue<t_ElementType, t_BlockSize, t_EnableBatch>::BatchDequeueList batch = m_queue.CreateDequeueList();

		size_t totalRemaining = nElements;
		while (totalRemaining > 0)
		{
			m_queue.DequeueBatch(batch, std::min(t_BatchSize, totalRemaining));
			while (batch.More())
			{
				t_ElementType data;
				while (!batch.Next(data))
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
		typename BEAST::ConcurrentQueue<t_ElementType, t_BlockSize, t_EnableBatch>::BatchDequeueList batch = m_queue.CreateDequeueList();

		for (size_t i = 0; i < nElements; ++i)
		{
			m_queue.DequeueBatch(batch, t_BatchSize);
		}
	}
private:
	BEAST::ConcurrentQueue<t_ElementType, t_BlockSize, t_EnableBatch> m_queue;
};

template<typename t_ElementType, size_t t_BlockSize, bool t_EnableBatch, template<typename> typename t_AllocatorType>
class QueueWrapper<BEAST::ConcurrentQueue<t_ElementType, t_BlockSize, t_EnableBatch, t_AllocatorType>, TicketType::EPHEMERAL, 0, PointerQueuePolicy::None>
{
public:
	void enqueue(size_t nElements, size_t offset, int tid)
	{
		for (size_t i = 0; i < nElements; ++i)
		{
			t_ElementType data = t_ElementType(offset + i);
			m_queue.Enqueue(data);
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
			typename BEAST::ConcurrentQueue<t_ElementType, t_BlockSize, t_EnableBatch>::ReadReservationTicket ticket;
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
	void dequeueEmpty(size_t nElements, int tid)
	{
		typename BEAST::ConcurrentQueue<t_ElementType, t_BlockSize, t_EnableBatch>::ReadReservationTicket ticket;
		m_queue.InitializeReservationTicket(ticket);

		t_ElementType data = t_ElementType();
		for (size_t i = 0; i < nElements; ++i)
		{
			m_queue.Dequeue(data, ticket);
		}
	}
private:
	BEAST::ConcurrentQueue<t_ElementType, t_BlockSize, t_EnableBatch> m_queue;
};

template<typename t_ElementType, size_t t_BlockSize, bool t_EnableBatch, template<typename> typename t_AllocatorType>
class QueueWrapper<BEAST::ConcurrentQueue<t_ElementType, t_BlockSize, t_EnableBatch, t_AllocatorType>, TicketType::NONE, 0, PointerQueuePolicy::None>
{
public:
	QueueWrapper()
		: m_queue(std::thread::hardware_concurrency())
	{}

	void enqueue(size_t nElements, size_t offset, int tid)
	{
		for (size_t i = 0; i < nElements; ++i)
		{
			t_ElementType data = t_ElementType(offset + i);
			m_queue.Enqueue(data);
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
	void dequeueEmpty(size_t nElements, int tid)
	{
		t_ElementType data = t_ElementType();
		for (size_t i = 0; i < nElements; ++i)
		{
			m_queue.Dequeue(data);
		}
	}
private:
	BEAST::ConcurrentQueue<t_ElementType, t_BlockSize, t_EnableBatch> m_queue;
};
