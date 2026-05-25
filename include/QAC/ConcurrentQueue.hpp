/*
 * MIT License
 *
 * Copyright (c) 2016-2026 Kitty Draper
 *
 * Permission is hereby granted, free of charge, to any person obtaining a copy
 * of this software and associated documentation files (the "Software"), to deal
 * in the Software without restriction, including without limitation the rights
 * to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
 * copies of the Software, and to permit persons to whom the Software is
 * furnished to do so, subject to the following conditions:
 *
 * The above copyright notice and this permission notice shall be included in all
 * copies or substantial portions of the Software.
 *
 * THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
 * IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
 * FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
 * AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
 * LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
 * OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
 * SOFTWARE.
 */

/*
 * Reference implementation and public library in C++ for the Quick And Curious Concurrent Queue
 */

#pragma once
#include <atomic>
#include <memory>
#include <string.h>

#include <limits>

#include <type_traits>
#include <stdexcept>
#include <semaphore>

#if defined(_WIN32)
#    include <BaseTsd.h>
#endif

#if defined(_MSC_VER) && !defined(__clang__)
#    define QAC_FORCE_NO_INLINE __declspec(noinline)
#    define QAC_FORCE_INLINE __forceinline
#elif defined(__INTEL_COMPILER_BUILD_DATE) || defined(__clang__) || defined(__GNUC__)
#    define QAC_FORCE_NO_INLINE __attribute__((noinline))
#    define QAC_FORCE_INLINE __attribute__((always_inline)) inline
#endif

#ifndef QAC_CACHELINE_SIZE
#    define QAC_CACHELINE_SIZE 128
#endif

#if defined(__aarch64__) || defined(_M_ARM64)
#include <arm_acle.h>
QAC_FORCE_INLINE void QAC_YIELD()
{
#ifdef _WIN32
	__dmb(_ARM_BARRIER_ISHST);
	__yield();
#else
	asm volatile("dmb ishst" ::: "memory");
	asm volatile("yield");
#endif
}
#else
#	include <immintrin.h>
#	define QAC_YIELD _mm_pause
#endif

#define QAC_CONCAT_2(left, right) left##right
#define QAC_CONCAT(left, right) QAC_CONCAT_2(left, right)

#define QAC_ABORT_MSG_F(msg, ...)       \
    fprintf(stderr, msg, ##__VA_ARGS__); \
    fputs("\n", stderr);                 \
    fflush(stderr);                      \
    std::terminate();

#ifndef QAC_CONCURRENT_QUEUE_DEBUG_ASSERTS
#    define QAC_CONCURRENT_QUEUE_DEBUG_ASSERTS 0
#endif

#if QAC_CONCURRENT_QUEUE_DEBUG_ASSERTS
#    define QAC_CONCURRENT_QUEUE_ASSERT(val)               \
        if (!(val)) {                                       \
            QAC_ABORT_MSG_F("Assertion failed: %s", #val); \
        }
#else
#    define QAC_CONCURRENT_QUEUE_ASSERT(val)
#endif

#if 1
#ifdef _WIN32
#define WIN32_LEAN_AND_MEAN
#define NOMINMAX
#include <windows.h>
#define QAC_DEBUG(msg, ...) printf("[TID %d] " msg "\n", GetCurrentThreadId(), __VA_ARGS__)
#else
#include <pthread.h>
#define QAC_DEBUG(msg, ...) printf("[TID %zd] " msg "\n", pthread_self(), __VA_ARGS__)
#endif
#else
#define QAC_DEBUG(...)
#endif

#ifndef QAC_DEFAULT_SPIN_COUNT
#	define QAC_DEFAULT_SPIN_COUNT 1000
#endif

namespace QAC
{
#if defined(_WIN32)
	using ssize_t = SSIZE_T;
#endif
	namespace detail
	{
		template <typename t_ElementType, size_t t_BlockSize, bool t_EnableBatch, bool t_EnableIdleSleep>
		class Buffer;

		template <typename t_ElementType, template<typename> typename t_AllocatorType>
		class ReservationTicketSubQueue;

		template<typename t_ElementType, bool t_EnableBatch, bool t_WithSemaphore>
		struct BufferElementImpl;

		template<typename t_ElementType, bool t_WithSemaphore>
		struct UnbatchedBufferElementImpl;

		template<typename t_ElementType, bool t_WithSemaphore>
		struct BoundedBufferElementImpl;

		// These functions collectively find the next power of 2 of a number
		// Which allows modulus using the faster & rather than %.
		constexpr uint32_t pow2_16(uint32_t const x) { return (x | x >> 16) + 1; }
		constexpr uint32_t pow2_8(uint32_t const x) { return pow2_16(x | x >> 8); }
		constexpr uint32_t pow2_4(uint32_t const x) { return pow2_8(x | x >> 4); }
		constexpr uint32_t pow2_2(uint32_t const x) { return pow2_4(x | x >> 2); }
		constexpr uint32_t pow2_1(uint32_t const x) { return pow2_2(x | x >> 1); }

		constexpr uint64_t pow2_32(uint64_t const x) { return (x | x >> 32) + 1; }
		constexpr uint64_t pow2_16(uint64_t const x) { return pow2_32(x | x >> 16); }
		constexpr uint64_t pow2_8(uint64_t const x) { return pow2_16(x | x >> 8); }
		constexpr uint64_t pow2_4(uint64_t const x) { return pow2_8(x | x >> 4); }
		constexpr uint64_t pow2_2(uint64_t const x) { return pow2_4(x | x >> 2); }
		constexpr uint64_t pow2_1(uint64_t const x) { return pow2_2(x | x >> 1); }

		constexpr int64_t log2(int64_t val)
		{
			if(val != 0)
			{
				return log2(val >> 1) + 1;
			}
			return -1;
		}

		template <typename t_IntegerType>
		constexpr t_IntegerType nextPowerOf2(t_IntegerType const x, typename std::enable_if<sizeof(t_IntegerType) == 8>::type* = nullptr)
		{
			return pow2_1(uint64_t(x - 1));
		}

		template <typename t_IntegerType>
		constexpr t_IntegerType nextPowerOf2(t_IntegerType const x, typename std::enable_if<sizeof(t_IntegerType) == 4>::type* = nullptr)
		{
			return pow2_1(uint32_t(x - 1));
		}

		static_assert(nextPowerOf2(uint64_t(1)) == 1, "nextPowerOf2 failed");
		static_assert(nextPowerOf2(uint64_t(2)) == 2, "nextPowerOf2 failed");
		static_assert(nextPowerOf2(uint64_t(3)) == 4, "nextPowerOf2 failed");
		static_assert(nextPowerOf2(uint64_t(4)) == 4, "nextPowerOf2 failed");
		static_assert(nextPowerOf2(uint64_t(5)) == 8, "nextPowerOf2 failed");
		static_assert(nextPowerOf2(uint64_t(9)) == 16, "nextPowerOf2 failed");
		static_assert(nextPowerOf2(uint64_t(17)) == 32, "nextPowerOf2 failed");
		static_assert(nextPowerOf2(uint64_t(1025)) == 2048, "nextPowerOf2 failed");
		static_assert(nextPowerOf2(uint64_t(32000)) == 32768, "nextPowerOf2 failed");

		static_assert(nextPowerOf2(uint32_t(1)) == 1, "nextPowerOf2 failed");
		static_assert(nextPowerOf2(uint32_t(2)) == 2, "nextPowerOf2 failed");
		static_assert(nextPowerOf2(uint32_t(3)) == 4, "nextPowerOf2 failed");
		static_assert(nextPowerOf2(uint32_t(4)) == 4, "nextPowerOf2 failed");
		static_assert(nextPowerOf2(uint32_t(5)) == 8, "nextPowerOf2 failed");
		static_assert(nextPowerOf2(uint32_t(9)) == 16, "nextPowerOf2 failed");
		static_assert(nextPowerOf2(uint32_t(17)) == 32, "nextPowerOf2 failed");
		static_assert(nextPowerOf2(uint32_t(1025)) == 2048, "nextPowerOf2 failed");
		static_assert(nextPowerOf2(uint32_t(32000)) == 32768, "nextPowerOf2 failed");
	}  // namespace detail

	template <typename t_ElementType, size_t t_BlockSize = 8192, bool t_EnableBatch = false, bool t_EnableIdleSleep = false, template<typename> typename t_AllocatorType = std::allocator>
	struct ReadReservationTicket;

	template <typename t_ElementType>
	struct BoundedReadReservationTicket;

	template <typename t_ElementType>
	struct BoundedWriteReservationTicket;

	
	
	template <typename t_ElementType, size_t t_BlockSize = 16384, bool t_EnableBatch = false, bool t_EnableIdleSleep = false, template<typename> typename t_AllocatorType = std::allocator>
	class ConcurrentQueue;

	template<typename t_ElementType, size_t t_BlockSize = 16384, template<typename> typename t_AllocatorType = std::allocator>
	using BatchableConcurrentQueue = ConcurrentQueue<t_ElementType, t_BlockSize, true, false, t_AllocatorType>;

	template<typename t_ElementType, size_t t_BlockSize = 16384, template<typename> typename t_AllocatorType = std::allocator>
	using IdleSleepingConcurrentQueue = ConcurrentQueue<t_ElementType, t_BlockSize, false, true, t_AllocatorType>;

	template<typename t_ElementType, size_t t_BlockSize = 16384, template<typename> typename t_AllocatorType = std::allocator>
	using BatchableIdleSleepingConcurrentQueue = ConcurrentQueue<t_ElementType, t_BlockSize, true, true, t_AllocatorType>;



	template <typename t_ElementType, size_t t_QueueSize = 131072, bool t_EnableBatch = false, bool t_EnableIdleSleep = false, template<typename> typename t_AllocatorType = std::allocator>
	class ConcurrentBoundedQueue;

	template <typename t_ElementType, size_t t_QueueSize = 131072, template<typename> typename t_AllocatorType = std::allocator>
	using BatchableConcurrentBoundedQueue = ConcurrentBoundedQueue<t_ElementType, t_QueueSize, true, false, t_AllocatorType>;

	template <typename t_ElementType, size_t t_QueueSize = 131072, template<typename> typename t_AllocatorType = std::allocator>
	using IdleSleepingConcurrentBoundedQueue = ConcurrentBoundedQueue<t_ElementType, t_QueueSize, false, true, t_AllocatorType>;

	template <typename t_ElementType, size_t t_QueueSize = 131072, template<typename> typename t_AllocatorType = std::allocator>
	using BatchableIdleSleepingConcurrentBoundedQueue = ConcurrentBoundedQueue<t_ElementType, t_QueueSize, true, true, t_AllocatorType>;

}  // namespace QAC


template<typename t_ElementType, bool t_EnableBatch, bool t_WithSemaphore>
struct QAC::detail::BufferElementImpl
{
	typedef std::binary_semaphore* NotifierType;

	static constexpr intptr_t READY_SENTINEL = 1;
	static constexpr intptr_t FREE_SENTINEL = 0;

	t_ElementType* item;
	std::atomic<std::binary_semaphore*>* notifier;

	QAC_FORCE_INLINE BufferElementImpl& operator++()
	{
		++item;
		++notifier;
		return *this;
	}

	ptrdiff_t operator-(BufferElementImpl other)
	{
		return item - other.item;
	}
	bool operator>(BufferElementImpl other)
	{
		return item > other.item;
	}
	bool operator>=(BufferElementImpl other)
	{
		return item >= other.item;
	}
	bool operator<(BufferElementImpl other)
	{
		return item < other.item;
	}
	bool operator<=(BufferElementImpl other)
	{
		return item <= other.item;
	}
	void operator=(BufferElementImpl const& other)
	{
		item = other.item;
		notifier = other.notifier;
	}
};

template<typename t_ElementType>
struct QAC::detail::BufferElementImpl<t_ElementType, true, false>
{
	typedef bool NotifierType;

	static constexpr bool READY_SENTINEL = true;
	static constexpr bool FREE_SENTINEL = false;

	t_ElementType* item;
	std::atomic<bool>* notifier;

	QAC_FORCE_INLINE BufferElementImpl& operator++()
	{
		++item;
		++notifier;
		return *this;
	}
	ptrdiff_t operator-(BufferElementImpl other)
	{
		return item - other.item;
	}
	bool operator>(BufferElementImpl other)
	{
		return item > other.item;
	}
	bool operator>=(BufferElementImpl other)
	{
		return item >= other.item;
	}
	bool operator<(BufferElementImpl other)
	{
		return item < other.item;
	}
	bool operator<=(BufferElementImpl other)
	{
		return item <= other.item;
	}
	void operator=(BufferElementImpl const& other)
	{
		item = other.item;
		notifier = other.notifier;
	}
};
template<typename t_ElementType, bool t_WithSemaphore>
struct QAC::detail::UnbatchedBufferElementImpl
{
	typedef std::binary_semaphore* NotifierType;

	static constexpr intptr_t READY_SENTINEL = 1;
	static constexpr intptr_t FREE_SENTINEL = 0;

	t_ElementType item;
	std::atomic<std::binary_semaphore*> notifier;
};

template<typename t_ElementType>
struct QAC::detail::UnbatchedBufferElementImpl<t_ElementType, false>
{
	typedef bool NotifierType;

	static constexpr bool READY_SENTINEL = true;
	static constexpr bool FREE_SENTINEL = false;

	t_ElementType item;
	std::atomic<bool> notifier;
};

template<typename t_ElementType>
struct QAC::detail::BufferElementImpl<t_ElementType, false, true>
{
	typedef std::binary_semaphore* NotifierType;

	static constexpr intptr_t READY_SENTINEL = 1;
	static constexpr intptr_t FREE_SENTINEL = 0;

	UnbatchedBufferElementImpl<t_ElementType, true>* element;
	t_ElementType* item;
	std::atomic<std::binary_semaphore*>* notifier;

	QAC_FORCE_INLINE BufferElementImpl& operator++()
	{
		++element;
		item = &element->item;
		notifier = &element->notifier;
		return *this;
	}

	ptrdiff_t operator-(BufferElementImpl other)
	{
		return element - other.element;
	}
	bool operator>(BufferElementImpl other)
	{
		return element > other.element;
	}
	bool operator>=(BufferElementImpl other)
	{
		return element >= other.element;
	}
	bool operator<(BufferElementImpl other)
	{
		return element < other.element;
	}
	bool operator<=(BufferElementImpl other)
	{
		return element <= other.element;
	}
	void operator=(BufferElementImpl const& other)
	{
		element = other.element;
		item = other.item;
		notifier = other.notifier;
	}
};

template<typename t_ElementType>
struct QAC::detail::BufferElementImpl<t_ElementType, false, false>
{
	typedef bool NotifierType;

	static constexpr bool READY_SENTINEL = true;
	static constexpr bool FREE_SENTINEL = false;

	UnbatchedBufferElementImpl<t_ElementType, false>* element;
	t_ElementType* item;
	std::atomic<bool>* notifier;

	QAC_FORCE_INLINE BufferElementImpl& operator++()
	{
		++element;
		item = &element->item;
		notifier = &element->notifier;
		return *this;
	}

	ptrdiff_t operator-(BufferElementImpl other)
	{
		return element - other.element;
	}
	bool operator>(BufferElementImpl other)
	{
		return element > other.element;
	}
	bool operator>=(BufferElementImpl other)
	{
		return element >= other.element;
	}
	bool operator<(BufferElementImpl other)
	{
		return element < other.element;
	}
	bool operator<=(BufferElementImpl other)
	{
		return element <= other.element;
	}
	void operator=(BufferElementImpl const& other)
	{
		element = other.element;
		item = other.item;
		notifier = other.notifier;
	}
};

template<typename t_ElementType, bool t_WithSemaphore>
struct QAC::detail::BoundedBufferElementImpl
{
	static constexpr intptr_t READY_SENTINEL = 1;

	std::atomic<std::binary_semaphore*> notifier{ nullptr };
	std::atomic<int64_t> generation{ 0 };
	t_ElementType item;
};

template<typename t_ElementType>
struct QAC::detail::BoundedBufferElementImpl<t_ElementType, false>
{
	std::atomic<int64_t> generation{ 0 };
	t_ElementType item;
};

/**
 * @class   QAC::detail::Buffer
 *
 * @brief   Simple buffer class representing a single allocated block within an unbounded concurrent queue.
 *
 * @details Provides concurrent read and write support. This class is the one that actually handles
 *          the majority of the atomic operations, as the read and write position are both
 *          contained within this class.
 */
template <typename t_ElementType, size_t t_BlockSize, bool t_EnableBatch, bool t_EnableIdleSleep>
class alignas(QAC_CACHELINE_SIZE) QAC::detail::Buffer
{
public:

	using BufferElement = QAC::detail::BufferElementImpl<t_ElementType, t_EnableBatch, t_EnableIdleSleep>;
	using UnbatchedBufferElement = QAC::detail::UnbatchedBufferElementImpl<t_ElementType, t_EnableIdleSleep>;

	Buffer()
		: m_next(nullptr),
		m_refCount(t_BlockSize + 2),  // One for each element, one for the writeBuffer pointer, and one for the readBuffer pointer
		m_readPos(reinterpret_cast<t_ElementType*>(m_buffer.elements)),
		m_writePos(reinterpret_cast<t_ElementType*>(m_buffer.elements)),
		m_readPosUnbatched(reinterpret_cast<UnbatchedBufferElement*>(m_buffer.unbatchedBuffer)),
		m_writePosUnbatched(reinterpret_cast<UnbatchedBufferElement*>(m_buffer.unbatchedBuffer)),
		m_end(reinterpret_cast<t_ElementType*>(m_buffer.elements) + t_BlockSize),
		m_endUnbatched(reinterpret_cast<UnbatchedBufferElement*>(m_buffer.unbatchedBuffer) + t_BlockSize)
	{
		// Memset the buffer block to 0 so all 'ready' flags read as 'false'
		if constexpr (t_EnableBatch)
		{
			memset(reinterpret_cast<void*>(m_buffer.elements), 0, sizeof(t_ElementType) * t_BlockSize);
			memset(reinterpret_cast<void*>(m_buffer.notifiers), 0, sizeof(std::atomic<typename BufferElement::NotifierType>) * t_BlockSize);
		}
		else
		{
			memset(reinterpret_cast<void*>(m_buffer.unbatchedBuffer), 0, sizeof(UnbatchedBufferElement) * t_BlockSize);
		}
	}

	/**
	 * @brief   Reset a buffer back to its original state.
	 *          Does NOT reset the read and write positions, those are done by the functions below.
	 *
	 * @details The way this works is like this:
	 *          When a buffer has been completely used up, rather than freeing it, it's marked for reuse later.
	 *          The reason for this is that freeing it isn't safe - it may still be accessed after or while it's
	 *          being freed. Instead, this algorithm takes used blocks and moves them to the end of the block list
	 *          to be used again later. When we start to write it again, we set the write position back to the start,
	 *          and likewise, when we start to read it again, we set the read position back to the start.
	 *
	 *          This is safe even though it may be read again because the read and write positions aren't set.
	 *          When the read and write positions are obtained, one of two results can occur:
	 *          1) It will get a value that's past the end of the buffer and go to retrieve (or allocate) the next buffer
	 *          2) It will read it while or after the write/read position is reset, in which case this buffer is already ready
	 *          for use again and it gets a valid item that it's absolutely permitted to continue operating on.
	 *
	 *          Either of these situations is fine, meaning that using this queue after it's been put on the back is never
	 *          a problem.
	 */
	inline void Clear()
	{
		m_refCount.store(t_BlockSize + 2);
		if constexpr (t_EnableBatch)
		{
			memset(reinterpret_cast<void*>(m_buffer.elements), 0, sizeof(t_ElementType) * t_BlockSize);
			memset(reinterpret_cast<void*>(m_buffer.notifiers), 0, sizeof(std::atomic<typename BufferElement::NotifierType>) * t_BlockSize);
		}
		else
		{
			memset(reinterpret_cast<void*>(m_buffer.unbatchedBuffer), 0, sizeof(UnbatchedBufferElement) * t_BlockSize);
		}
	}

	/**
	 * @brief   Resets the write position
	 */
	inline void SetWritePosition() 
	{
		if constexpr (t_EnableBatch)
		{
			m_writePos.store(reinterpret_cast<t_ElementType*>(m_buffer.elements));
		}
		else
		{
			m_writePosUnbatched.store(reinterpret_cast<UnbatchedBufferElement*>(m_buffer.unbatchedBuffer));
		}
	}

	/**
	 * @brief   Resets the read position
	 */
	inline void SetReadPosition() 
	{
		if constexpr (t_EnableBatch)
		{
			m_readPos.store(reinterpret_cast<t_ElementType*>(m_buffer.elements));
		}
		else
		{
			m_readPosUnbatched.store(reinterpret_cast<UnbatchedBufferElement*>(m_buffer.unbatchedBuffer));
		}
	}

	/**
	 * @brief   Set the next pointer for this buffer.
	 *
	 * @details The caller (the enclosing queue) is responsible for detecting when
	 *          the buffer element it's received is outside the bounds of the buffer,
	 *          allocating a new buffer in a synchronized way, and then setting the next
	 *          pointer on the current buffer. This burden is placed on the caller for
	 *          performance reasons.
	 *
	 * @param   next   The pointer to a newly allocated buffer
	 */
	inline void SetNext(Buffer* next) 
	{ 
		m_next.store(next, std::memory_order_release); 
	}

	/**
	 * @brief   Get the next pointer for this buffer.
	 *
	 * @details Like with SetNext, the caller is responsible for detecting when the element
	 *          they received is outside the boundaries of the buffer and retrieving the next buffer.
	 *
	 * @return  Pointer to the next buffer. If there is no next, returns nullptr.
	 */
	inline Buffer* GetNext() 
	{ 
		return m_next.load(std::memory_order_acquire); 
	}

	/**
	 * @brief   Retrieve a pointer to an element for pop.
	 *
	 * @details This function is thread-safe and is guaranteed to return an element reserved
	 *          for only the caller. There's no need to synchronize access to this element.
	 *          However, this element is NOT guaranteed to actually have valid data stored in it yet.
	 *          It's the responsibility of the caller to check the 'ready' flag on the element and
	 *          to handle the case where it's not yet ready. Also, the buffer does not support
	 *          putting an element back in the read queue - once an element is retrieved for read,
	 *          it must be read as retrieved, as that element will never be returned from this
	 *          method again.
	 *
	 *          Additionally, note that the returned pointer may be beyond the end of the buffer,
	 *          and it is the responsibility of the caller to handle that case by retrieving the next
	 *          buffer.
	 *
	 * @return  A pointer to an element. If the pointer is < this->GetEnd(), it is valid to read from.
	 */
	inline BufferElement GetForRead()
	{
		if constexpr (t_EnableBatch)
		{
			t_ElementType* element = m_readPos.fetch_add(1, std::memory_order_acq_rel);
			std::atomic<typename BufferElement::NotifierType>* notifier = reinterpret_cast<std::atomic<typename BufferElement::NotifierType>*>(m_buffer.notifiers) + (element - GetStart().item);
			return { element, notifier };
		}
		else
		{
			UnbatchedBufferElement* element = m_readPosUnbatched.fetch_add(1, std::memory_order_acq_rel);
			return { element, &element->item, &element->notifier };
		}
	}

	inline BufferElement GetBatchForRead(ssize_t count)
	{
		if constexpr (t_EnableBatch)
		{
			t_ElementType* element = m_readPos.fetch_add(count, std::memory_order_acq_rel);
			std::atomic<typename BufferElement::NotifierType>* notifier = reinterpret_cast<std::atomic<typename BufferElement::NotifierType>*>(m_buffer.notifiers) + (element - GetStart().item);
			return { element, notifier };
		}
		else
		{
			UnbatchedBufferElement* element = m_readPosUnbatched.fetch_add(count, std::memory_order_acq_rel);
			return { element, &element->item, &element->notifier };
		}
	}

	/**
	 * @brief   Retrieve a pointer to an element for push.
	 *
	 * @details This function is thread-safe and is guaranteed to return an element reserved
	 *          for only the caller. There's no need to synchronize access to this element.
	 *          Note, however, that the returned pointer may be beyond the end of the buffer,
	 *          and it is the responsibility of the caller to handle that case by allocating a new
	 *          buffer.
	 *
	 * @return  A pointer to an element. If the pointer is < this->GetEnd(), it is valid to write to.
	 */
	inline BufferElement GetForWrite()
	{
		if constexpr (t_EnableBatch)
		{
			t_ElementType* element = m_writePos.fetch_add(1, std::memory_order_acq_rel);
			std::atomic<typename BufferElement::NotifierType>* notifier = reinterpret_cast<std::atomic<typename BufferElement::NotifierType>*>(m_buffer.notifiers) + (element - GetStart().item);
			return { element, notifier };
		}
		else
		{
			UnbatchedBufferElement* element = m_writePosUnbatched.fetch_add(1, std::memory_order_acq_rel);
			return { element, &element->item, &element->notifier };
		}
	}

	inline BufferElement GetBatchForWrite(ssize_t count)
	{
		if constexpr (t_EnableBatch)
		{
			t_ElementType* element = m_writePos.fetch_add(count, std::memory_order_acq_rel);
			std::atomic<typename BufferElement::NotifierType>* notifier = reinterpret_cast<std::atomic<typename BufferElement::NotifierType>*>(m_buffer.notifiers) + (element - GetStart().item);
			return { element, notifier };
		}
		else
		{
			UnbatchedBufferElement* element = m_writePosUnbatched.fetch_add(count, std::memory_order_acq_rel);
			return { element, &element->item, &element->notifier };
		}
	}

	/**
	 * @brief   Get a pointer to the end of the queue. If a returned pointer is >= this value, it's not valid,
	 *          and a reallocation or call to GetNext() is required.
	 *
	 * @return  A pointer to the end of the buffer.
	 */
	inline BufferElement const GetEnd() const
	{
		if constexpr (t_EnableBatch)
		{
			return { m_end, nullptr };
		}
		else
		{
			return { m_endUnbatched, nullptr, nullptr };
		}
	}

	/**
	 * @brief   Get a pointer to the start of the queue. Used along with Generation to calculate the absolute
	 * position of an element in the queue, which is used to order themm within the priority subqueue.
	 *
	 * @return  A pointer to the start of the buffer.
	*/
	inline BufferElement const GetStart()
	{
		if constexpr (t_EnableBatch)
		{
			return { reinterpret_cast<t_ElementType*>(m_buffer.elements), nullptr };
		}
		else
		{
			return { reinterpret_cast<UnbatchedBufferElement*>(m_buffer.unbatchedBuffer), nullptr };
		}
	}

	/**
	 * @brief   Decrement the ref count.
	 *
	 * @details This isn't a traditional reference count. Rather than dealing in terms of the number of current references,
	 *          this actually indicates the number of unread elements, plus 2 additional references for the writeBuffer and
	 *          readBuffer elements of the queue. Once all elements have been read and those two pointers are pointing at
	 *          something else, we know nothing else is pointing at this and it's safe to move it to the end of the buffer list -
	 *          therefore we don't have to worry about incrementing the reference count ever.
	 *
	 * @return  The new reference count after this operation has completed. If the result is 0, the buffer should be moved to the end of the buffer list.
	 */
	inline ssize_t DecRef()
	{
		return m_refCount.fetch_sub(1, std::memory_order_acq_rel) - 1;
	}

	/**
	 * @brief   Special version of DecRef that will decrease the reference count multiple times with a single atomic operation
	 *
	 * @param   amount   the amount by which to decrement the count
	 * @return  The new reference count after this operation has completed. If the result is 0, the buffer should be moved to the end of the buffer list.
	 */
	inline ssize_t DecRef(ssize_t amount)
	{
		return m_refCount.fetch_sub(amount, std::memory_order_acq_rel) - amount;
	}

	/**
	 * @brief   Clean up the buffer. This is NOT thread-safe.
	 */
	void Cleanup()
	{
		BufferElement element = this->GetForRead();
		while(element.item < m_end && element.notifier->load(std::memory_order_relaxed) == (typename Buffer::BufferElement::NotifierType)(Buffer::BufferElement::READY_SENTINEL))
		{
			element.item->~t_ElementType();
			element = this->GetForRead();
		}
	}

	int64_t GetGeneration()
	{
		return m_generation;
	}

	void SetGeneration(int64_t generation)
	{
		m_generation = generation;
	}

private:
	alignas(QAC_CACHELINE_SIZE) std::atomic<Buffer*> m_next;
	alignas(QAC_CACHELINE_SIZE) std::atomic<ssize_t> m_refCount;
	alignas(QAC_CACHELINE_SIZE) std::atomic<t_ElementType*> m_readPos;
	alignas(QAC_CACHELINE_SIZE) std::atomic<t_ElementType*> m_writePos;
	alignas(QAC_CACHELINE_SIZE) std::atomic<UnbatchedBufferElement*> m_readPosUnbatched;
	alignas(QAC_CACHELINE_SIZE) std::atomic<UnbatchedBufferElement*> m_writePosUnbatched;
	alignas(QAC_CACHELINE_SIZE) int64_t m_generation{ 0 };

	// Separate memory layouts for batched vs. unbatched operations.
	// Batched operations benefit from elements being contiguous without notifiers interleaving
	// because that allows batch push to be performed using a memcpy for trivially copyable types.
	// Unbatched operations benefit from elements and their notifiers being colocated in memory.
	union
	{
		char unbatchedBuffer[t_BlockSize * sizeof(UnbatchedBufferElement)];
		struct
		{
			char elements[t_BlockSize * sizeof(t_ElementType)];
			char notifiers[t_BlockSize * sizeof(std::atomic<typename BufferElement::NotifierType>)];
		};
	} m_buffer;
	t_ElementType* const m_end;
	UnbatchedBufferElement* const m_endUnbatched;
};

/**
 * @class   QAC::ReadReservationTicket
 *
 * @brief   Represents a reservation to read an element that hasn't been written to yet.
 *
 * @warning You must call queue.InitializeReservationTicket() on this before using it!
 */
template <typename t_ElementType, size_t t_BlockSize, bool t_EnableBatch, bool t_EnableIdleSleep, template<typename> typename t_AllocatorType>
struct QAC::ReadReservationTicket
{
	detail::Buffer<t_ElementType, t_BlockSize, t_EnableBatch, t_EnableIdleSleep>* buffer{ nullptr };
	typename detail::Buffer<t_ElementType, t_BlockSize, t_EnableBatch, t_EnableIdleSleep>::BufferElement ptr{ nullptr, nullptr };
	QAC::ConcurrentQueue<t_ElementType, t_BlockSize, t_EnableBatch, t_EnableIdleSleep, t_AllocatorType>* queue{ nullptr };

	ReadReservationTicket()
	{}

	ReadReservationTicket(ReadReservationTicket const& other) = delete;
	ReadReservationTicket& operator=(ReadReservationTicket const& other) = delete;

	ReadReservationTicket(ReadReservationTicket&& other) noexcept 
		: buffer(other.buffer)
		, ptr(other.ptr)
		, queue(other.queue)
	{
		other.buffer = nullptr;
		other.ptr = nullptr;
	}
	ReadReservationTicket& operator=(ReadReservationTicket&& other) noexcept
	{
		buffer = other.buffer;
		ptr = other.ptr;
		queue = other.queue;
		other.buffer = nullptr;
		other.ptr = { nullptr, nullptr };
		return *this;
	}
};

template <typename t_ElementType, template<typename> typename t_AllocatorType>
class alignas(QAC_CACHELINE_SIZE) QAC::detail::ReservationTicketSubQueue
{
private:
	enum class State
	{
		Free,
		Pending,
		Ready,
		Clearing
	};
	struct Element
	{
		std::atomic<State> state;
		size_t pos;
		t_ElementType data;
	};

public:
	ReservationTicketSubQueue(size_t const maxConcurrentTicketlessReads)
		: m_buffer(maxConcurrentTicketlessReads == 0 ? nullptr : m_allocator.allocate(maxConcurrentTicketlessReads))
		, m_capacity(maxConcurrentTicketlessReads)
	{
		if (m_buffer)
		{
			memset(reinterpret_cast<void*>(m_buffer), 0, maxConcurrentTicketlessReads * sizeof(*m_buffer));
		}
	}

	void Push(t_ElementType& element, size_t pos)
	{
		Element* internalElement = GetFree();
		internalElement->pos = pos;
		internalElement->data = std::move(element);
		internalElement->state.store(State::Ready, std::memory_order_release);
		m_count.fetch_add(1, std::memory_order_release);
	}

	bool TryPop(t_ElementType& result)
	{
		if (m_count.load(std::memory_order_acquire) == 0)
		{
			return false;
		}
		Element* element = RemoveFirst();
		if (element == nullptr)
		{
			return false;
		}
		result = std::move(element->data);
		element->state.store(State::Free, std::memory_order_release);
		m_count.fetch_sub(1, std::memory_order_release);
		return true;
	}
private:
	Element* RemoveFirst()
	{
		for (;;)
		{
			Element* low = nullptr;
			for (size_t i = 0; i < m_capacity; ++i)
			{
				if (m_buffer[i].state.load(std::memory_order_acquire) == State::Ready && (low == nullptr || m_buffer[i].pos < low->pos))
				{
					low = m_buffer + i;
				}
			}
			if (low == nullptr)
			{
				return nullptr;
			}
			State desiredState = State::Ready;
			if (low->state.compare_exchange_strong(desiredState, State::Clearing, std::memory_order_acq_rel))
			{
				return low;
			}
		}
	}

	Element* GetFree()
	{
		for (size_t i = 0; i < m_capacity; ++i)
		{
			State desiredState = State::Free;
			if (m_buffer[i].state.compare_exchange_strong(desiredState, State::Pending, std::memory_order_acq_rel))
			{
				return m_buffer + i;
			}
		}
		// should not be possible if max concurrent is not exceeded
		return nullptr;
	}

	void Free(Element* element)
	{
		element->inUse.store(false, std::memory_order_release);
	}

	t_AllocatorType<Element> m_allocator;

	alignas(QAC_CACHELINE_SIZE) std::atomic<int> m_count{ 0 };
	alignas(QAC_CACHELINE_SIZE) size_t const m_capacity;
	Element* m_buffer;
};

/**
 * class    QAC::ConcurrentQueue
 *
 * @brief   Concurrent queue, supporting multi-consumer, multi-producer access
 *          from multiple threads with no synchronization required. Unbounded, capable of
 *          resizing itself when it's out of space.
 *
 * @details Strictly speaking, this is not a lock-free queue. When it needs to allocate,
 *          it does acquire a spin lock. It also does this when it needs to fetch a new
 *          read queue because the current one is exhausted.
 *
 *          However, while it's not STRICTLY speaking lock-free, PRACTICALLY speaking,
 *          it's wait-free population agnostic for the vast majority of pushes and pops.
 *          So long as the reservation ticket used for pops is kept alive, this queue is extremely fast.
 *          Be warned, however, that if you don't keep the reservation ticket alive, the queue will still work,
 *          but pops will be somewhat slower - while the ticket stays alive, it batches reference counting
 *          operations, but each time the reservation ticket destructs it has to apply those reference count changes.
 *          Which means if it destructs after every pop, there's an atomic fetch_sub that will happen after each
 *          queue. It sounds like it's not a big deal, but removing one fetch_sub operation from each pop
 *          can have a surprisingly large performance impact.
 *
 *          Note, though, that the reservation tickets MUST BE KEPT ALIVE if pop returns false, or an element
 *          in the queue will become unreachable and will never be read, and memory for the buffer containing it
 *          will not be able to be reused and will cause a memory leak.
 *
 * @tparam  t_ElementType       the type of element to store in the queue
 *
 * @tparam  t_BlockSize         the number of elements to allocate at a time.
 *                              Generally speaking, most queues will end up seeing double this number in use,
 *                              assuming it's reasonably large and push operations don't outpace pop operations.
 *                              Once the first block is used up a new one will be allocated and the first will be reused
 *                              if it's empty, rather than being freed, hence seeing double this number in memory usage after
 *                              the initial t_BlockSize reads have been completed.
 *
 * @tparam   t_EnableBatch      When batch operations are supported, non-batch operations have to do a little extra work to play
 *                              nicely with them. If you're not using batch operations, you can gain a performance improvement
 *                              by setting this parameter to false.
 *
 * @tparam   t_AllocatorType    An allocator class compatible with std::allocator. Does not actually allocate individual elements;
 *                              rather, allocates blocks of type detail::Buffer<t_Element, t_BlockSize>, hence this class
 *                              must support `rebind`. For ticket-free pop operations, ReadReservationTickets will also
 *                              be allocated after failed reads, and deallocated on subsequent successful reads.
 */
template <typename t_ElementType, size_t t_BlockSize, bool t_EnableBatch, bool t_EnableIdleSleep, template<typename> typename t_AllocatorType>
class alignas(QAC_CACHELINE_SIZE) QAC::ConcurrentQueue
{
public:
	using ReadReservationTicket = QAC::ReadReservationTicket<t_ElementType, t_BlockSize, t_EnableBatch, t_EnableIdleSleep, t_AllocatorType>;
	using Buffer = QAC::detail::Buffer<t_ElementType, t_BlockSize, t_EnableBatch, t_EnableIdleSleep>;

	friend struct QAC::ReadReservationTicket<t_ElementType, t_BlockSize, t_EnableBatch, t_EnableIdleSleep, t_AllocatorType>;

protected:
	/**
	 * @brief   Decrement the ref count on the buffer and move it to the end of the queue if necessary
	 *
	 * @param   buffer   The buffer to decref and free
	 */
	inline void consume_(Buffer* buffer, ssize_t amount)
	{
		ssize_t ret = buffer->DecRef(amount);
		if(ret == 0) [[unlikely]]
		{
			while(m_reallocatingBuffer.exchange(true, std::memory_order_acq_rel))
			{
				QAC_YIELD();
			}
			swapToEnd_(buffer);
			m_reallocatingBuffer.store(false);
		}
	}

protected:
	ConcurrentQueue(ConcurrentQueue const& other) = delete;
	ConcurrentQueue& operator=(ConcurrentQueue const& other) = delete;
	ConcurrentQueue(ConcurrentQueue&& other) = delete;
	ConcurrentQueue& operator=(ConcurrentQueue&& other) = delete;

	/**
	 * @brief   Move a buffer to the end of the buffer list
	 *
	 * @details This needs to be called within the m_reallocatingBuffer guard.
	 */
	inline void swapToEnd_(Buffer* buffer)
	{
		Buffer* tail = m_tail.load(std::memory_order_acquire);
		buffer->Clear();
		QAC_CONCURRENT_QUEUE_ASSERT(tail->GetNext() == nullptr);
		QAC_CONCURRENT_QUEUE_ASSERT(buffer != m_writeBuffer.load());
		QAC_CONCURRENT_QUEUE_ASSERT(buffer != m_readBuffer.load());
		QAC_CONCURRENT_QUEUE_ASSERT(buffer != tail);
		buffer->SetGeneration(tail->GetGeneration() + 1);
		tail->SetNext(buffer);
		buffer->SetNext(nullptr);
		m_tail.store(buffer, std::memory_order_release);
	}

	/**
	 * @brief   Decrement the ref count on the buffer and move it to the end of the queue if necessary
	 *
	 * @details This needs to be called within the m_reallocatingBuffer guard.
	 *
	 * @param   buffer   The buffer to decref and free
	 */
	inline void consumeUnlocked_(Buffer* buffer)
	{
		ssize_t ret = buffer->DecRef();
		if(ret == 0) [[unlikely]]
		{
			swapToEnd_(buffer);
		}
	}

	/**
	 * @brief   Decrement the ref count on the buffer and move it to the end of the queue if necessary
	 *
	 * @details This needs to be called within the m_reallocatingBuffer guard.
	 *
	 * @param   buffer   The buffer to decref and free
	 * @param   amount   the amount by which to decrement the count
	 */
	inline void consumeUnlocked_(Buffer* buffer, ssize_t amount)
	{
		ssize_t ret = buffer->DecRef(amount);
		if(ret == 0) [[unlikely]]
		{
			swapToEnd_(buffer);
		}
	}

	/**
	 * @brief   Fetch the next write buffer.
	 *
	 * @details This function is forced not inlined because it's called very rarely, and when it gets inlined,
	 *          it ends up driving the calling function's assembly size high enough to fall outside cache lines,
	 *          which results in slower performance for the common case. Forcing this to be a non-inlined function
	 *          keeps the code for the COMMON case small, and the cost of a function call for the uncommon case
	 *          is largely irrelevant.
	 */
	QAC_FORCE_NO_INLINE void fetchNextWriteBuffer_(typename Buffer::BufferElement& element, Buffer*& buffer, ssize_t batchCount)
	{
		// Just because we won the lottery, though, doesn't mean we're the only ones who won.
		// Someone else may have already claimed the prize. We need to make sure we still
		// need to do this before we actually do it.
		// We do that by re-fetching the buffer and element and re-doing the above check.
		buffer = m_writeBuffer.load(std::memory_order_acquire);
		element = buffer->GetBatchForWrite(batchCount);

		if(element >= buffer->GetEnd())
		{
			// If we're still past the end, time to replace the write buffer.
			// First we get the next buffer in the list. If one exists, it's one
			// we've previously used up and are now taking for reuse.
			Buffer* newBuffer = buffer->GetNext();
			if(!newBuffer)
			{
				// If we get nullptr back from this, then we actually need to allocate.
				newBuffer = m_allocator.allocate(1);
				new (newBuffer) Buffer();
				newBuffer->SetGeneration(buffer->GetGeneration() + 1);
				buffer->SetNext(newBuffer);
				if(buffer == m_tail.load(std::memory_order_acquire))
				{
					m_tail.store(newBuffer, std::memory_order_release);
				}
			}
			QAC_CONCURRENT_QUEUE_ASSERT(newBuffer != buffer);
			// Once we've either obtained or allocated the new buffer, we need to make sure
			// the write position's set to the start of the queue, otherwise we'll just
			// end up throwing it away again.
			newBuffer->SetWritePosition();

			// Now that it's ready for writing, we can store m_writeBuffer and let other threads
			// start using it.
			m_writeBuffer.store(newBuffer, std::memory_order_release);

			// Then we consume the old buffer to tell it that we're no longer pointing m_writeBuffer at it,
			// then we get a new element from it.
			// This shouldn't be past the end, but it's theoretically possible it could be, so we reassign buffer
			// as well so we can do this in a while loop
			consumeUnlocked_(buffer);
			buffer = newBuffer;
			element = buffer->GetBatchForWrite(batchCount);
		}
	}

	/**
	 * @brief   Fetch the next read buffer.
	 *
	 * @details This function is forced not inlined because it's called very rarely, and when it gets inlined,
	 *          it ends up driving the calling function's assembly size high enough to fall outside cache lines,
	 *          which results in slower performance for the common case. Forcing this to be a non-inlined function
	 *          keeps the code for the COMMON case small, and the cost of a function call for the uncommon case
	 *          is largely irrelevant.
	 */
	QAC_FORCE_NO_INLINE bool fetchNextReadBuffer_(typename Buffer::BufferElement& element, Buffer*& buffer, ReadReservationTicket& ticket)
	{
		buffer = m_readBuffer.load(std::memory_order_acquire);
		element = buffer->GetForRead();

		if(element >= buffer->GetEnd())
		{
			Buffer* nextBuffer = buffer->GetNext();
			if(nextBuffer == nullptr)
			{
				// If there isn't a new buffer to read from, we're just going to return false.
				// In this case, we're not updating any information in the ticket.
				// By virtue of the fact that we're here, the ticket's ptr is already null
				// And since there's no next buffer to read from, and we don't want to allocate one when we're just reading,
				// we're just going to keep it null and redo this work next time.
				return false;
			}
			nextBuffer->SetReadPosition();
			QAC_CONCURRENT_QUEUE_ASSERT(nextBuffer != buffer);

			m_readBuffer.store(nextBuffer, std::memory_order_release);
			consumeUnlocked_(buffer);
			buffer = nextBuffer;
			element = buffer->GetForRead();
		}
		// We then set the ticket's buffer to the new buffer we've obtained.
		ticket.buffer = buffer;
		return true;
	}

	QAC_FORCE_NO_INLINE bool fetchNextReadBuffer_(typename Buffer::BufferElement& element, Buffer*& buffer, ssize_t count)
	{
		buffer = m_readBuffer.load(std::memory_order_acquire);
		element = buffer->GetBatchForRead(count);

		if(element >= buffer->GetEnd())
		{
			Buffer* nextBuffer = buffer->GetNext();
			if(nextBuffer == nullptr)
			{
				// If there isn't a new buffer to read from, we're just going to return false.
				// In this case, we're not updating any information in the ticket.
				// By virtue of the fact that we're here, the ticket's ptr is already null
				// And since there's no next buffer to read from, and we don't want to allocate one when we're just reading,
				// we're just going to keep it null and redo this work next time.
				return false;
			}
			nextBuffer->SetReadPosition();
			QAC_CONCURRENT_QUEUE_ASSERT(nextBuffer != buffer);

			m_readBuffer.store(nextBuffer, std::memory_order_release);
			consumeUnlocked_(buffer);
			buffer = nextBuffer;
			element = buffer->GetBatchForRead(count);
		}
		return true;
	}

	/**
	 * @brief   Retrieve the next element to write to.
	 *
	 * @details This method does all the work of both incrementing the write pointer
	 *          and detecting when it's past the end of the write buffer. If it is,
	 *          this function will move on to the next buffer, or allocate a new one if needed,
	 *          and then return an element guaranteed to be valid to write to.
	 *
	 * @return  The next viable write element for the queue
	 */
	inline typename Buffer::BufferElement getNextElement_()
	{
		// First we try to retrieve an element for write from our write buffer.
		Buffer* buffer = m_writeBuffer.load(std::memory_order_acquire);
		typename Buffer::BufferElement element = buffer->GetForWrite();

		// The write buffer may be full. If it is, it'll return a pointer past the end of the buffer.
		// If that happens we have to retrieve or allocate a new buffer.
		// Strictly speaking, this section violates lock-free because the allocation happens within a spin-lock.
		// Practically speaking, this spin-lock happens so infrequently in a queue with a proper block size that
		// it may as well never happen at all.
		while(element >= buffer->GetEnd()) [[unlikely]]
		{
			// When we get here, we use a simple atomic boolean as a spin lock.
			// We perform an exchange() on it - if it returns false, that means we won the lottery
			// because we were the first to set it true.
			if(!m_reallocatingBuffer.exchange(true, std::memory_order_acq_rel))
			{
				fetchNextWriteBuffer_(element, buffer, 1);
				m_reallocatingBuffer.store(false, std::memory_order_release);
			}
			else
			{
				QAC_YIELD();
			}
		}

		// Now we've gotten an element! We can return it back to the caller!
		return element;
	}

public:
	ConcurrentQueue(size_t const maxConcurrentTicketlessReads = 0) 
		: m_readBuffer(nullptr)
		, m_reallocatingBuffer(false)
		, m_writeBuffer(nullptr)
		, m_tail(nullptr)
		, m_subQueue(maxConcurrentTicketlessReads)
		, m_failedReads(0)
		, m_outstanding(0)
	{
		Buffer* buffer = m_allocator.allocate(1);
		new (buffer) Buffer();
		m_readBuffer = buffer;
		m_writeBuffer = buffer;
		m_tail = buffer;
	}

	~ConcurrentQueue()
	{
		Buffer* buffer = m_readBuffer.load(std::memory_order_acquire);
		while(buffer)
		{
			Buffer* nextBuffer = buffer->GetNext();
			buffer->Cleanup();
			buffer->~Buffer();
			m_allocator.deallocate(buffer, 1);
			buffer = nextBuffer;
		}
	}

	/**
	 * @brief   Initialize a reservation ticket. Must be called on a ticket before it can be used.
	 *
	 * @details This isn't a particularly expensive operation, but needs to be called on a buffer
	 *          when it's constructed. The main purpose of this is to save Pop() from having to
	 *          add an if-check to detect an uninitialized buffer. Branching is expensive.
	 *
	 * @param   ticket   the ticket to initialize
	 */
	void InitializeReservationTicket(ReadReservationTicket& ticket)
	{
		ticket.buffer = m_readBuffer.load(std::memory_order_acquire);
		ticket.queue = this;
	}

	/**
	 * @brief   Push an item by reference, calling the copy constructor. Will not fail (unless OOM).
	 *
	 * @param   val   The value to equeue
	 */
	inline void Push(t_ElementType const& val)
	{
		typename Buffer::BufferElement element = getNextElement_();
		new (element.item) t_ElementType(val);
		QAC_CONCURRENT_QUEUE_ASSERT(element.notifier.load() == nullptr);
		if constexpr (t_EnableIdleSleep)
		{
			auto notifier = element.notifier->exchange((typename Buffer::BufferElement::NotifierType)(Buffer::BufferElement::READY_SENTINEL), std::memory_order_release);
			if (notifier != nullptr) [[unlikely]]
			{
				notifier->release();
			}
		}
		else
		{
			element.notifier->store(true, std::memory_order_release);
		}
		if constexpr(t_EnableBatch)
		{
			m_outstanding.fetch_add(1, std::memory_order_release);
		}
	}

	/**
	 * @brief   Push an item by rvalue, calling the move constructor. Will not fail (unless OOM).
	 *
	 * @param   val   The value to equeue
	 */
	inline void PushMove(t_ElementType&& val)
	{
		typename Buffer::BufferElement element = getNextElement_();
		new (element.item) t_ElementType(std::move(val));
		QAC_CONCURRENT_QUEUE_ASSERT(element.notifier.load() == nullptr);
		if constexpr (t_EnableIdleSleep)
		{
			auto notifier = element.notifier->exchange((typename Buffer::BufferElement::NotifierType)(Buffer::BufferElement::READY_SENTINEL), std::memory_order_release);
			if (notifier != nullptr) [[unlikely]]
				{
					notifier->release();
				}
		}
		else
		{
			element.notifier->store(true, std::memory_order_release);
		}
		if constexpr (t_EnableBatch)
		{
			m_outstanding.fetch_add(1, std::memory_order_release);
		}
	}

	inline ssize_t PushBatchPartial(t_ElementType* vals, ssize_t count)
	{
		Buffer* buffer = m_writeBuffer.load(std::memory_order_acquire);
		typename Buffer::BufferElement element = buffer->GetBatchForWrite(count);
		typename Buffer::BufferElement end = buffer->GetEnd();
		while (element >= end) [[unlikely]]
		{
			// When we get here, we use a simple atomic boolean as a spin lock.
			// We perform an exchange() on it - if it returns false, that means we won the lottery
			// because we were the first to set it true.
			if (!m_reallocatingBuffer.exchange(true, std::memory_order_acq_rel))
			{
				fetchNextWriteBuffer_(element, buffer, count);
				m_reallocatingBuffer.store(false, std::memory_order_release);
				end = buffer->GetEnd();

				QAC_YIELD();
			}
		}
		ssize_t pushedCount = std::min(count, end - element);
		if constexpr (std::is_trivially_copyable<t_ElementType>::value)
		{
			memcpy(element.item, reinterpret_cast<void*>(vals), pushedCount * sizeof(t_ElementType));
		}
		for (ssize_t i = 0; i < pushedCount; ++i)
		{
			if constexpr (!std::is_trivially_copyable<t_ElementType>::value)
			{
				new (element.item) t_ElementType(vals[i]);
			}
			if constexpr (t_EnableIdleSleep)
			{
				auto notifier = element.notifier->exchange((typename Buffer::BufferElement::NotifierType)(Buffer::BufferElement::READY_SENTINEL), std::memory_order_release);
				if (notifier != nullptr) [[unlikely]]
				{
					notifier->release();
				}
			}
			else
			{
				element.notifier->store(true, std::memory_order_release);
			}
			++element;
		}
		m_outstanding.fetch_add(pushedCount, std::memory_order_release);
		return pushedCount;
	}

	/**
	 * @brief   Push a batch of items. The items will be copy-constructed from the array. Will not fail (unless OOM).
	 *
	 * @details Compared to Push(), when enqueuing multiple items in sequence, PushBatch() reduces the number of
	 *          contentuous atomic variable operations to only two per batch, thus dramatically increasing performance.
	 *          However, when only a single item is being enqueued, the non-batched push will perform slightly better
	 *          (though not better enough to warrant the cost of a branch to detect if the number is 1 when it isn't known
	 *          at compile time).
	 *
	 * @param   vals   A C-style array of objects to push
	 * @param   count  The number of items in the array. (Note this is not necessarily the memory size of the array, but the number of elements that should actually be read from it.)
	 */
	inline void PushBatch(t_ElementType * vals, ssize_t count)
	{
		if constexpr (!t_EnableBatch)
		{
			throw std::logic_error("Batch operations are not enabled on this queue.");
		}
		else
		{
			while (count > 0)
			{
				ssize_t pushedCount = PushBatchPartial(vals, count);
				vals += pushedCount;
				count -= pushedCount;
			}
		}
	}

	/**
	 * @brief   Attempt to pop an item. Not guaranteed to succeed, as the queue may be empty.
	 *
	 * @details To improve performance, all pop operations will cache data in the ReadReservationTicket parameter.
	 *
	 *          If the pop operation returns false, this parameter MUST be held onto and passed back into Pop()
	 *          or an element in the queue will become permanently inaccessible.
	 *
	 *          It doesn't matter what thread passes the ticket back in, but it cannot be disposed of so long as
	 *          Pop() has returned false.
	 *
	 *          For emphasis: The ticket MUST be passed back to the queue again in order to read all elements from the queue.
	 *          Ticketed pops operate like a backorder system. If you make a pop and an item is ready to read, it will
	 *          be given to you on the spot. If the queue is empty, it populates the passed ReadReservationTicket with a
	 *          *reservation* for the spot it tried to read. When that spot is later written to, you must return with the same
	 *          ticket - with the receipt, to continue the backorder metaphor - in order to read it. It will not be given
	 *          to another customer, no matter what!
	 *
	 *          The reason for this is that, to achieve its speed, QACQueue pops items *optimistically*, assuming something
	 *          is ready to read when you attempt to read it. It increments the read head based on this assumption. This
	 *          allows QACQueue to avoid complex compare-and-swap operations and keep its common-case operation to a single
	 *          atomic increment per push or pop. The downside, though, is when it's incorrect on its optimistic pop,
	 *          it cannot safely correct - it can't simply decrement the read head because a race condition exists where thread
	 *          A attempts to read index 0, to find it not yet written, then thread B pushes indexes 0 and 1, and then thread
	 *          C successfully reads index 1, believing index 0 to already have been read because thread A incremented the read
	 *          head already. The read head is now at 2, with index 1 consumed and index 0 not consumed. Decrementing the read
	 *          head would set it back to index 1, thus resulting in index 0 not being read on the next pop, and index 1
	 *          being read twice.
	 *
	 *          In order to resolve that problem, the ReadReservationTicket is used to record locally (so as to avoid the need
	 *          for something like a secondary concurrent queue to store failed read indices in) that index 0 was claimed but
	 *          not yet read. In order to actually READ index 0, that ticket must be passed back into Pop() again.
	 *
	 *          It is vitally important, however, to stress that ReadReservationTicket *is not thread-safe* and *must only
	 *          be accessed by one thread at a time.* This DOES limit the use cases for ticketed pops to those where either
	 *          only one consumer is active, or each consumer is assigned its own ticket, possibly in stack memory or thread-local
	 *          storage.
	 *
	 *          It's also worth emphasizing that the ticket is a permanent reservation for a specific index in the queue and cannot
	 *          be returned to the queue, so doing something like emptying out the ticket by looping until Pop() returns false
	 *          will result in one item in the queue being permanently associated with the ticket used, so if other Pop() forms
	 *          are used to read from the queue later, or if a different ticket is used later, one item will have been rendered
	 *          unavailable.
	 *
	 *          If these limitations do not suit your use case (and, in many circumstances, they won't), then consider using
	 *          the ticket-free Pop() or BatchPop(). In fact, BatchPop() is often preferable to ticketed pops,
	 *          as well - if you're reading more than one or two elements at a time, you'll likely find BatchPop() to perform
	 *          faster than Pop() and have fewer limitations. (Please see the benchmarks for a better understanding of where
	 *          BatchPop with small batch sizes exceeds or falls behind ticketed pops.)
	 *
	 *          An additional word of warning: Ticket-Free pops do, in fact, use a secondary queue under the hood to
	 *          store tickets that are shared between threads. This secondary queue is fast in most use cases, because
	 *          it only stores tickets when a pop fails and pop-from-empty in the secondary queue is the optimal
	 *          path. However, because pops when it's not empty are much slower, the overall amortized performance of
	 *          ticket-free pops will be somewhat worse than ticketed pops.
	 *
	 *          Additionally, and vitally: The Ticket-Free Pop API is ticket-free in name only and does use tickets
	 *          under the hood. However, BatchPop() is actually ENTIRELY ticket-free and DOES NOT use tickets. Which means
	 *          that the Ticket-Free and BatchPop APIs *do not mix very well* unless you are *very careful* about your
	 *          usage - any time the ticket-free Pop() returns false, an element in the queue has been made inaccessible
	 *          for batch dequeueing and may then only be retrieved via another ticket-free pop. The same is true for
	 *          mixing ticket-free and ticketed pops - any time either returns false, an element has been made inaccessible
	 *          to the other.
	 *
	 *          If Pop() returns true, it is still highly recommended to keep the ticket alive and pass it back in.
	 *          The only reason for this is performance - the performance drop from having to adjust reference counts
	 *          on each pop operation isn't crippling, but it is noticeable.
	 *
	 *
	 * @param   val      A reference to a value, which will be filled with the contents of the dequeued element, if any.
	 *                   The move assignment operator will be called on the value, if one exists.
	 * @param   ticket   A reservation ticket which will hold cached data to improve performance.
	 *
	 * @return  true if the pop succeeded and tha value holds a valid item, false if the pop failed.
	 */
	inline bool TryPop(t_ElementType& val, ReadReservationTicket& ticket)
	{
		// For reads, we'll start out by checking our reservation ticket. If it's got cached data, we can skip a lot of work we already did.
		typename Buffer::BufferElement element = ticket.ptr;
		Buffer* buffer = ticket.buffer;

		// There are a few cases we can run into in the pop operation.
		// The easiest case is after a failed pop, in which case we already have our element and can check it again.
		if(!element.item) [[likely]]
		{
			// The second case is when the ticket passed in has been held over from a previous successful pop.
			// In this case we don't have to worry about acquiring the read buffer, because it's cached. We only have
			// to do that if the current one is exhausted.

			// Step one, get the next element and determine if the current buffer is exhausted!
			element = buffer->GetForRead();
			while(element >= buffer->GetEnd()) [[unlikely]]
			{
				// If the buffer is exhausted, we have to acquire the next one.
				// This is done under the same spin-lock as allocating a new buffer for writes, and the logic is almost identical.
				// The only difference is that, if buffer->GetNext() returns nullptr, instead of allocating a new one,
				// we just return false; for more details on this logic, see the comments in getNextElement_()
				if(!m_reallocatingBuffer.exchange(true, std::memory_order_acq_rel))
				{
					if(!fetchNextReadBuffer_(element, buffer, ticket))
					{
						m_reallocatingBuffer.store(false, std::memory_order_release);
						return false;
					}
					m_reallocatingBuffer.store(false, std::memory_order_release);
				}
				else
				{
					QAC_YIELD();
				}
			}
		}

		if constexpr(t_EnableBatch)
		{
			m_outstanding.fetch_add(-1, std::memory_order_relaxed);
		}

		// Now that we have an element to read, we have to check if there's any actual data in it.
		// If not, we're going to remember this element in the reservation ticket and come back to it later.
		// This definitively prevents any race conditions involved in attempting to correct for overcommit.
		auto notifier = element.notifier->load(std::memory_order_acquire);
		if(notifier == (typename Buffer::BufferElement::NotifierType)(Buffer::BufferElement::READY_SENTINEL)) [[likely]]
		{
			// If the element did have valid data, we need to make sure our ticket's not holding any cache information.
			// Otherwise we'd just keep ending up reading the same cached element over and over.
			ticket.ptr = { nullptr, nullptr };

			// Finally, we'll go ahead and pull the data from the element, destroy it, and decrement and possibly free the buffer.
			// Then we can return true - success!
			val = std::move(*element.item);
			element.item->~t_ElementType();
			QAC_CONCURRENT_QUEUE_ASSERT(element->notifier.exchange(nullptr, std::memory_order_acq_rel) == (typename Buffer::BufferElement::NotifierType)(Buffer::BufferElement::READY_SENTINEL));

			// Surprisingly, even though the ability exists to store a local count on the ticket
			// and consume it as a single operation only when switching buffers, in practice, in
			// this particular case, doing the consume every time actually improves performance
			// because it allows contention to be shared between two variables rather than focused
			// entirely on just one.
			// Strangely, the same doesn't hold true for batch pops (where accumulating locally
			// and waiting till the end yields much better performance) or for the calls to change m_outstanding
			// on the single-item API when batch mode is enabled.
			consume_(buffer, 1);

			return true;
		}
		m_contentionSplitter.fetch_add(1, std::memory_order_relaxed);
		ticket.ptr = element;
		return false;
	}

	void PopWait(t_ElementType& val, size_t maxSpinsBeforeSemaphoreWait = QAC_DEFAULT_SPIN_COUNT)
	{
		ReadReservationTicket ticket;
		InitializeReservationTicket(ticket);
		while (ticket.ptr.item == nullptr)
		{
			if (TryPop(val, ticket))
			{
				return;
			}
		}
		size_t spins = 0;
		while (ticket.ptr.notifier->load(std::memory_order_acquire) == (typename Buffer::BufferElement::NotifierType)(Buffer::BufferElement::FREE_SENTINEL)) [[unlikely]]
		{
			QAC_YIELD();
			if constexpr (t_EnableIdleSleep)
			{
				if (++spins > maxSpinsBeforeSemaphoreWait)
				{
					std::binary_semaphore semaphore(0);
					std::binary_semaphore* previous = ticket.ptr.notifier->exchange(&semaphore, std::memory_order_acq_rel);
					if (previous != (typename Buffer::BufferElement::NotifierType)(Buffer::BufferElement::READY_SENTINEL))
					{
						semaphore.acquire();
					}
					break;
				}
			}
		}
		val = std::move(*ticket.ptr.item);
		ticket.ptr.item->~t_ElementType();
		QAC_CONCURRENT_QUEUE_ASSERT(ticket.ptr->notifier.exchange((typename Buffer::BufferElement::NotifierType)(Buffer::BufferElement::FREE_SENTINEL)) == (typename Buffer::BufferElement::NotifierType)(Buffer::BufferElement::READY_SENTINEL));

		consume_(ticket.buffer, 1);
		return;
	}

	/**
	 * @brief   Attempt to pop an item without passing in any tickets.
	 *
	 * @details This version of Pop() does not require user-provided tickets to complete the pop operation,
	 *          making it more suitable for certain use cases that can't meet the riged requirements of the ticketed
	 *          API. Do note, however, that while pop-from-empty is quite fast with the ticketed API, the ticket-free
	 *          API suffers greatly with the ticket-free API. Pop-from-empty, in general, gets roughly 1/3 the throughput
	 *          of non-empty pops.
	 *
	 *          HOWEVER, there is a word of warning: Ticket-Free pops do, in fact, use a secondary queue under the hood to
	 *          store tickets that are shared between threads. This secondary queue is fast in most use cases, because
	 *          it only stores tickets when a pop fails and pop-from-empty in the secondary queue is the optimal
	 *          path. However, because pops when it's not empty are much slower, the overall amortized performance of
	 *          ticket-free pops will be somewhat worse than ticketed pops.
	 *
	 *          Additionally, and vitally: The Ticket-Free Pop API is ticket-free in name only and does use tickets
	 *          under the hood. However, BatchPop() is actually ENTIRELY ticket-free and DOES NOT use tickets. Which means
	 *          that the Ticket-Free and BatchPop APIs *do not mix very well* unless you are *very careful* about your
	 *          usage - any time the ticket-free Pop() returns false, an element in the queue has been made inaccessible
	 *          for batch dequeueing and may then only be retrieved via another ticket-free pop. The same is true for
	 *          mixing ticket-free and ticketed pops - any time either returns false, an element has been made inaccessible
	 *          to the other.
	 *
	 *          See the documentation for Pop(t_ElementType& val, ReadReservationTicket& ticket) for more information.
	 *
	 * @param   val      A reference to a value, which will be filled with the contents of the dequeued element, if any.
	 *                   The move assignment operator will be called on the value, if one exists.
	 *
	 * @return  true if the pop succeeded and tha value holds a valid item, false if the pop failed.
	 */
	inline bool TryPop(t_ElementType& val)
	{
		ReadReservationTicket ticket;
		bool reattempt = m_subQueue.TryPop(ticket);
		if (!reattempt)
		{
			if (m_failedReads.load(std::memory_order_acquire) != 0)
			{
				return false;
			}
			InitializeReservationTicket(ticket);
		}
		if (TryPop(val, ticket))
		{
			if (reattempt)
			{
				m_failedReads.fetch_sub(1, std::memory_order_acq_rel);
			}
			return true;
		}
		if (!reattempt)
		{
			m_failedReads.fetch_add(1, std::memory_order_acq_rel);
		}
		m_subQueue.Push(ticket, (ticket.ptr - ticket.buffer->GetStart()) + ticket.buffer->GetGeneration() * t_BlockSize);
		return false;
	}

	/**
	 * @brief Stores state and provides logic for iterating through the results of a BatchPop.
	 *
	 * @details The BatchPopList is an iterator-like class that allows for the consumption of elements
	 *          returned via BatchPop(). Because the queue uses multiple buffers under the hood, there is
	 *          a possibility that the results of the BatchPop() will span two more more buffers. In
	 *          that situation, BatchPopList will contain the contiguous elements retrieved from only
	 *          one buffer at a time. When the end of the buffer is reached, it will lazy-fetch elements from
	 *          the next buffer until the entire batch has been consumed.
	 *
	 *          WARNING: Iterating the BatchPopList is important to trigger reference counting logic on
	 *          the queue buffers to enable them to be recycled. If you pop but don't iterate the list,
	 *          you may cause the queue to experience a memory leak. When BatchPopList is destroyed, it
	 *          will automatically perform this iteration for you to update the reference counts. The iteration
	 *          will also be performed automatically if you pass a non-consumed iterator back into BatchPop
	 *          to retrieve more items. However, if you do neither of those things and an iterator is left sitting
	 *          somewhere unconsumed, it will prevent the reference counting from occurring and memory will not
	 *          be restored to the reusable buffer list, resulting in a leak.
	 */
	class BatchPopList
	{
	public:
		/**
		 * @brief Fetch the next element in the batch
		 *
		 * @details Normally, this function amounts to a pointer increment and a copy constructor and destructor
		 *          for t_ElementType. However, in scenarios where a batch spans the boundaries of two buffers,
		 *          this will iterate until it reaches the end of the current buffer, then lazy fetch elements
		 *          from successive buffers until the batch is exhausted.
		 */
		inline bool TryReadNext(t_ElementType& val)
		{
			if (m_primed) [[unlikely]]
			{
				val = t_ElementType(std::move(m_primer));
				m_primed = false;
				return true;
			}
			if(!m_pendingRead)
			{
				while(m_element >= m_end) [[unlikely]]
				{
					// If the buffer is exhausted, we have to acquire the next one.
					// This is done under the same spin-lock as allocating a new buffer for writes, and the logic is almost identical.
					// The only difference is that, if buffer->GetNext() returns nullptr, instead of allocating a new one,
					// we just return false; for more details on this logic, see the comments in getNextElement_()
					Buffer* buffer = m_buffer;
					for(;;)
					{
						if(!m_queue->m_reallocatingBuffer.exchange(true, std::memory_order_acq_rel))
						{
							if(!m_queue->fetchNextReadBuffer_(m_element, m_buffer, m_remaining))
							{
								m_queue->m_reallocatingBuffer.store(false, std::memory_order_release);
								continue;
							}
							if(m_consumed != 0)
							{
								m_queue->consumeUnlocked_(buffer, m_consumed);
								m_consumed = 0;
							}
							m_end = m_buffer->GetEnd();
							m_queue->m_reallocatingBuffer.store(false, std::memory_order_release);
							break;
						}
						QAC_YIELD();
					}
				}
			}
			if(m_element.notifier->load(std::memory_order_acquire) != (typename Buffer::BufferElement::NotifierType)(Buffer::BufferElement::READY_SENTINEL)) [[unlikely]]
			{
				m_pendingRead = true;
				return false;
			}
			++m_consumed;
			val = t_ElementType(std::move(*m_element.item));
			m_element.item->~t_ElementType();
			--m_remaining;
			++m_element;
			m_pendingRead = false;
			return true;
		}

		inline void ReadNextWait(t_ElementType& val, size_t maxSpinsBeforeSemaphoreWait = QAC_DEFAULT_SPIN_COUNT)
		{
			if (m_primed) [[unlikely]]
			{
				val = t_ElementType(std::move(m_primer));
				m_primed = false;
				return;
			}
			if (!m_pendingRead)
			{
				while (m_element >= m_end) [[unlikely]]
				{
					// If the buffer is exhausted, we have to acquire the next one.
					// This is done under the same spin-lock as allocating a new buffer for writes, and the logic is almost identical.
					// The only difference is that, if buffer->GetNext() returns nullptr, instead of allocating a new one,
					// we just return false; for more details on this logic, see the comments in getNextElement_()
					Buffer* buffer = m_buffer;
					for (;;)
					{
						if (!m_queue->m_reallocatingBuffer.exchange(true, std::memory_order_acq_rel))
						{
							if (!m_queue->fetchNextReadBuffer_(m_element, m_buffer, m_remaining))
							{
								m_queue->m_reallocatingBuffer.store(false, std::memory_order_release);
								continue;
							}
							if (m_consumed != 0)
							{
								m_queue->consumeUnlocked_(buffer, m_consumed);
								m_consumed = 0;
							}
							m_end = m_buffer->GetEnd();
							m_queue->m_reallocatingBuffer.store(false, std::memory_order_release);
							break;
						}
						QAC_YIELD();
					}
				}
			}

			size_t spins = 0;
			while (m_element.notifier->load(std::memory_order_acquire) != (typename Buffer::BufferElement::NotifierType)(Buffer::BufferElement::READY_SENTINEL)) [[unlikely]]
			{
				QAC_YIELD();
				if constexpr (t_EnableIdleSleep)
				{
					if (++spins > maxSpinsBeforeSemaphoreWait)
					{
						std::binary_semaphore semaphore(0);
						std::binary_semaphore* previous = m_element.notifier->exchange(&semaphore, std::memory_order_acq_rel);
						if (previous != (typename Buffer::BufferElement::NotifierType)(Buffer::BufferElement::READY_SENTINEL))
						{
							semaphore.acquire();
						}
						break;
					}
				}
			}

			++m_consumed;
			val = t_ElementType(std::move(*m_element.item));
			m_element.item->~t_ElementType();
			--m_remaining;
			++m_element;
			m_pendingRead = false;
		}

		/**
		 * @brief Check if there are more items to iterate.
		 *
		 * @return true if there are elements left in the batch, false if the batch is exhausted
		 */
		inline bool More() { return (m_remaining > 0 || m_primed); }

		~BatchPopList()
		{
			while(More()) [[unlikely]]
			{

				t_ElementType data;
				ReadNextWait(data);
			}

			if(m_consumed != 0) [[likely]]
			{
				m_queue->consume_(m_buffer, m_consumed);
			}
		}

		BatchPopList(BatchPopList&& other)
			: m_queue(other.m_queue)
			, m_element(other.m_element)
			, m_end(other.m_end)
			, m_buffer(other.m_buffer)
			, m_remaining(other.m_remaining)
			, m_count(other.m_count)
			, m_consumed(other.m_consumed)
			, m_pendingRead(other.m_pendingRead)
		{
			other.m_queue = nullptr;
			other.m_element = nullptr;
			other.m_end = nullptr;
			other.m_buffer = nullptr;
			other.m_remaining = 0;
			other.m_count = 0;
			other.m_consumed = 0;
			other.m_pendingRead = false;
		}

	protected:

		BatchPopList()
		{}

		BatchPopList(ConcurrentQueue* queue)
			: m_queue(queue)
		{}

		BatchPopList(BatchPopList const& other) = delete;
		BatchPopList(BatchPopList& other) = delete;
		BatchPopList& operator=(BatchPopList const& other) = delete;
		BatchPopList& operator=(BatchPopList& other) = delete;

		friend class ConcurrentQueue;
		ConcurrentQueue* m_queue;
		typename Buffer::BufferElement m_element;
		typename Buffer::BufferElement m_end;
		Buffer* m_buffer{ nullptr };
		ssize_t m_remaining{ 0 };
		ssize_t m_count{ 0 };
		ssize_t m_consumed{ 0 };
		bool m_pendingRead{ false };

		bool m_primed{ false };
		t_ElementType m_primer;
	};

	BatchPopList CreatePopList()
	{
		return BatchPopList(this);
	}

	/**
	 * @brief Retrieve multiple items from the queue. When maxCount is more than 1 or 2, PopBatch can offer orders of
	 *        magnitude greater performance than either Pop option.
	 *
	 * @details In contrast with the other two Pop() options, PopBatch() takes advantage of the contiguous storage
	 *          structure of QACQueue to reduce contention by allowing the retrieval of multiple items from the queue with
	 *          only a single atomic increment. A second atomic operation is used to keep track of how many elements it's allowed
	 *          to read to ensure it doesn't over-consume the queue. When it does, a third atomic operation is used to correct.
	 *
	 *          However, while the additional atomic operations on the queue result in slower performance for individual item
	 *          pops, this is vastly made up for when reading larger numbers of items by reducing the contention on each
	 *          individual read - while 100 normal pop operations would involve a total of 100 atomic increments on contentuous
	 *          variables (when batching is disabled), a batch read of 100 items involves a total of 2 atomic increments on
	 *          contentuous variables in the optimistic case, and 3 in the pessimistic case. Additionally, since multiple elements
	 *          are retrieved in a single function call, the user code can spend more time actually processing the elements it has
	 *          retrieved, which means there are fewer overall function calls on the queue, and thus, those 3 operations are far
	 *          less likely to actually experience contention resulting in cache misses, and the code doing the processing is able
	 *          to safely rely on the cache locality of the data it receives without concern for losing that locality to contention
	 *          while iterating them.
	 *
	 *          There are, however, drawbacks to the batch API.
	 *
	 *          First, simply the act of enabling batch push and pop makes the non-batched operations a little bit slower,
	 *          as it adds a requirement for them to update the outstanding count in order for batched operations to function properly
	 *          when the two are mixed.
	 *
	 *          Second, batched operations with a maxCount of 1 are slower than ticketed operations. In general, batch size of 1 will see
	 *          close to the same performance as the ticket-free API for successful pops when batch mode is enabled, and will be slightly
	 *          slower than ticket-free pops with batch mode disabled. However...
	 *
	 *          Third (to be taken with a LARGE grain of salt), while successful pops in batch mode are extremely fast,
	 *          pop-from-empty can be much slower than other options depending on your use case. If you're doing other processing
	 *          when the queue is empty, or sleeping when the queue is empty, and thus keeping contention low, you'll likely see
	 *          pop-from-empty performing as well as a successful pop. But if your threads are all looping on trying to read
	 *          from the empty queue, the number of attempts they can do per second will be dramatically lower due to the increased
	 *          contention this causes. (However, if you're in that situation, you're not really DOING anything, so practically
	 *          speaking... does it really matter that you're doing less of nothing?)
	 *
	 *          Finally, mixing the normal API and the batch API can lead to unexpected behavior. The non-batch API removes items from
	 *          the pool that the batch API can read from *even when their reads fail*, so if you perform a non-batch read that returns false,
	 *          then push an item, then attempt to pop that item using the batch API, you will find the batch API returns 0 items
	 *          instead of the expected 1, because that item was already reserved by the non-batch API before it was written.
	 *          See the documentation for Pop(t_ElementType& val, ReadReservationTicket& ticket) for more information.
	 *
	 * @param   result    Out variable in which to store the retrieved batch data. May safely be reused once all items have been consumed.
	 *
	 * @param   maxCount  Maximum number of elements to retrieve. If the full requested amount doesn't exist in the queue, a partial result
	 *                    will be returned.
	 */
	void PopBatch(BatchPopList& result, ssize_t maxCount)
	{
		if constexpr(!t_EnableBatch)
		{
			throw std::logic_error("Batch operations are not enabled on this queue.");
		}
		else
		{
			/*while(result.More()) [[unlikely]]
			{
				t_ElementType data;
				result.ReadNextWait(data);
			}*/
			ssize_t newOutstanding = std::max(m_outstanding.fetch_sub(maxCount, std::memory_order_acq_rel) - maxCount, -maxCount);
			ssize_t batchSize = maxCount;
			if(newOutstanding < 0) [[unlikely]]
			{
				batchSize += newOutstanding;
				newOutstanding = m_outstanding.fetch_sub(newOutstanding, std::memory_order_release) - newOutstanding;
				if(batchSize <= 0) [[likely]]
				{
					return;
				}
			}
			Buffer* buffer = m_readBuffer.load(std::memory_order_acquire);
			typename Buffer::BufferElement element = buffer->GetBatchForRead(batchSize);
			if((result.m_buffer != buffer) & (result.m_consumed != 0))
			{
				consume_(result.m_buffer, result.m_consumed);
				result.m_consumed = 0;
			}
			result.m_element = element;
			result.m_end = buffer->GetEnd();
			result.m_buffer = buffer;
			result.m_remaining = batchSize;
			result.m_count = batchSize;
		}
	}

	void PopBatchWait(BatchPopList& result, ssize_t maxCount, size_t maxSpinsBeforeSemaphoreWait = QAC_DEFAULT_SPIN_COUNT)
	{
		if constexpr (!t_EnableBatch)
		{
			throw std::logic_error("Batch operations are not enabled on this queue.");
		}
		else
		{
			PopBatch(result, maxCount);
			if (!result.More())
			{
				t_ElementType primer;
				PopWait(primer, maxSpinsBeforeSemaphoreWait);
				PopBatch(result, maxCount - 1);
				result.m_primed = true;
				result.m_primer = t_ElementType(std::move(primer));
			}
		}
	}

protected:
	// Cacheline padding prevents false sharing.
	// Read head, not necessarily the same as the write head
	alignas(QAC_CACHELINE_SIZE) std::atomic<Buffer*> m_readBuffer;
	// Spin lock used when swapping buffers - not technically lock free, but lock free isn't always faster.
	// And this is used rarely enough that the simplicity of the code around it is far more valuable.
	// The performance improvement of making this lock free would be imperceptible, and the increased amount
	// of code to get it to work right would likely bloat code size and cause more cache misses in execution.
	alignas(QAC_CACHELINE_SIZE) std::atomic<bool> m_reallocatingBuffer;
	// Write head, not necessarily the same as the read head
	alignas(QAC_CACHELINE_SIZE) std::atomic<Buffer*> m_writeBuffer;
	// Tail. Obviously.
	alignas(QAC_CACHELINE_SIZE) std::atomic<Buffer*> m_tail;
	alignas(QAC_CACHELINE_SIZE) detail::ReservationTicketSubQueue<ReadReservationTicket, t_AllocatorType> m_subQueue;
	alignas(QAC_CACHELINE_SIZE) std::atomic<ssize_t> m_failedReads;
	alignas(QAC_CACHELINE_SIZE) std::atomic<ssize_t> m_outstanding;
	alignas(QAC_CACHELINE_SIZE) std::atomic<ssize_t> m_contentionSplitter;
	alignas(QAC_CACHELINE_SIZE) t_AllocatorType<Buffer> m_allocator;
};

/**
 * @class QAC::BoundedReadReservationTicket
 *
 * @brief Represents a reservation to read an element that hasn't been written to yet.
 */
template <typename t_ElementType>
struct QAC::BoundedReadReservationTicket
{
	void* ptr{ nullptr };
	int64_t generation{ 0 };

	BoundedReadReservationTicket()
	{}

	BoundedReadReservationTicket(BoundedReadReservationTicket const& other) = delete;
	BoundedReadReservationTicket& operator=(BoundedReadReservationTicket const& other) = delete;

	BoundedReadReservationTicket(BoundedReadReservationTicket&& other) noexcept 
		: ptr(other.ptr)
	{
		other.ptr = nullptr;
		other.generation = 0;
	}

	BoundedReadReservationTicket& operator=(BoundedReadReservationTicket&& other) noexcept
	{
		ptr = other.ptr;
		generation = other.generation;
		other.ptr = nullptr;
		other.generation = 0;
		return *this;
	}
};

/**
 * @class QAC::BoundedReadReservationTicket
 *
 * @brief Represents a reservation to write an element that's already holding unread data
 */
template <typename t_ElementType>
struct QAC::BoundedWriteReservationTicket
{
	void* ptr{ nullptr };
	int64_t generation{ 0 };

	BoundedWriteReservationTicket()
	{}

	BoundedWriteReservationTicket(BoundedWriteReservationTicket const& other) = delete;
	BoundedWriteReservationTicket& operator=(BoundedWriteReservationTicket const& other) = delete;

	BoundedWriteReservationTicket(BoundedWriteReservationTicket&& other) noexcept 
		: ptr(other.ptr) 
		, generation(other.generation)
	{ 
		other.ptr = nullptr; 
		other.generation = 0;
	}

	BoundedWriteReservationTicket& operator=(BoundedWriteReservationTicket&& other) noexcept
	{
		ptr = other.ptr;
		generation = other.generation;
		other.ptr = nullptr;
		other.generation = 0;
		return *this;
	}
};

/**
 * @class   QAC::ConcurrentBoundedQueue
 *
 * @brief   A bounded implementation of ConcurrentQueue.
 *
 * @details The core algorithm of this queue is essentially the same algorithm as the
 *          unbounded version of this queue - however, there are a few key differences:
 *
 *          First, and probably most importantly, this queue cannot grow. It works as
 *          a circular buffer, and can only hold the specified number of elements at
 *          one time. Elements that are read by Pop() become available to be
 *          written again, but if no consumer threads are running, or producer threads
 *          significantly outpace consumer threads, the queue can become full,
 *          causing Push() to return false.
 *
 *          Secondly, unlike the unbounded version, this queue is truly lock-free
 *          and wait-free. There are no situations that involve taking a lock.
 *
 *          Thirdly, reservation tickets are required for both push AND pop;
 *          however, they only need to be kept alive after a return of false from either
 *          method. If the return value is true, the ticket can be safely thrown away.
 *
 *          Note that there is one situation that can cause an push thread to become
 *          blocked: if a pop thread gets a return of false and doesn't call Pop()
 *          again with that ticket, an push thread will be blocked waiting for that
 *          spot to be read, even after other push threads successfully move on and continue
 *          writing.
 *
 *          Also note that t_QueueSize will be adjusted up to the nearest power of 2 for performance
 *          reasons.
 *
 *          Finally, note that ConcurrentBoundedQueue does NOT support a batched API.
 *          The reason for this is that the fact that pushes can fail increases the bookkeeping
 *          requirements for the batch API beyond the point that can be reasonably, correctly,
 *          and performantly handled in a lock-free concurrent context.
 *
 * @tparam  t_ElementType       the type of element to store in the queue
 *
 * @tparam  t_QueueSize         the maximum number of elements that can be in the queue at a time.
 *                              Once this number has been reached, push() operations will fail until
 *                              elements have been dequeued. This is not a maximum number of elements
 *                              ever inserted, only a maximum number that can be held unread at a time -
 *                              representing overhead between push and pop operations.
 *
 * @tparam  t_AllocatorType     Allocator used to allocate tickets for the ticket-free push
 *                              and pop operations. The allocators are NOT used in the operations
 *                              that do accept ticket parameters; those are alloc-free.
 */
template <typename t_ElementType, size_t t_QueueSize, bool t_EnableBatch, bool t_EnableIdleSleep, template<typename> typename t_AllocatorType>
class alignas(QAC_CACHELINE_SIZE) QAC::ConcurrentBoundedQueue
{
public:
	using ReadReservationTicket = QAC::BoundedReadReservationTicket<t_ElementType>;
	using WriteReservationTicket = BoundedWriteReservationTicket<t_ElementType>;

	using BufferElement = QAC::detail::BoundedBufferElementImpl<t_ElementType, t_EnableIdleSleep>;

	ConcurrentBoundedQueue(ssize_t maxConcurrentTicketFreeReads = 0, ssize_t maxConcurrentTicketFreeWrites = 0) 
		: m_readIdx(0)
		, m_writeIdx(0)
		, m_readSubQueue(maxConcurrentTicketFreeReads)
		, m_failedReads(0)
		, m_writeSubQueue(maxConcurrentTicketFreeWrites)
		, m_failedWrites(0)
		, m_outstanding(0)
	{
		memset(reinterpret_cast<void*>(m_buffer), 0, c_adjustedSize * sizeof(BufferElement)); 
	}

	~ConcurrentBoundedQueue()
	{
		BufferElement* buffer = reinterpret_cast<BufferElement*>(m_buffer);
		for(size_t idx = 0; idx < c_adjustedSize; ++idx)
		{
			BufferElement* element = buffer + (idx & (c_adjustedSize - 1));
			if(element->generation.load() > 0)
			{
				element->item.~t_ElementType();
			}
		}
	}

	/**
	 * @brief   Push an item by reference, calling the copy constructor. Will fail if the queue is full.
	 *
	 * @param   val      The value to equeue
	 * @param   ticket   A reservation ticket that will hold cached data in the event of a return of false
	 *
	 * @return  true if the element was successfully enqueued, false otherwise
	 */
	inline bool TryPush(t_ElementType const& val, WriteReservationTicket& ticket)
	{
		// This case is much simpler than the unbounded case!
		// First we check to see if the reservation ticket contains an element we're supposed to retry a write to
		BufferElement* element = reinterpret_cast<BufferElement*>(ticket.ptr);
		int64_t writeGeneration = ticket.generation;

		if(!element) [[likely]]
		{
			// If not, then we get a new one with a simple fetch_add on the write index, wrapping it appropriately.
			size_t idx = m_writeIdx.fetch_add(1, std::memory_order_acq_rel);
			element = m_buffer + (idx & (c_adjustedSize - 1));
			writeGeneration = (idx >> c_generationOp) + 1;
		}


		// Check the generation flag. If it's not at current generation - 1, we can't overwrite it and have to return false,
		// storing this element on the reservation ticket to make sure we try it again later.
		int64_t generation = element->generation.load(std::memory_order_acquire);
		if(generation == -(writeGeneration - 1)) [[likely]]
		{
			// If it's not already ready, we make sure the reservation ticket is clear so we don't write it again...
			ticket.ptr = nullptr;

			// ...then we construct the new element...
			new (&element->item) t_ElementType(val);
			QAC_CONCURRENT_QUEUE_ASSERT(element->generation.load() == -(writeGeneration - 1));

			if constexpr (t_EnableBatch)
			{
				m_outstanding.fetch_add(1, std::memory_order_release);
			}
			if constexpr (t_EnableIdleSleep)
			{
				auto waiting = element->notifier.exchange(reinterpret_cast<std::binary_semaphore*>(BufferElement::READY_SENTINEL), std::memory_order_release);
				if (waiting != nullptr)
				{
					waiting->release();
				}
			}
			// ...then we signal that the element is ready to read and return true.
			element->generation.store(writeGeneration, std::memory_order_release);
			return true;
		}
		ticket.ptr = element;
		ticket.generation = writeGeneration;
		m_writeContentionSplitter.fetch_add(1, std::memory_order_relaxed);
		return false;
	}

	/**
	 * @brief   Push an item by rvalue reference, calling the move constructor. Will fail if the queue is full.
	 *
	 * @param   val      The value to equeue
	 * @param   ticket   A reservation ticket that will hold cached data in the event of a return of false
	 *
	 * @return  true if the element was successfully enqueued, false otherwise
	 */
	inline bool TryPushMove(t_ElementType& val, WriteReservationTicket& ticket)
	{
		// See above for comments; this algorithm is identical except for construction via move.
		BufferElement* element = reinterpret_cast<BufferElement*>(ticket.ptr);
		int64_t writeGeneration = ticket.generation;

		if (!element) [[likely]]
		{
			size_t idx = m_writeIdx.fetch_add(1, std::memory_order_acq_rel);
			element = m_buffer + (idx & (c_adjustedSize - 1));
			writeGeneration = (idx >> c_generationOp) + 1;
		}


		int64_t generation = element->generation.load(std::memory_order_acquire);
		if (generation == -(writeGeneration - 1)) [[likely]]
		{
			ticket.ptr = nullptr;

			new (&element->item) t_ElementType(std::move(val));
			QAC_CONCURRENT_QUEUE_ASSERT(element->generation.load() == -(writeGeneration - 1));

			if constexpr (t_EnableBatch)
			{
				m_outstanding.fetch_add(1, std::memory_order_release);
			}
			if constexpr (t_EnableIdleSleep)
			{
				auto waiting = element->notifier.exchange(reinterpret_cast<std::binary_semaphore*>(BufferElement::READY_SENTINEL), std::memory_order_release);
				if (waiting != nullptr)
				{
					waiting->release();
				}
			}
			element->generation.store(writeGeneration, std::memory_order_release);
			return true;
		}
		ticket.ptr = element;
		ticket.generation = writeGeneration;
		m_writeContentionSplitter.fetch_add(1, std::memory_order_relaxed);
		return false;
	}

	void PushWait(t_ElementType const& val)
	{
		WriteReservationTicket ticket;
		while (ticket.ptr == nullptr)
		{
			if (TryPush(val, ticket))
			{
				return;
			}
		}

		BufferElement* element = reinterpret_cast<BufferElement*>(ticket.ptr);
		int64_t writeGeneration = ticket.generation;

		size_t spins = 0;
		while (element->generation.load(std::memory_order_acquire) != -(writeGeneration - 1)) [[unlikely]]
		{
			QAC_YIELD();
		}

		new (&element->item) t_ElementType(val);
		QAC_CONCURRENT_QUEUE_ASSERT(element->generation.load() == -(writeGeneration - 1));

		if constexpr (t_EnableBatch)
		{
			m_outstanding.fetch_add(1, std::memory_order_release);
		}
		if constexpr (t_EnableIdleSleep)
		{
			auto waiting = element->notifier.exchange(reinterpret_cast<std::binary_semaphore*>(BufferElement::READY_SENTINEL), std::memory_order_release);
			if (waiting != nullptr)
			{
				waiting->release();
			}
		}
		// ...then we signal that the element is ready to read and return true.
		element->generation.store(writeGeneration, std::memory_order_release);
	}

	void PushMoveWait(t_ElementType& val)
	{
		WriteReservationTicket ticket;
		while (ticket.ptr == nullptr)
		{
			if (TryPushMove(val, ticket))
			{
				return;
			}
		}

		BufferElement* element = reinterpret_cast<BufferElement*>(ticket.ptr);
		int64_t writeGeneration = ticket.generation;

		size_t spins = 0;
		while (element->generation.load(std::memory_order_acquire) != -(writeGeneration - 1)) [[unlikely]]
		{
			QAC_YIELD();
		}

		new (&element->item) t_ElementType(std::move(val));
		QAC_CONCURRENT_QUEUE_ASSERT(element->generation.load() == -(writeGeneration - 1));

		if constexpr (t_EnableBatch)
		{
			m_outstanding.fetch_add(1, std::memory_order_release);
		}
		if constexpr (t_EnableIdleSleep)
		{
			auto waiting = element->notifier.exchange(reinterpret_cast<std::binary_semaphore*>(BufferElement::READY_SENTINEL), std::memory_order_release);
			if (waiting != nullptr)
			{
				waiting->release();
			}
		}
		// ...then we signal that the element is ready to read and return true.
		element->generation.store(writeGeneration, std::memory_order_release);
	}

	/**
	 * @brief   Pop an item.  Will fail if the queue is empty.
	 *
	 * @param   val      A reference to a value, which will be filled with the contents of the dequeued element, if any.
	 *                   The move assignment operator will be called on the value, if one exists.
	 * @param   ticket   A reservation ticket which will hold cached data to improve performance.
	 *
	 * @return  true if the element was successfully enqueued, false otherwise
	 */
	inline bool TryPop(t_ElementType& val, ReadReservationTicket& ticket)
	{
		// See above for comments; this algorithm is identical except we're operating on m_readIdx
		// instead of m_writeIdx, and destructing the element instead of constructing it.
		BufferElement* element = reinterpret_cast<BufferElement*>(ticket.ptr);
		int64_t readGeneration = ticket.generation;

		if(!element) [[likely]]
		{
			size_t idx = m_readIdx.fetch_add(1, std::memory_order_acq_rel);
			element = m_buffer + (idx & (c_adjustedSize - 1));
			readGeneration = (idx >> c_generationOp) + 1;
		}

		if constexpr (t_EnableBatch)
		{
			m_outstanding.fetch_add(-1, std::memory_order_relaxed);
		}

		int64_t generation = element->generation.load(std::memory_order_acquire);
		if(generation == readGeneration) [[likely]]
		{
			ticket.ptr = nullptr;

			val = std::move(element->item);
			element->item.~t_ElementType();
			QAC_CONCURRENT_QUEUE_ASSERT(element->generation.load() == readGeneration);
			if constexpr (t_EnableIdleSleep)
			{
				element->notifier.store(nullptr, std::memory_order_release);
			}
			element->generation.store(-readGeneration, std::memory_order_release);
			//QAC_CONCURRENT_QUEUE_ASSERT(element->generation.load() == readGeneration);
			return true;
		}
		ticket.ptr = element;
		ticket.generation = readGeneration;
		m_readContentionSplitter.fetch_add(1, std::memory_order_relaxed);
		return false;
	}

	void PopWait(t_ElementType& val, size_t maxSpinsBeforeSemaphoreWait = QAC_DEFAULT_SPIN_COUNT)
	{
		ReadReservationTicket ticket;
		while (ticket.ptr == nullptr)
		{
			if (TryPop(val, ticket))
			{
				return;
			}
		}

		BufferElement* element = reinterpret_cast<BufferElement*>(ticket.ptr);
		int64_t readGeneration = ticket.generation;

		size_t spins = 0;
		while (element->generation.load(std::memory_order_acquire) != readGeneration) [[unlikely]]
		{
			QAC_YIELD();
			if constexpr (t_EnableIdleSleep)
			{
				if (++spins > maxSpinsBeforeSemaphoreWait)
				{
					// Edge case: Should not normally happen in production systems in properly-sized queues, but it CAN happen
					// if the queue is too small to handle the throughput that's being pushed through it.
					// If two consumer queues end up trying to read from the same slot at different generations because the consumers
					// lapped an entire buffer before a producer was able to finish, both consumers would end up writing to this and
					// only one would get woken up by the write, while the other one's semaphore would be lost.
					// To deal with that, we prevent multiple threads from idle sleeping on the same slot... if that case hits,
					// the additional threads will just spin loop until it resolves. This is considered not a severe issue, since
					// the existence of this case implies that a producer is actively writing to the slot already and therefore the
					// spin loop is actually the more performant option.
					std::binary_semaphore* previous = nullptr;
					std::binary_semaphore semaphore(0);
					if(element->notifier.compare_exchange_strong(previous, &semaphore, std::memory_order_acq_rel))
					{
						semaphore.acquire();
					}
				}
			}
		}

		val = std::move(element->item);
		element->item.~t_ElementType();
		QAC_CONCURRENT_QUEUE_ASSERT(element->generation.load() == readGeneration);
		if constexpr (t_EnableIdleSleep)
		{
			element->notifier.store(nullptr, std::memory_order_release);
		}
		element->generation.store(-readGeneration, std::memory_order_release);
		//QAC_CONCURRENT_QUEUE_ASSERT(element->generation.load() == readGeneration);
	}

	/**
	 * @brief   Attempt to push an item without passing in any tickets.
	 *
	 * @details This version of Push() does not require persistent tickets even on a return value of false
	 *          (or any tickets, for that matter). The performance of the common case will be similar to the other
	 *          version of Push(). In the case of failed writes, performance will be somewhat hampered,
	 *          but still superior to the performance of a successful write.
	 *
	 *
	 * @param   val      The value to equeue
	 *
	 * @return  true if the push succeeded, false if the push failed.
	 */
	inline bool TryPush(t_ElementType& val)
	{
		WriteReservationTicket ticket;
		bool reattempt = m_writeSubQueue.TryPop(ticket);
		if(!reattempt && m_failedWrites.load(std::memory_order_acquire) != 0)
		{
			return false;
		}
		if(TryPush(val, ticket))
		{
			if(reattempt)
			{
				m_failedWrites.fetch_sub(1, std::memory_order_acq_rel);
			}
			return true;
		}
		if(!reattempt)
		{
			m_failedWrites.fetch_add(1, std::memory_order_acq_rel);
		}
		m_writeSubQueue.Push(ticket, ((BufferElement*)ticket.ptr) - m_buffer + ticket.generation * t_QueueSize);
		return false;
	}

	/**
	 * @brief   Attempt to pop an item without passing in any tickets.
	 *
	 * @details This version of Pop() does not require persistent tickets even on a return value of false
	 *          (or any tickets, for that matter). The performance of the common case will be similar to the other
	 *          version of Pop(). In the case of failed reads, performance will be somewhat hampered,
	 *          but still superior to the performance of a successful read.
	 *
	 *
	 * @param   val      A reference to a value, which will be filled with the contents of the dequeued element, if any.
	 *                   The move assignment operator will be called on the value, if one exists.
	 *
	 * @return  true if the pop succeeded and tha value holds a valid item, false if the pop failed.
	 */
	inline bool TryPop(t_ElementType& val)
	{
		ReadReservationTicket ticket;
		bool reattempt = m_readSubQueue.TryPop(ticket);
		if(!reattempt && m_failedReads.load(std::memory_order_acquire) != 0)
		{
			return false;
		}
		if(TryPop(val, ticket))
		{
			if(reattempt)
			{
				m_failedReads.fetch_sub(1, std::memory_order_acq_rel);
			}
			return true;
		}
		if(!reattempt)
		{
			m_failedReads.fetch_add(1, std::memory_order_acq_rel);
		}
		m_readSubQueue.Push(ticket, ((BufferElement*)ticket.ptr) - m_buffer + ticket.generation * t_QueueSize);
		return false;
	}

	class BatchPopList
	{
	public:
		/**
		 * @brief Fetch the next element in the batch
		 *
		 * @details Normally, this function amounts to a pointer increment and a copy constructor and destructor
		 *          for t_ElementType. However, in scenarios where a batch spans the boundaries of two buffers,
		 *          this will iterate until it reaches the end of the current buffer, then lazy fetch elements
		 *          from successive buffers until the batch is exhausted.
		 */
		inline bool TryReadNext(t_ElementType& val)
		{
			if (m_primed) [[unlikely]]
			{
				val = t_ElementType(std::move(m_primer));
				m_primed = false;
				return true;
			}
			BufferElement* element = m_buffer + (m_idx & (c_adjustedSize - 1));
			int64_t readGeneration = (m_idx >> c_generationOp) + 1;
			if (element->generation.load(std::memory_order_acquire) != readGeneration)
			{
				return false;
			}
			val = t_ElementType(std::move(element->item));
			element->item.~t_ElementType();
			--m_remaining;
			++m_idx;
			if constexpr (t_EnableIdleSleep)
			{
				element->notifier.store(nullptr, std::memory_order_release);
			}
			element->generation.store(-readGeneration, std::memory_order_release);
			return true;
		}

		inline void ReadNextWait(t_ElementType& val, size_t maxSpinsBeforeSemaphoreWait = QAC_DEFAULT_SPIN_COUNT)
		{
			if (m_primed) [[unlikely]]
			{
				val = t_ElementType(std::move(m_primer));
				m_primed = false;
				return;
			}
			BufferElement* element = m_buffer + (m_idx & (c_adjustedSize - 1));
			int64_t readGeneration = (m_idx >> c_generationOp) + 1;

			size_t spins = 0;
			while (element->generation.load(std::memory_order_acquire) != readGeneration) [[unlikely]]
			{
				QAC_YIELD();
				if constexpr (t_EnableIdleSleep)
				{
					if (++spins > maxSpinsBeforeSemaphoreWait)
					{
						// Edge case: Should not normally happen in production systems in properly-sized queues, but it CAN happen
						// if the queue is too small to handle the throughput that's being pushed through it.
						// If two consumer queues end up trying to read from the same slot at different generations because the consumers
						// lapped an entire buffer before a producer was able to finish, both consumers would end up writing to this and
						// only one would get woken up by the write, while the other one's semaphore would be lost.
						// To deal with that, we prevent multiple threads from idle sleeping on the same slot... if that case hits,
						// the additional threads will just spin loop until it resolves. This is considered not a severe issue, since
						// the existence of this case implies that a producer is actively writing to the slot already and therefore the
						// spin loop is actually the more performant option.
						std::binary_semaphore* previous = nullptr;
						std::binary_semaphore semaphore(0);
						if (element->notifier.compare_exchange_strong(previous, &semaphore, std::memory_order_acq_rel))
						{
							semaphore.acquire();
						}
					}
				}
			}
			val = t_ElementType(std::move(element->item));
			element->item.~t_ElementType();
			--m_remaining;
			++m_idx;
			if constexpr (t_EnableIdleSleep)
			{
				element->notifier.store(nullptr, std::memory_order_release);
			}
			element->generation.store(-readGeneration, std::memory_order_release);
		}

		/*
		 * @brief Check if there are more items to iterate.
		 *
		 * @return true if there are elements left in the batch, false if the batch is exhausted
		 */
		inline bool More() { return (m_remaining > 0 || m_primed); }

		~BatchPopList()
		{
			while (More()) [[unlikely]]
			{
				t_ElementType data;
				ReadNextWait(data);
			}
		}

		BatchPopList(BatchPopList&& other)
			: m_idx(other.m_idx)
			, m_buffer(other.m_buffer)
			, m_remaining(other.m_remaining)
			, m_count(other.m_count)
		{
			other.m_idx = 0;
			other.m_buffer = nullptr;
			other.m_remaining = 0;
			other.m_count = 0;
		}

	protected:
		friend class ConcurrentBoundedQueue;
		BatchPopList()
		{}

		BatchPopList(BufferElement* buffer)
			: m_buffer(buffer)
		{}

		BatchPopList(BatchPopList const& other) = delete;
		BatchPopList(BatchPopList& other) = delete;
		BatchPopList& operator=(BatchPopList const& other) = delete;
		BatchPopList& operator=(BatchPopList& other) = delete;

		size_t m_idx;
		BufferElement* m_buffer;
		ssize_t m_remaining{ 0 };
		ssize_t m_count{ 0 };

		bool m_primed{ false };
		t_ElementType m_primer;
	};

	class BatchPushList
	{
	public:
		inline bool TryWriteNextMove(t_ElementType& val)
		{
			if (m_primer != nullptr) [[unlikely]]
			{
				new (&m_primer->item) t_ElementType(std::move(val));
				m_primer->generation.store(m_primerGeneration, std::memory_order_release);
				m_primer = nullptr;
				return true;
			}
			BufferElement* element = m_buffer + (m_idx & (c_adjustedSize - 1));
			int64_t writeGeneration = (m_idx >> c_generationOp) + 1;
			if (element->generation.load(std::memory_order_acquire) != -(writeGeneration - 1)) [[unlikely]]
			{
				return false;
			}

			new (&element->item) t_ElementType(std::move(val));
			QAC_CONCURRENT_QUEUE_ASSERT(element->generation.load() == -(writeGeneration - 1));

			element->generation.store(writeGeneration, std::memory_order_release);

			--m_remaining;
			++m_idx;
			return true;
		}

		inline bool TryWriteNext(t_ElementType const& val)
		{
			if (m_primer != nullptr) [[unlikely]]
			{
				new (&m_primer->item) t_ElementType(val);
				m_primer->generation.store(m_primerGeneration, std::memory_order_release);
				m_primer = nullptr;
				return true;
			}
			BufferElement* element = m_buffer + (m_idx & (c_adjustedSize - 1));
			int64_t writeGeneration = (m_idx >> c_generationOp) + 1;
			if (element->generation.load(std::memory_order_acquire) != -(writeGeneration - 1)) [[unlikely]]
			{
				return false;
			}

			new (&element->item) t_ElementType(val);
			QAC_CONCURRENT_QUEUE_ASSERT(element->generation.load() == -(writeGeneration - 1));

			if constexpr (t_EnableIdleSleep)
			{
				auto notifier = element->notifier.exchange(reinterpret_cast<std::binary_semaphore*>(BufferElement::READY_SENTINEL), std::memory_order_acq_rel);
				if (notifier != nullptr)
				{
					notifier->release();
				}
			}

			element->generation.store(writeGeneration, std::memory_order_release);

			--m_remaining;
			++m_idx;
			return true;
		}

		inline void WriteNextMoveWait(t_ElementType& val)
		{
			if (m_primer != nullptr) [[unlikely]]
			{
				new (&m_primer->item) t_ElementType(std::move(val));
				m_primer->generation.store(m_primerGeneration, std::memory_order_release);
				m_primer = nullptr;
				return;
			}
			BufferElement* element = m_buffer + (m_idx & (c_adjustedSize - 1));
			int64_t writeGeneration = (m_idx >> c_generationOp) + 1;

			size_t spins = 0;
			while (element->generation.load(std::memory_order_acquire) != -(writeGeneration - 1)) [[unlikely]]
			{
				QAC_YIELD();
			}

			new (&element->item) t_ElementType(std::move(val));
			QAC_CONCURRENT_QUEUE_ASSERT(element->generation.load() == -(writeGeneration - 1));

			if constexpr (t_EnableIdleSleep)
			{
				auto notifier = element->notifier.exchange(reinterpret_cast<std::binary_semaphore*>(BufferElement::READY_SENTINEL), std::memory_order_acq_rel);
				if (notifier != nullptr)
				{
					notifier->release();
				}
			}

			element->generation.store(writeGeneration, std::memory_order_release);

			--m_remaining;
			++m_idx;
		}

		inline void WriteNextWait(t_ElementType const& val)
		{
			if (m_primer != nullptr) [[unlikely]]
			{
				new (&m_primer->item) t_ElementType(val);
				m_primer->generation.store(m_primerGeneration, std::memory_order_release);
				m_primer = nullptr;
				return;
			}
			BufferElement* element = m_buffer + (m_idx & (c_adjustedSize - 1));
			int64_t writeGeneration = (m_idx >> c_generationOp) + 1;

			size_t spins = 0;
			while (element->generation.load(std::memory_order_acquire) != -(writeGeneration - 1)) [[unlikely]]
			{
				QAC_YIELD();
			}

			new (&element->item) t_ElementType(val);
			QAC_CONCURRENT_QUEUE_ASSERT(element->generation.load() == -(writeGeneration - 1));

			if constexpr (t_EnableIdleSleep)
			{
				auto notifier = element->notifier.exchange(reinterpret_cast<std::binary_semaphore*>(BufferElement::READY_SENTINEL), std::memory_order_acq_rel);
				if (notifier != nullptr)
				{
					notifier->release();
				}
			}

			element->generation.store(writeGeneration, std::memory_order_release);

			--m_remaining;
			++m_idx;
		}

		/*
		 * @brief Check if there are more items to iterate.
		 *
		 * @return true if there are elements left in the batch, false if the batch is exhausted
		 */
		inline bool More()
		{
			return (m_remaining > 0 || m_primer != nullptr);
		}

		~BatchPushList()
		{
			while (More()) [[unlikely]]
			{
				t_ElementType data;
				WriteNextWait(data);
			}
		}

		BatchPushList(BatchPushList&& other)
			: m_idx(other.m_idx)
			, m_buffer(other.m_buffer)
			, m_remaining(other.m_remaining)
			, m_count(other.m_count)
		{
			other.m_idx = 0;
			other.m_buffer = nullptr;
			other.m_remaining = 0;
			other.m_count = 0;
		}

	protected:
		friend class ConcurrentBoundedQueue;
		BatchPushList()
		{}

		BatchPushList(BufferElement* buffer)
			: m_buffer(buffer)
		{}

		BatchPushList(BatchPushList const& other) = delete;
		BatchPushList(BatchPushList& other) = delete;
		BatchPushList& operator=(BatchPushList const& other) = delete;
		BatchPushList& operator=(BatchPushList& other) = delete;

		size_t m_idx{ 0 };
		BufferElement* m_buffer;
		ssize_t m_remaining{ 0 };
		ssize_t m_count{ 0 };
		BufferElement* m_primer{ nullptr };
		int64_t m_primerGeneration;
	};

	BatchPushList CreatePushList()
	{
		return BatchPushList(m_buffer);
	}

	BatchPopList CreatePopList()
	{
		return BatchPopList(m_buffer);
	}


	void PushBatch(BatchPushList& enqueueList, ssize_t count)
	{
		if constexpr (!t_EnableBatch)
		{
			throw std::logic_error("Batch operations are not enabled on this queue.");
		}
		else
		{
			m_outstanding.fetch_add(count, std::memory_order_acq_rel);

			size_t startIdx = m_writeIdx.fetch_add(count, std::memory_order_acq_rel);
			enqueueList.m_idx = startIdx;
			enqueueList.m_count = count;
			enqueueList.m_remaining = count;
		}
	}

	void PushBatchWait(BatchPushList& enqueueList, ssize_t count, size_t maxSpinsBeforeSemaphoreWait = QAC_DEFAULT_SPIN_COUNT)
	{
		if constexpr (!t_EnableBatch)
		{
			throw std::logic_error("Batch operations are not enabled on this queue.");
		}
		else
		{
			PushBatch(enqueueList, count);

			if (!enqueueList.More()) [[unlikely]]
			{
				size_t idx = m_writeIdx.fetch_add(1, std::memory_order_acq_rel);
				BufferElement* element = m_buffer + (idx & (c_adjustedSize - 1));
				int64_t writeGeneration = (idx >> c_generationOp) + 1;

				// Check the generation flag. If it's not at current generation - 1, we can't overwrite it and have to return false,
				// storing this element on the reservation ticket to make sure we try it again later.
				int64_t generation = element->generation.load(std::memory_order_acquire);

				size_t spins = 0;
				while (element->generation.load(std::memory_order_acquire) != -(writeGeneration - 1)) [[unlikely]]
				{
					QAC_YIELD();
				}

				PushBatch(enqueueList, count - 1);
				enqueueList.m_primer = element;
				enqueueList.m_primerGeneration = writeGeneration;
			}
		}
	}

	/**
	 * @brief Retrieve multiple items from the queue. When maxCount is more than 1 or 2, PopBatch can offer orders of
	 *        magnitude greater performance than either Pop option.
	 *
	 * @details In contrast with the other two Pop() options, PopBatch() takes advantage of the contiguous storage
	 *          structure of QACQueue to reduce contention by allowing the retrieval of multiple items from the queue with
	 *          only a single atomic increment. A second atomic operation is used to keep track of how many elements it's allowed
	 *          to read to ensure it doesn't over-consume the queue. When it does, a third atomic operation is used to correct.
	 *
	 *          However, while the additional atomic operations on the queue result in slower performance for individual item
	 *          pops, this is vastly made up for when reading larger numbers of items by reducing the contention on each
	 *          individual read - while 100 normal pop operations would involve a total of 100 atomic increments on contentuous
	 *          variables (when batching is disabled), a batch read of 100 items involves a total of 2 atomic increments on
	 *          contentuous variables in the optimistic case, and 3 in the pessimistic case. Additionally, since multiple elements
	 *          are retrieved in a single function call, the user code can spend more time actually processing the elements it has
	 *          retrieved, which means there are fewer overall function calls on the queue, and thus, those 3 operations are far
	 *          less likely to actually experience contention resulting in cache misses, and the code doing the processing is able
	 *          to safely rely on the cache locality of the data it receives without concern for losing that locality to contention
	 *          while iterating them.
	 *
	 *          There are, however, drawbacks to the batch API.
	 *
	 *          First, simply the act of enabling batch push and pop makes the non-batched operations a little bit slower,
	 *          as it adds a requirement for them to update the outstanding count in order for batched operations to function properly
	 *          when the two are mixed.
	 *
	 *          Second, batched operations with a maxCount of 1 are slower than ticketed operations. In general, batch size of 1 will see
	 *          close to the same performance as the ticket-free API for successful pops when batch mode is enabled, and will be slightly
	 *          slower than ticket-free pops with batch mode disabled. However...
	 *
	 *          Third (to be taken with a LARGE grain of salt), while successful pops in batch mode are extremely fast,
	 *          pop-from-empty can be much slower than other options depending on your use case. If you're doing other processing
	 *          when the queue is empty, or sleeping when the queue is empty, and thus keeping contention low, you'll likely see
	 *          pop-from-empty performing as well as a successful pop. But if your threads are all looping on trying to read
	 *          from the empty queue, the number of attempts they can do per second will be dramatically lower due to the increased
	 *          contention this causes. (However, if you're in that situation, you're not really DOING anything, so practically
	 *          speaking... does it really matter that you're doing less of nothing?)
	 *
	 *          Finally, mixing the normal API and the batch API can lead to unexpected behavior. The non-batch API removes items from
	 *          the pool that the batch API can read from *even when their reads fail*, so if you perform a non-batch read that returns false,
	 *          then push an item, then attempt to pop that item using the batch API, you will find the batch API returns 0 items
	 *          instead of the expected 1, because that item was already reserved by the non-batch API before it was written.
	 *          See the documentation for Pop(t_ElementType& val, ReadReservationTicket& ticket) for more information.
	 *
	 * @param   result    Out variable in which to store the retrieved batch data. May safely be reused once all items have been consumed.
	 *
	 * @param   maxCount  Maximum number of elements to retrieve. If the full requested amount doesn't exist in the queue, a partial result
	 *                    will be returned.
	 */
	void PopBatch(BatchPopList& result, ssize_t maxCount)
	{
		if constexpr (!t_EnableBatch)
		{
			throw std::logic_error("Batch operations are not enabled on this queue.");
		}
		else
		{
			/*while (result.More()) [[unlikely]]
			{
				t_ElementType data;
				result.ReadNextWait(data);
			}*/
			ssize_t newOutstanding = std::max(m_outstanding.fetch_sub(maxCount, std::memory_order_acq_rel) - maxCount, -maxCount);
			ssize_t batchSize = maxCount;
			if (newOutstanding < 0) [[unlikely]]
			{
				batchSize += newOutstanding;
				newOutstanding = m_outstanding.fetch_sub(newOutstanding, std::memory_order_release) - newOutstanding;
				if (batchSize <= 0) [[likely]]
				{
					return;
				}
			}

			size_t startIdx = m_readIdx.fetch_add(batchSize, std::memory_order_acq_rel);
			result.m_idx = startIdx;
			result.m_count = batchSize;
			result.m_remaining = batchSize;
		}
	}

	void PopBatchWait(BatchPopList& result, ssize_t maxCount, size_t maxSpinsBeforeSemaphoreWait = QAC_DEFAULT_SPIN_COUNT)
	{
		if constexpr (!t_EnableBatch)
		{
			throw std::logic_error("Batch operations are not enabled on this queue.");
		}
		else
		{
			PopBatch(result, maxCount);
			if (!result.More())
			{
				t_ElementType primer;
				PopWait(primer, maxSpinsBeforeSemaphoreWait);
				PopBatch(result, maxCount - 1);
				result.m_primed = true;
				result.m_primer = t_ElementType(std::move(primer));
			}
		}
	}

private:
	constexpr static size_t c_adjustedSize = detail::nextPowerOf2(t_QueueSize);
	constexpr static int64_t c_generationOp = detail::log2(c_adjustedSize);
	
	template<int64_t t_Size>
	static constexpr int64_t assertSize()
	{
		static_assert(t_Size < 32, "Queue size is too large");
		return t_Size;
	}
	constexpr static int64_t asserted = assertSize<c_generationOp>();

	alignas(QAC_CACHELINE_SIZE) std::atomic<size_t> m_readIdx;
	alignas(QAC_CACHELINE_SIZE) std::atomic<size_t> m_writeIdx;
	alignas(QAC_CACHELINE_SIZE) BufferElement m_buffer[c_adjustedSize];
	alignas(QAC_CACHELINE_SIZE) detail::ReservationTicketSubQueue<ReadReservationTicket, t_AllocatorType> m_readSubQueue;
	alignas(QAC_CACHELINE_SIZE) std::atomic<ssize_t> m_failedReads;
	alignas(QAC_CACHELINE_SIZE) detail::ReservationTicketSubQueue<WriteReservationTicket, t_AllocatorType> m_writeSubQueue;
	alignas(QAC_CACHELINE_SIZE) std::atomic<ssize_t> m_failedWrites;
	alignas(QAC_CACHELINE_SIZE) std::atomic<ssize_t> m_outstanding;
	alignas(QAC_CACHELINE_SIZE) std::atomic<ssize_t> m_writeContentionSplitter;
	alignas(QAC_CACHELINE_SIZE) std::atomic<ssize_t> m_readContentionSplitter;
	alignas(QAC_CACHELINE_SIZE) bool pad;
};