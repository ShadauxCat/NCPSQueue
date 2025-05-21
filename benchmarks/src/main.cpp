#include "../../include/NCPS/ConcurrentQueue.hpp"
#include <tbb/concurrent_queue.h>
#include <boost/lockfree/queue.hpp>
#include <deque>
#include <mutex>
#include <thread>
#include <vector>
#include <iostream>
#include <string>
#include <math.h>
#include <limits>
#include <functional>

//#define VERIFY

#ifdef VERIFY
std::unordered_map<int, int> values;
std::mutex valueLock;
#endif

#if defined(_WIN32)
#define NOMINMAX
#include <Windows.h>
	static int64_t GetPerformanceFrequency()
	{
		LARGE_INTEGER frequency;
		QueryPerformanceFrequency(&frequency);
		return frequency.QuadPart;
	}
	static int64_t s_performanceFrequency = GetPerformanceFrequency();
	
	int64_t SteadyNow()
	{
		LARGE_INTEGER time;

		QueryPerformanceCounter(&time);

		double nanoseconds = time.QuadPart * double(1000000000);
		nanoseconds /= s_performanceFrequency;
		return int64_t(nanoseconds);
	}
#elif defined(__apple__)
	static double GetTimeBase()
	{
		mach_timebase_info_data_t info;
		mach_timebase_info(&info);
		return double(info.numer) / double(info.denom);
	}
	static double s_timeBase = GetTimeBase();
	
	int64_t SteadyNow(Resolution resolution)
	{
		uint64_t absTime = mach_absolute_time();
		uint64_t nanosecondResult = absTime * s_timeBase;
		return nanosecondResult;
	}
#else
	int64_t SteadyNow()
	{
		struct timespec ts;
		clock_gettime(CLOCK_MONOTONIC, &ts);
		uint64_t nanosecondResult = ts.tv_sec;
		nanosecondResult *= 1000000000;
		nanosecondResult += ts.tv_nsec;
		return nanosecondResult;
	}
#endif

constexpr size_t NUM_ELEMENTS = 1000000;

namespace ext_1024cores {
	
	template<typename T>
	class mpmc_bounded_queue
	{
	public:
	  mpmc_bounded_queue(size_t buffer_size)
		: buffer_(new cell_t [buffer_size])
		, buffer_mask_(buffer_size - 1)
	  {
		assert((buffer_size >= 2) &&
		  ((buffer_size & (buffer_size - 1)) == 0));
		for (size_t i = 0; i != buffer_size; i += 1)
		  buffer_[i].sequence_.store(i, std::memory_order_relaxed);
		enqueue_pos_.store(0, std::memory_order_relaxed);
		dequeue_pos_.store(0, std::memory_order_relaxed);
	  }
	
	  ~mpmc_bounded_queue()
	  {
		delete [] buffer_;
	  }
	
	  bool enqueue(T const& data)
	  {
		cell_t* cell;
		size_t pos = enqueue_pos_.load(std::memory_order_relaxed);
		for (;;)
		{
		  cell = &buffer_[pos & buffer_mask_];
		  size_t seq =
			cell->sequence_.load(std::memory_order_acquire);
		  intptr_t dif = (intptr_t)seq - (intptr_t)pos;
		  if (dif == 0)
		  {
			if (enqueue_pos_.compare_exchange_weak
				(pos, pos + 1, std::memory_order_relaxed))
			  break;
		  }
		  else if (dif < 0)
			return false;
		  else
			pos = enqueue_pos_.load(std::memory_order_relaxed);
		}
		cell->data_ = data;
		cell->sequence_.store(pos + 1, std::memory_order_release);
		return true;
	  }
	
	  bool dequeue(T& data)
	  {
		cell_t* cell;
		size_t pos = dequeue_pos_.load(std::memory_order_relaxed);
		for (;;)
		{
		  cell = &buffer_[pos & buffer_mask_];
		  size_t seq =
			cell->sequence_.load(std::memory_order_acquire);
		  intptr_t dif = (intptr_t)seq - (intptr_t)(pos + 1);
		  if (dif == 0)
		  {
			if (dequeue_pos_.compare_exchange_weak
				(pos, pos + 1, std::memory_order_relaxed))
			  break;
		  }
		  else if (dif < 0)
			return false;
		  else
			pos = dequeue_pos_.load(std::memory_order_relaxed);
		}
		data = cell->data_;
		cell->sequence_.store
		  (pos + buffer_mask_ + 1, std::memory_order_release);
		return true;
	  }
	
	private:
	  struct cell_t
	  {
		std::atomic<size_t>   sequence_;
		T					 data_;
	  };
	
	  static size_t const	 cacheline_size = 64;
	  typedef char			cacheline_pad_t [cacheline_size];
	
	  cacheline_pad_t		 pad0_;
	  cell_t* const		   buffer_;
	  size_t const			buffer_mask_;
	  cacheline_pad_t		 pad1_;
	  std::atomic<size_t>	 enqueue_pos_;
	  cacheline_pad_t		 pad2_;
	  std::atomic<size_t>	 dequeue_pos_;
	  cacheline_pad_t		 pad3_;
	
	  mpmc_bounded_queue(mpmc_bounded_queue const&);
	  void operator = (mpmc_bounded_queue const&);
	};
}

enum class TicketType
{
	PERSISTENT,
	EPHEMERAL,
	NONE,
	BATCH_1,
	BATCH_10,
	BATCH_100,
	BATCH_1000,
	BALANCED_BATCH_10,
	BALANCED_BATCH_100,
	BALANCED_BATCH_1000
};

template<typename t_QueueType, TicketType t_TicketType = TicketType::PERSISTENT>
class QueueWrapper;

template<typename t_ElementType>
class QueueWrapper<ext_1024cores::mpmc_bounded_queue<t_ElementType>, TicketType::PERSISTENT>
{
public:
	QueueWrapper()
		: m_queue(pow(2, ceil(log(NUM_ELEMENTS)/log(2))))
	{
		
	}

	void enqueue(size_t nElements, size_t offset)
	{
		for (size_t i = 0; i < nElements; ++i)
		{
			t_ElementType data = t_ElementType(offset + i);
			m_queue.enqueue(data);
		}
	}
	void enqueueMove(size_t nElements)
	{
		for (size_t i = 0; i < nElements; ++i)
		{
			t_ElementType data = t_ElementType();
			m_queue.enqueue(std::move(data));
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
			while (!m_queue.dequeue(data)) {};
#ifdef VERIFY
			localValues[data] += 1;
#endif
		}
#ifdef VERIFY
		{
			std::lock_guard<std::mutex> guard(valueLock);
			for(auto& kvp : localValues)
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
			m_queue.dequeue(data);
		}
	}

private:
	ext_1024cores::mpmc_bounded_queue<t_ElementType> m_queue;
};

template<typename t_ElementType>
class QueueWrapper<tbb::concurrent_bounded_queue<t_ElementType>, TicketType::PERSISTENT>
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
			for(auto& kvp : localValues)
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
class QueueWrapper<tbb::concurrent_queue<t_ElementType>, TicketType::PERSISTENT>
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
			for(auto& kvp : localValues)
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

template<typename t_ElementType>
class QueueWrapper<boost::lockfree::queue<t_ElementType>, TicketType::PERSISTENT>
{
public:
	QueueWrapper()
		: m_queue(NUM_ELEMENTS)
	{
		
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
			while (!m_queue.pop(data)) {};
#ifdef VERIFY
			localValues[data] += 1;
#endif
		}
#ifdef VERIFY
		{
			std::lock_guard<std::mutex> guard(valueLock);
			for(auto& kvp : localValues)
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
			m_queue.pop(data);
		}
	}
private:
	boost::lockfree::queue<t_ElementType> m_queue;
};

template <typename t_ElementType>
using BoostBoundedQueue = boost::lockfree::queue<t_ElementType, boost::lockfree::fixed_sized<true>, boost::lockfree::capacity<NUM_ELEMENTS>>;

template<typename t_ElementType>
class QueueWrapper<BoostBoundedQueue<t_ElementType>, TicketType::PERSISTENT>
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
			while (!m_queue.pop(data)) {};
#ifdef VERIFY
			localValues[data] += 1;
#endif
		}
#ifdef VERIFY
		{
			std::lock_guard<std::mutex> guard(valueLock);
			for(auto& kvp : localValues)
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
			m_queue.pop(data);
		}
	}
private:
	BoostBoundedQueue<t_ElementType> m_queue;
};

template<typename t_ElementType>
class QueueWrapper<std::deque<t_ElementType>, TicketType::PERSISTENT>
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
			for(auto& kvp : localValues)
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
			for(auto& kvp : localValues)
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
class QueueWrapper<NCPS::ConcurrentQueue<t_ElementType, t_BlockSize, t_EnableBatch>, TicketType::BATCH_1>
{
	std::atomic<int> totalRemaining{ 0 };
public:
	void enqueue(size_t nElements, size_t offset)
	{
		for (size_t i = 0; i < nElements; ++i)
		{
			t_ElementType data = t_ElementType(offset+i);
			m_queue.EnqueueBatch(&data, 1);
		}
	}
	void dequeue(size_t nElements)
	{
#ifdef VERIFY
		std::unordered_map<int, int> localValues;
#endif
		typename NCPS::ConcurrentQueue<t_ElementType, t_BlockSize, t_EnableBatch>::BatchDequeueList batch;

		totalRemaining += nElements;
		while(totalRemaining.load() > 0)
		{
			m_queue.DequeueBatch(batch, 1);
			while(batch.More())
			{
				t_ElementType data;
				while(!batch.Next(data))
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
			for(auto& kvp : localValues)
			{
				values[kvp.first] += kvp.second;
			}
		}
#endif
	}
	void dequeueEmpty(size_t nElements)
	{
		typename NCPS::ConcurrentQueue<t_ElementType, t_BlockSize, t_EnableBatch>::BatchDequeueList batch;

		for (size_t i = 0; i < nElements; ++i)
		{
			m_queue.DequeueBatch(batch, 1);
		}
	}
private:
	NCPS::ConcurrentQueue<t_ElementType, t_BlockSize, t_EnableBatch> m_queue;
};


template<typename t_ElementType, ssize_t t_BlockSize, bool t_EnableBatch>
class QueueWrapper<NCPS::ConcurrentQueue<t_ElementType, t_BlockSize, t_EnableBatch>, TicketType::BATCH_10>
{
	std::atomic<int> totalRemaining{ 0 };
public:
	void enqueue(size_t nElements, size_t offset)
	{
		size_t remaining = nElements;
		while(remaining > 0)
		{
			size_t batchSize = remaining < 10 ? remaining : 10;
			t_ElementType data[10];
			for(size_t j = 0; j < batchSize; ++j)
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
		typename NCPS::ConcurrentQueue<t_ElementType, t_BlockSize, t_EnableBatch>::BatchDequeueList batch;

		totalRemaining += nElements;
		while(totalRemaining.load() > 0)
		{
			m_queue.DequeueBatch(batch, 10);
			while(batch.More())
			{
				t_ElementType data;
				while(!batch.Next(data))
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
			for(auto& kvp : localValues)
			{
				values[kvp.first] += kvp.second;
			}
		}
#endif
	}
	void dequeueEmpty(size_t nElements)
	{
		typename NCPS::ConcurrentQueue<t_ElementType, t_BlockSize, t_EnableBatch>::BatchDequeueList batch;

		for (size_t i = 0; i < nElements; ++i)
		{
			m_queue.DequeueBatch(batch, 10);
		}
	}
private:
	NCPS::ConcurrentQueue<t_ElementType, t_BlockSize, t_EnableBatch> m_queue;
};

template<typename t_ElementType, ssize_t t_BlockSize, bool t_EnableBatch>
class QueueWrapper<NCPS::ConcurrentQueue<t_ElementType, t_BlockSize, t_EnableBatch>, TicketType::BATCH_100>
{
	std::atomic<int> totalRemaining{ 0 };
public:
	void enqueue(size_t nElements, size_t offset)
	{
		size_t remaining = nElements;
		while(remaining > 0)
		{
			size_t batchSize = remaining < 100 ? remaining : 100;
			t_ElementType data[100];
			for(size_t j = 0; j < batchSize; ++j)
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
		typename NCPS::ConcurrentQueue<t_ElementType, t_BlockSize, t_EnableBatch>::BatchDequeueList batch;

		totalRemaining += nElements;
		while(totalRemaining.load() > 0)
		{
			m_queue.DequeueBatch(batch, 100);
			while(batch.More())
			{
				t_ElementType data;
				while(!batch.Next(data))
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
			for(auto& kvp : localValues)
			{
				values[kvp.first] += kvp.second;
			}
		}
#endif
	}
	void dequeueEmpty(size_t nElements)
	{
		typename NCPS::ConcurrentQueue<t_ElementType, t_BlockSize, t_EnableBatch>::BatchDequeueList batch;

		for (size_t i = 0; i < nElements; ++i)
		{
			m_queue.DequeueBatch(batch, 1000);
		}
	}
private:
	NCPS::ConcurrentQueue<t_ElementType, t_BlockSize, t_EnableBatch> m_queue;
};

template<typename t_ElementType, ssize_t t_BlockSize, bool t_EnableBatch>
class QueueWrapper<NCPS::ConcurrentQueue<t_ElementType, t_BlockSize, t_EnableBatch>, TicketType::BATCH_1000>
{
	std::atomic<int> totalRemaining{ 0 };
public:
	void enqueue(size_t nElements, size_t offset)
	{
		size_t remaining = nElements;
		while(remaining > 0)
		{
			size_t batchSize = remaining < 1000 ? remaining : 1000;
			t_ElementType data[1000];
			for(size_t j = 0; j < batchSize; ++j)
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
		typename NCPS::ConcurrentQueue<t_ElementType, t_BlockSize, t_EnableBatch>::BatchDequeueList batch;

		totalRemaining += nElements;
		while(totalRemaining.load() > 0)
		{
			m_queue.DequeueBatch(batch, 1000);
			while(batch.More())
			{
				t_ElementType data;
				while(!batch.Next(data))
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
			for(auto& kvp : localValues)
			{
				values[kvp.first] += kvp.second;
			}
		}
#endif
	}
	void dequeueEmpty(size_t nElements)
	{
		typename NCPS::ConcurrentQueue<t_ElementType, t_BlockSize, t_EnableBatch>::BatchDequeueList batch;

		for (size_t i = 0; i < nElements; ++i)
		{
			m_queue.DequeueBatch(batch, 1000);
		}
	}
private:
	NCPS::ConcurrentQueue<t_ElementType, t_BlockSize, t_EnableBatch> m_queue;
};

template<typename t_ElementType, ssize_t t_BlockSize, bool t_EnableBatch>
class QueueWrapper<NCPS::ConcurrentQueue<t_ElementType, t_BlockSize, t_EnableBatch>, TicketType::BALANCED_BATCH_10>
{
	std::atomic<int> totalRemaining{ 0 };
public:
	void enqueue(size_t nElements, size_t offset)
	{
		size_t totalElements = 0;
		while(totalElements < nElements)
		{
			size_t batchSize = std::min(nElements - totalElements, size_t(10.0/double(NUM_ELEMENTS) * double(nElements)));
			t_ElementType data[10];
			for(size_t j = 0; j < batchSize; ++j)
			{
				data[j] = t_ElementType(offset + totalElements + j);
			}
			m_queue.EnqueueBatch(data, batchSize);
			totalElements += batchSize;
		}
	}
	void dequeue(size_t nElements)
	{
#ifdef VERIFY
		std::unordered_map<int, int> localValues;
#endif
		typename NCPS::ConcurrentQueue<t_ElementType, t_BlockSize, t_EnableBatch>::BatchDequeueList batch;

		totalRemaining += nElements;
		const size_t batchSize = size_t(10.0/double(NUM_ELEMENTS) * double(nElements));
		while(totalRemaining.load() > 0)
		{
			m_queue.DequeueBatch(batch, batchSize);
			while(batch.More())
			{
				t_ElementType data;
				while(!batch.Next(data))
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
			for(auto& kvp : localValues)
			{
				values[kvp.first] += kvp.second;
			}
		}
#endif
	}
	void dequeueEmpty(size_t nElements)
	{
		typename NCPS::ConcurrentQueue<t_ElementType, t_BlockSize, t_EnableBatch>::BatchDequeueList batch;

		const size_t batchSize = size_t(10.0/double(NUM_ELEMENTS) * double(nElements));
		for (size_t i = 0; i < nElements; ++i)
		{
			m_queue.DequeueBatch(batch, batchSize);
		}
	}
private:
	NCPS::ConcurrentQueue<t_ElementType, t_BlockSize, t_EnableBatch> m_queue;
};

template<typename t_ElementType, ssize_t t_BlockSize, bool t_EnableBatch>
class QueueWrapper<NCPS::ConcurrentQueue<t_ElementType, t_BlockSize, t_EnableBatch>, TicketType::BALANCED_BATCH_100>
{
	std::atomic<int> totalRemaining{ 0 };
public:
	void enqueue(size_t nElements, size_t offset)
	{
		size_t totalElements = 0;
		while(totalElements < nElements)
		{
			size_t batchSize = std::min(nElements - totalElements, size_t(100.0/double(NUM_ELEMENTS) * double(nElements)));
			t_ElementType data[100];
			for(size_t j = 0; j < batchSize; ++j)
			{
				data[j] = t_ElementType(offset + totalElements + j);
			}
			m_queue.EnqueueBatch(data, batchSize);
			totalElements += batchSize;
		}
	}
	void dequeue(size_t nElements)
	{
#ifdef VERIFY
		std::unordered_map<int, int> localValues;
#endif
		typename NCPS::ConcurrentQueue<t_ElementType, t_BlockSize, t_EnableBatch>::BatchDequeueList batch;

		totalRemaining += nElements;
		const size_t batchSize = size_t(100.0/double(NUM_ELEMENTS) * double(nElements));
		while(totalRemaining.load() > 0)
		{
			m_queue.DequeueBatch(batch, batchSize);
			while(batch.More())
			{
				t_ElementType data;
				while(!batch.Next(data))
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
			for(auto& kvp : localValues)
			{
				values[kvp.first] += kvp.second;
			}
		}
#endif
	}
	void dequeueEmpty(size_t nElements)
	{
		typename NCPS::ConcurrentQueue<t_ElementType, t_BlockSize, t_EnableBatch>::BatchDequeueList batch;

		const size_t batchSize = size_t(100.0/double(NUM_ELEMENTS) * double(nElements));
		for (size_t i = 0; i < nElements; ++i)
		{
			m_queue.DequeueBatch(batch, batchSize);
		}
	}
private:
	NCPS::ConcurrentQueue<t_ElementType, t_BlockSize, t_EnableBatch> m_queue;
};


template<typename t_ElementType, ssize_t t_BlockSize, bool t_EnableBatch>
class QueueWrapper<NCPS::ConcurrentQueue<t_ElementType, t_BlockSize, t_EnableBatch>, TicketType::BALANCED_BATCH_1000>
{
	std::atomic<int> totalRemaining{ 0 };
public:
	void enqueue(size_t nElements, size_t offset)
	{
		size_t totalElements = 0;
		while(totalElements < nElements)
		{
			size_t batchSize = std::min(nElements - totalElements, size_t(1000.0/double(NUM_ELEMENTS) * double(nElements)));
			t_ElementType data[1000];
			for(size_t j = 0; j < batchSize; ++j)
			{
				data[j] = t_ElementType(offset + totalElements + j);
			}
			m_queue.EnqueueBatch(data, batchSize);
			totalElements += batchSize;
		}
	}
	void dequeue(size_t nElements)
	{
#ifdef VERIFY
		std::unordered_map<int, int> localValues;
#endif
		typename NCPS::ConcurrentQueue<t_ElementType, t_BlockSize, t_EnableBatch>::BatchDequeueList batch;

		totalRemaining += nElements;
		const size_t batchSize = size_t(1000.0/double(NUM_ELEMENTS) * double(nElements));
		while(totalRemaining.load() > 0)
		{
			m_queue.DequeueBatch(batch, batchSize);
			while(batch.More())
			{
				t_ElementType data;
				while(!batch.Next(data))
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
			for(auto& kvp : localValues)
			{
				values[kvp.first] += kvp.second;
			}
		}
#endif
	}
	void dequeueEmpty(size_t nElements)
	{
		typename NCPS::ConcurrentQueue<t_ElementType, t_BlockSize, t_EnableBatch>::BatchDequeueList batch;

		const size_t batchSize = size_t(1000.0/double(NUM_ELEMENTS) * double(nElements));
		for (size_t i = 0; i < nElements; ++i)
		{
			m_queue.DequeueBatch(batch, batchSize);
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
			t_ElementType data = t_ElementType(offset+i);
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
			for(auto& kvp : localValues)
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
		: m_queue(1024)
	{}

	void enqueue(size_t nElements, size_t offset)
	{
		for (size_t i = 0; i < nElements; ++i)
		{
			t_ElementType data = t_ElementType(offset+i);
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
			for(auto& kvp : localValues)
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

template<typename t_ElementType, TicketType t_TicketType>
class QueueWrapper<NCPS::ConcurrentBoundedQueue<t_ElementType, NUM_ELEMENTS>, t_TicketType>
{
public:
	QueueWrapper()
		: m_queue(new NCPS::ConcurrentBoundedQueue<t_ElementType, NUM_ELEMENTS>())
	{}
	
	~QueueWrapper()
	{
		delete m_queue;
	}

	void enqueue(size_t nElements, size_t offset)
	{
		NCPS::BoundedWriteReservationTicket<t_ElementType> ticket;

		for (size_t i = 0; i < nElements; ++i)
		{
			t_ElementType data = t_ElementType(offset+i);
			m_queue->Enqueue(data, ticket);
		}
	}
	void enqueueMove(size_t nElements)
	{
		NCPS::BoundedWriteReservationTicket<t_ElementType> ticket;

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
		NCPS::BoundedReadReservationTicket<t_ElementType> ticket;

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
			for(auto& kvp : localValues)
			{
				values[kvp.first] += kvp.second;
			}
		}
#endif
	}
	void dequeueEmpty(size_t nElements)
	{
		NCPS::BoundedReadReservationTicket<t_ElementType> ticket;

		t_ElementType data = t_ElementType();
		for (size_t i = 0; i < nElements; ++i)
		{
			m_queue->Dequeue(data, ticket);
		}
	}
private:
	NCPS::ConcurrentBoundedQueue<t_ElementType, NUM_ELEMENTS>* m_queue;
};


template<typename t_ElementType>
class QueueWrapper<NCPS::ConcurrentBoundedQueue<t_ElementType, NUM_ELEMENTS>, TicketType::NONE>
{
public:
	QueueWrapper()
		: m_queue(new NCPS::ConcurrentBoundedQueue<t_ElementType, NUM_ELEMENTS>(1024, 1024))
	{}

	~QueueWrapper()
	{
		delete m_queue;
	}

	void enqueue(size_t nElements, size_t offset)
	{
		for (size_t i = 0; i < nElements; ++i)
		{
			t_ElementType data = t_ElementType(offset+i);
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
			for(auto& kvp : localValues)
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
	NCPS::ConcurrentBoundedQueue<t_ElementType, NUM_ELEMENTS>* m_queue;
};
template<typename t_Type>
struct TypeName
{
private:
	static constexpr size_t prefix_size = sizeof("static std::string TypeName<") - 1;
public:
	static std::string GetName(bool useMove, TicketType ticketType)
	{
#ifdef _WIN32
		std::string ret = __FUNCTION__;
		ret = ret.substr(ret.find('<')+7);
		ret = ret.substr(0, ret.find("GetName") - 4);
#else
		std::string ret = __PRETTY_FUNCTION__;
		ret = ret.substr(ret.find("t_Type = ")+9);
		ret = ret.substr(0, ret.find("]"));
#endif
		if (useMove)
		{
			ret += " [moves]";
		}
		switch(ticketType)
		{
		case TicketType::EPHEMERAL:
			ret += " [Ephemeral Tickets]";
			break;
		case TicketType::NONE:
			ret += " [No Tickets]";
			break;
		case TicketType::BATCH_1:
			ret += " [Batch (1)]";
			break;
		case TicketType::BATCH_10:
			ret += " [Batch (10)]";
			break;
		case TicketType::BATCH_100:
			ret += " [Batch (100)]";
			break;
		case TicketType::BATCH_1000:
			ret += " [Batch (1000)]";
			break;
		case TicketType::BALANCED_BATCH_10:
			ret += " [Balanced Batch (10)]";
			break;
		case TicketType::BALANCED_BATCH_100:
			ret += " [Balanced Batch (100)]";
			break;
		case TicketType::BALANCED_BATCH_1000:
			ret += " [Balanced Batch (1000)]";
			break;
		default:
			break;
		}
		return ret;
	}
};

std::atomic<int64_t> timer(-1);
std::atomic<int64_t> started(0);

void timeFn(std::function<void()> fn)
{
	++started;
	while(timer.load() == -1) {}
	fn();
	timer.store(SteadyNow());
}

int64_t mean(std::vector<int64_t> const& data)
{
	int64_t total = 0;
	for(auto& item : data)
	{
		total += item;
	}
	return total / data.size();
}

int64_t median(std::vector<int64_t> const& data)
{
	std::vector<int64_t> newVect(data.begin(), data.end());
	std::sort(newVect.begin(), newVect.end());
	auto size = newVect.size();
	if(size % 2 == 0)
	{
		return (newVect[size/2 - 1] + newVect[size/2])/2;
	}
	return newVect[size/2];	
}

int64_t Max(std::vector<int64_t> const& data)
{
	int64_t val = 0;
	for(auto& item : data)
	{
		val = val > item ? val : item;
	}
	return val;
}

int64_t Min(std::vector<int64_t> const& data)
{
	int64_t val = (std::numeric_limits<int64_t>::max)();
	for(auto& item : data)
	{
		val = val < item ? val : item;
	}
	return val;
}

double OpsPerSecond(int64_t duration, size_t numOps)
{
	double avgNanosPerOp = double(duration) / numOps;
	// 1000000000 nanoseconds = 1 second
	double opsPerSecond = 1000000000 / avgNanosPerOp;
	return opsPerSecond;
}

#ifdef VERIFY
void verify(std::string type, int operation, int producers, int consumers, int count)
{
	bool valid = true;
	int totalCount = 0;
	for(int i = 0; i < count; ++i)
	{
		if(values.find(i) == values.end())
		{
			std::cout << "\033[1;31m" << type << " " << operation << " " << producers << " " << consumers << "--> ERROR: VALUE " << i << " WAS NOT FOUND IN THE QUEUE RESULTS.\033[0m" << std::endl;
			valid = false;
			continue;
		}
		if(values.at(i) != 1)
		{
			std::cout << "\033[1;31m" << type << " " << operation << " " << producers << " " << consumers << "--> ERROR: VALUE " << i << " WAS DEQUEUED " << values.at(i) << " TIMES!\033[0m" << std::endl;
			valid = false;
		}
		totalCount += values.at(i);
	}
	if(totalCount != count)
	{
		std::cout << "\033[1;31m" << type << " " << operation << " " << producers << " " << consumers << "--> ERROR: Total dequeue count " << totalCount << " does not match expected " << count << "\033[0m" << std::endl;
		valid = false;
	}
	if(!valid)
	{
		exit(1);
	}
	values.clear();
	std::cout << "\033[1;32m" << type << " " << operation << " " << producers << " " << consumers << "--> Verified! " << count << " elements (" << NUM_ELEMENTS << " adjusted for thread count) are valid.\033[0m" << std::endl;
}
#endif

#ifdef VERIFY
constexpr int nIters = 1;
#else
constexpr int nIters = 25;
#endif

template<typename t_ElementType, typename t_QueueType, TicketType t_TicketType = TicketType::PERSISTENT>
void RunTestsOnQueueTypeWithThreadCounts(size_t enqueueThreads, size_t dequeueThreads, bool useMoves = false)
{
	size_t adjustedNumElements = NUM_ELEMENTS;
	while(adjustedNumElements % enqueueThreads != 0 || adjustedNumElements % dequeueThreads != 0)
	{
		--adjustedNumElements;
	}
	size_t nEnqueueElements = adjustedNumElements / enqueueThreads;
	size_t nDequeueElements = adjustedNumElements / dequeueThreads;

	std::vector<int64_t> dequeues;
	dequeues.resize(dequeueThreads);
	std::vector<int64_t> enqueues;
	enqueues.resize(enqueueThreads);
	std::vector<int64_t> times[4];
	for (auto& timeVect : times)
	{
		timeVect.resize(nIters);
	}

	for (int iter = 0; iter < nIters; ++iter)
	{
		QueueWrapper<t_QueueType, t_TicketType> separateEnqueueDequeueWrapper;
		if(enqueueThreads == 1 || dequeueThreads == 1)
		{
			// Time the enqueues only.
			std::vector<std::thread> threads;
			
			size_t numEnqueuesToActuallyDo = enqueueThreads;
			size_t actualNEnqueueElements = nEnqueueElements;
			if(dequeueThreads != 1)
			{
				// Most queues operate faster single-threaded, and since we're only measuring raw enqueue performance once (when dequeue threads == 1),
				// we can just set it to 1 thread on all the other scenarios to make the benchmarks run faster.
				numEnqueuesToActuallyDo = 1;
				actualNEnqueueElements = adjustedNumElements;
			}
			threads.reserve(numEnqueuesToActuallyDo);

			for (size_t i = 0; i < numEnqueuesToActuallyDo; ++i)
			{
				std::function<void()> enqueueFunc = std::bind(&QueueWrapper<t_QueueType, t_TicketType>::enqueue, &separateEnqueueDequeueWrapper, actualNEnqueueElements, actualNEnqueueElements*i);
				threads.emplace_back(
					std::bind(
						timeFn,
						enqueueFunc
					)
				);
	#if 0
	#ifdef _WIN32
				if(!SetThreadAffinityMask(threads.back().native_handle(), 1 << (i % std::thread::hardware_concurrency())))
				{
					abort();
				}
	#else
				cpu_set_t cpuset;
				pthread_t thread = threads.back().native_handle();

				CPU_ZERO(&cpuset);
				CPU_SET((i % std::thread::hardware_concurrency()), &cpuset);
				if(pthread_setaffinity_np(thread, sizeof(cpu_set_t), &cpuset) != 0)
				{
					abort();
				}
	#endif
	#endif
			}
			while(started.load() < numEnqueuesToActuallyDo) {}
			started.store(0);
			int64_t start = SteadyNow();
			timer.store(start);
			for (auto& thread : threads)
			{
				thread.join();
			}
			times[0][iter] = timer.exchange(-1) - start;
		}
		if(enqueueThreads == 1)
		{
			// Time the dequeues only.
			std::vector<std::thread> threads;
			threads.reserve(dequeueThreads);

			for (size_t i = 0; i < dequeueThreads; ++i)
			{
				std::function<void()> dequeueFunc = std::bind(&QueueWrapper<t_QueueType, t_TicketType>::dequeue, &separateEnqueueDequeueWrapper, nDequeueElements);
				threads.emplace_back(
					std::bind(
						timeFn,
						dequeueFunc
					)
				);
#if 0
#ifdef _WIN32
				if(!SetThreadAffinityMask(threads.back().native_handle(), 1 << (i % std::thread::hardware_concurrency())))
				{
					abort();
				}
#else
				cpu_set_t cpuset;
				pthread_t thread = threads.back().native_handle();

				CPU_ZERO(&cpuset);
				CPU_SET((i % std::thread::hardware_concurrency()), &cpuset);
				if(pthread_setaffinity_np(thread, sizeof(cpu_set_t), &cpuset) != 0)
				{
					abort();
				}
#endif
#endif
			}
			while(started.load() < dequeueThreads) {}
			started.store(0);
			int64_t start = SteadyNow();
			timer.store(start);
			for (auto& thread : threads)
			{
				thread.join();
			}
			times[1][iter] = timer.exchange(-1) - start;
#ifdef VERIFY
			verify(TypeName<t_QueueType>::GetName(useMoves, t_TicketType), 12, enqueueThreads, dequeueThreads, adjustedNumElements);
#endif
		}

		{
			// Time both happening concurrently.
			QueueWrapper<t_QueueType, t_TicketType> dualWrapper;
			std::vector<std::thread> threads;
			threads.reserve(enqueueThreads + dequeueThreads);

			size_t enq = 0;
			size_t deq = 0;
			for (;;)
			{
				if (++deq <= dequeueThreads)
				{
					std::function<void()> fn = std::bind(&QueueWrapper<t_QueueType, t_TicketType>::dequeue, &dualWrapper, nDequeueElements);
					threads.emplace_back(
						std::bind(
							timeFn,
							fn
						)
					);
#if 0
#ifdef _WIN32
					if(!SetThreadAffinityMask(threads.back().native_handle(), 1 << ((enq + deq) % std::thread::hardware_concurrency())))
					{
						abort();
					}
#else
					cpu_set_t cpuset;
					pthread_t thread = threads.back().native_handle();

					CPU_ZERO(&cpuset);
					CPU_SET(((enq + deq) % std::thread::hardware_concurrency()), &cpuset);
					if(pthread_setaffinity_np(thread, sizeof(cpu_set_t), &cpuset) != 0)
					{
						abort();
					}
#endif
#endif
				}
				if (++enq <= enqueueThreads)
				{
					std::function<void()> fn = std::bind(&QueueWrapper<t_QueueType, t_TicketType>::enqueue, &dualWrapper, nEnqueueElements, nEnqueueElements*(enq - 1));
					threads.emplace_back(
						std::bind(
							timeFn,
							fn
						)
					);
#if 0
#ifdef _WIN32
					if(!SetThreadAffinityMask(threads.back().native_handle(), 1 << ((enq + deq) % std::thread::hardware_concurrency())))
					{
						abort();
					}
#else
					cpu_set_t cpuset;
					pthread_t thread = threads.back().native_handle();

					CPU_ZERO(&cpuset);
					CPU_SET(((enq + deq) % std::thread::hardware_concurrency()), &cpuset);
					if(pthread_setaffinity_np(thread, sizeof(cpu_set_t), &cpuset))
					{
						abort();
					}
#endif
#endif
				}
				if (enq >= enqueueThreads && deq >= dequeueThreads)
				{
					break;
				}
			}
			while(started.load() < dequeueThreads + enqueueThreads) {}
			started.store(0);
			int64_t start = SteadyNow();
			timer.store(start);
			for (auto& thread : threads)
			{
				thread.join();
			}
			times[2][iter] = timer.exchange(-1) - start;
#ifdef VERIFY
			verify(TypeName<t_QueueType>::GetName(useMoves, t_TicketType), 3, enqueueThreads, dequeueThreads, adjustedNumElements);
#endif
		}

		if(enqueueThreads == 1)
		{
			// Time dequeues from an empty queue
			QueueWrapper<t_QueueType, t_TicketType> emptyWrapper;
			std::vector<std::thread> threads;
			threads.reserve(dequeueThreads);

			for (size_t i = 0; i < dequeueThreads; ++i)
			{
				std::function<void()> fn = std::bind(&QueueWrapper<t_QueueType, t_TicketType>::dequeueEmpty, &emptyWrapper, nDequeueElements * 10);
				threads.emplace_back(
					std::bind(
						timeFn,
						fn
					)
				);
#if 0
#ifdef _WIN32
				if (!SetThreadAffinityMask(threads.back().native_handle(), 1 << (i % std::thread::hardware_concurrency())))
				{
					abort();
				}
#else
				cpu_set_t cpuset;
				pthread_t thread = threads.back().native_handle();

				CPU_ZERO(&cpuset);
				CPU_SET((i % std::thread::hardware_concurrency()), &cpuset);
				if (pthread_setaffinity_np(thread, sizeof(cpu_set_t), &cpuset) != 0)
				{
					abort();
				}
#endif
#endif
			}
			while(started.load() < dequeueThreads) {}
			started.store(0);
			int64_t start = SteadyNow();
			timer.store(start);
			for (auto& thread : threads)
			{
				thread.join();
			}
			times[3][iter] = timer.exchange(-1) - start;
		}
	}

	if(dequeueThreads == 1)
	{
		std::cout << TypeName<t_QueueType>::GetName(useMoves, t_TicketType) << "\t" << 1 << "\t" << enqueueThreads << "\t" << dequeueThreads << "\t" <<
			OpsPerSecond(mean(times[0]), adjustedNumElements) << "\t" <<
			OpsPerSecond(Max(times[0]), adjustedNumElements) << "\t" <<
			OpsPerSecond(Min(times[0]), adjustedNumElements) << "\t" <<
			OpsPerSecond(median(times[0]), adjustedNumElements) << std::endl;
	}
		
	if(enqueueThreads == 1)
	{
		std::cout << TypeName<t_QueueType>::GetName(useMoves, t_TicketType) << "\t" << 2 << "\t" << enqueueThreads << "\t" << dequeueThreads << "\t" <<
			OpsPerSecond(mean(times[1]), adjustedNumElements) << "\t" <<
			OpsPerSecond(Max(times[1]), adjustedNumElements) << "\t" <<
			OpsPerSecond(Min(times[1]), adjustedNumElements) << "\t" <<
			OpsPerSecond(median(times[1]), adjustedNumElements) << std::endl;
	}
		
	std::cout << TypeName<t_QueueType>::GetName(useMoves, t_TicketType) << "\t" << 3 << "\t" << enqueueThreads << "\t" << dequeueThreads << "\t" <<
		OpsPerSecond(mean(times[2]), adjustedNumElements) << "\t" <<
		OpsPerSecond(Max(times[2]), adjustedNumElements) << "\t" <<
		OpsPerSecond(Min(times[2]), adjustedNumElements) << "\t" <<
		OpsPerSecond(median(times[2]), adjustedNumElements) << std::endl;
		
		
	if(enqueueThreads == 1)
	{
		std::cout << TypeName<t_QueueType>::GetName(useMoves, t_TicketType) << "\t" << 4 << "\t" << enqueueThreads << "\t" << dequeueThreads << "\t" <<
			OpsPerSecond(mean(times[3]), adjustedNumElements * 10) << "\t" <<
			OpsPerSecond(Max(times[3]), adjustedNumElements * 10) << "\t" <<
			OpsPerSecond(Min(times[3]), adjustedNumElements * 10) << "\t" <<
			OpsPerSecond(median(times[3]), adjustedNumElements) << std::endl;
	}
}

template<typename t_ElementType, typename t_QueueType, TicketType t_TicketType = TicketType::PERSISTENT>
void RunTestsOnQueueType(bool useMoves = false)
{
	size_t totalThreads = std::thread::hardware_concurrency();
	for(size_t i = 1; i <= totalThreads; ++i) {
		for(size_t j = 1; j <= totalThreads; ++j) {
			RunTestsOnQueueTypeWithThreadCounts<t_ElementType, t_QueueType, t_TicketType>(i, j, useMoves);
		}
	}
}


template<typename t_ElementType, typename t_QueueType>
void PrintEmpty()
{
	size_t totalThreads = std::thread::hardware_concurrency();
	for (size_t i = 1; i <= totalThreads; ++i) {
		for (size_t j = 1; j <= totalThreads; ++j) {
			std::cout << TypeName<t_QueueType>::GetName(false, TicketType::PERSISTENT) << "\t" << 0 << "\t" << 0 << "\t" << 0 << "\t" << 0 << std::endl;
		}
	}
}

class NoBoost {};

template<typename t_ElementType, bool t_SupportsBoost = true>
void RunTestsOnElementType()
{
	RunTestsOnQueueType<t_ElementType, ext_1024cores::mpmc_bounded_queue<t_ElementType>>();
	RunTestsOnQueueType<t_ElementType, tbb::concurrent_bounded_queue<t_ElementType>>();
	RunTestsOnQueueType<t_ElementType, tbb::concurrent_queue<t_ElementType>>();
	if constexpr(t_SupportsBoost)
	{
		RunTestsOnQueueType<t_ElementType, boost::lockfree::queue<t_ElementType>>();
	}
	else
	{
		PrintEmpty<t_ElementType, boost::lockfree::queue<t_ElementType>>();
	}
	RunTestsOnQueueType<t_ElementType, std::deque<t_ElementType>>();
	
	RunTestsOnQueueType<t_ElementType, NCPS::ConcurrentQueue<t_ElementType, 8192, true>>();
	RunTestsOnQueueType<t_ElementType, NCPS::ConcurrentQueue<t_ElementType, 8192, false>>();
	RunTestsOnQueueType<t_ElementType, NCPS::ConcurrentQueue<t_ElementType, 8192, true>, TicketType::BATCH_1>();
	RunTestsOnQueueType<t_ElementType, NCPS::ConcurrentQueue<t_ElementType, 8192, true>, TicketType::BATCH_10>();
	RunTestsOnQueueType<t_ElementType, NCPS::ConcurrentQueue<t_ElementType, 8192, true>, TicketType::BATCH_100>();
	RunTestsOnQueueType<t_ElementType, NCPS::ConcurrentQueue<t_ElementType, 8192, true>, TicketType::BATCH_1000>();
	
	RunTestsOnQueueType<t_ElementType, NCPS::ConcurrentQueue<t_ElementType, NUM_ELEMENTS, true>>();
	RunTestsOnQueueType<t_ElementType, NCPS::ConcurrentQueue<t_ElementType, NUM_ELEMENTS, false>>();
	RunTestsOnQueueType<t_ElementType, NCPS::ConcurrentQueue<t_ElementType, NUM_ELEMENTS, true>, TicketType::BATCH_1>();
	RunTestsOnQueueType<t_ElementType, NCPS::ConcurrentQueue<t_ElementType, NUM_ELEMENTS, true>, TicketType::BATCH_10>();
	RunTestsOnQueueType<t_ElementType, NCPS::ConcurrentQueue<t_ElementType, NUM_ELEMENTS, true>, TicketType::BATCH_100>();
	RunTestsOnQueueType<t_ElementType, NCPS::ConcurrentQueue<t_ElementType, NUM_ELEMENTS, true>, TicketType::BATCH_1000>();

	RunTestsOnQueueType<t_ElementType, NCPS::ConcurrentQueue<t_ElementType, 8192, true>, TicketType::EPHEMERAL>();
	RunTestsOnQueueType<t_ElementType, NCPS::ConcurrentQueue<t_ElementType, NUM_ELEMENTS, true>, TicketType::EPHEMERAL>();
	RunTestsOnQueueType<t_ElementType, NCPS::ConcurrentQueue<t_ElementType, 8192, false>, TicketType::EPHEMERAL>();
	RunTestsOnQueueType<t_ElementType, NCPS::ConcurrentQueue<t_ElementType, NUM_ELEMENTS, false>, TicketType::EPHEMERAL>();

	RunTestsOnQueueType<t_ElementType, NCPS::ConcurrentQueue<t_ElementType, 8192, true>, TicketType::NONE>();
	RunTestsOnQueueType<t_ElementType, NCPS::ConcurrentQueue<t_ElementType, NUM_ELEMENTS, true>, TicketType::NONE>();
	RunTestsOnQueueType<t_ElementType, NCPS::ConcurrentQueue<t_ElementType, 8192, false>, TicketType::NONE>();
	RunTestsOnQueueType<t_ElementType, NCPS::ConcurrentQueue<t_ElementType, NUM_ELEMENTS, false>, TicketType::NONE>();

	RunTestsOnQueueType<t_ElementType, NCPS::ConcurrentBoundedQueue<t_ElementType, NUM_ELEMENTS>>();
	RunTestsOnQueueType<t_ElementType, NCPS::ConcurrentBoundedQueue<t_ElementType, NUM_ELEMENTS>, TicketType::NONE>();
}

template<size_t t_Size>
class FixedStaticString
{
public:
	FixedStaticString(){}
	FixedStaticString(int _unused){}

	FixedStaticString(FixedStaticString const& other)
	{
		memcpy(m_str, other.m_str, t_Size);
	}

	FixedStaticString& operator=(FixedStaticString const& other)
	{
		memcpy(m_str, other.m_str, t_Size);
		return *this;
	}
private:
	char m_str[t_Size];
};

int main()
{
	std::cout << std::fixed;
#ifdef VERIFY
	RunTestsOnElementType<int>();
#else
	RunTestsOnElementType<char>();
	RunTestsOnElementType<int64_t>();
	RunTestsOnElementType<FixedStaticString<64>, false>();
#endif
}

