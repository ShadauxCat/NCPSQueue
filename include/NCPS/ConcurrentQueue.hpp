/*
 * MIT License
 *
 * Copyright (c) 2016 Jaedyn Kitt Draper
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

#pragma once

#include <atomic>
#include <memory>
#include <string.h>

#include <limits>

#include <type_traits>
#include <stdexcept>

#if defined(_WIN32)
#    include <BaseTsd.h>
#endif

#if defined(_MSC_VER) && !defined(__clang__)
#    define NCPS_LIKELY(x) (x)
#    define NCPS_UNLIKELY(x) (x)
#    define NCPS_FORCE_NO_INLINE __declspec(noinline)
#elif defined(__INTEL_COMPILER_BUILD_DATE) || defined(__clang__) || defined(__GNUC__)
#    define NCPS_LIKELY(x) (__builtin_expect(!!(x), 1))
#    define NCPS_UNLIKELY(x) (__builtin_expect(!!(x), 0))
#    define NCPS_FORCE_NO_INLINE __attribute__((noinline))
#endif

#define NCPS_CONCAT_2(left, right) left##right
#define NCPS_CONCAT(left, right) NCPS_CONCAT_2(left, right)

#define NCPS_ABORT_MSG_F(msg, ...)       \
    fprintf(stderr, msg, ##__VA_ARGS__); \
    fputs("\n", stderr);                 \
    fflush(stderr);                      \
    std::terminate();

#ifndef NCPS_CACHELINE_SIZE
#    define NCPS_CACHELINE_SIZE 64
#endif

#define NCPS_PAD_CACHELINE CachelinePad NCPS_CONCAT(NCPS_CONCAT(pad##_, __LINE__), __)

#ifndef NCPS_CONCURRENT_QUEUE_DEBUG_ASSERTS
#    define NCPS_CONCURRENT_QUEUE_DEBUG_ASSERTS 0
#endif

#if NCPS_CONCURRENT_QUEUE_DEBUG_ASSERTS
#    define NCPS_CONCURRENT_QUEUE_ASSERT(val)               \
        if (!(val)) {                                       \
            NCPS_ABORT_MSG_F("Assertion failed: %s", #val); \
        }
#else
#    define NCPS_CONCURRENT_QUEUE_ASSERT(val)
#endif

namespace NCPS {
#if defined(_WIN32)
using ssize_t = SSIZE_T;
#endif

typedef unsigned char CachelinePad[NCPS_CACHELINE_SIZE];
namespace detail {
template <typename t_ElementType, size_t t_BlockSize>
class Buffer;

template <typename t_ElementType, typename t_AllocatorType>
class ReservationTicketSubQueue;

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

template <typename t_IntegerType>
constexpr t_IntegerType nextPowerOf2(t_IntegerType const x, typename std::enable_if<sizeof(t_IntegerType) == 8>::type* = nullptr) {
    return pow2_1(uint64_t(x - 1));
}

template <typename t_IntegerType>
constexpr t_IntegerType nextPowerOf2(t_IntegerType const x, typename std::enable_if<sizeof(t_IntegerType) == 4>::type* = nullptr) {
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

template <typename t_ElementType, size_t t_BlockSize = 8192, bool t_EnableBatch = false, typename t_AllocatorType = std::allocator<t_ElementType>>
struct ReadReservationTicket;

template <typename t_ElementType>
struct BoundedReadReservationTicket;

template <typename t_ElementType>
struct BoundedWriteReservationTicket;

template <typename t_ElementType, size_t t_BlockSize = 8192, bool t_EnableBatch = false, typename t_AllocatorType = std::allocator<t_ElementType>>
class ConcurrentQueue;

template <typename t_ElementType, size_t t_QueueSize, typename t_AllocatorType = std::allocator<t_ElementType>>
class ConcurrentBoundedQueue;
}  // namespace NCPS

/**
 * @class   NCPS::detail::Buffer
 *
 * @brief   Simple buffer class representing a single allocated block within an unbounded concurrent queue.
 *
 * @details Provides concurrent read and write support. This class is the one that actually handles
 *          the majority of the atomic operations, as the read and write position are both
 *          contained within this class.
 */
template <typename t_ElementType, size_t t_BlockSize>
class NCPS::detail::Buffer {
   public:
    struct BufferElement {
        std::atomic<bool> ready;
        t_ElementType     item;
    };

    Buffer()
        : m_next(nullptr),
          m_refCount(t_BlockSize + 2)  // One for each element, one for the writeBuffer pointer, and one for the readBuffer pointer
          ,
          m_readPos(reinterpret_cast<BufferElement*>(m_buffer)),
          m_writePos(reinterpret_cast<BufferElement*>(m_buffer)),
          m_end(reinterpret_cast<BufferElement*>(m_buffer) + t_BlockSize) {
        // Memset the buffer block to 0 so all 'ready' flags read as 'false'
        memset(m_buffer, 0, sizeof(BufferElement) * t_BlockSize);
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
    inline void Clear() {
        m_refCount.store(t_BlockSize + 2);
        memset(m_buffer, 0, sizeof(BufferElement) * t_BlockSize);
    }

    /**
     * @brief   Resets the write position
     */
    inline void SetWritePosition() { m_writePos.store(reinterpret_cast<BufferElement*>(m_buffer)); }

    /**
     * @brief   Resets the read position
     */
    inline void SetReadPosition() { m_readPos.store(reinterpret_cast<BufferElement*>(m_buffer)); }

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
    inline void SetNext(Buffer* next) { m_next.store(next, std::memory_order_release); }

    /**
     * @brief   Get the next pointer for this buffer.
     *
     * @details Like with SetNext, the caller is responsible for detecting when the element
     *          they received is outside the boundaries of the buffer and retrieving the next buffer.
     *
     * @return  Pointer to the next buffer. If there is no next, returns nullptr.
     */
    inline Buffer* GetNext() { return m_next.load(std::memory_order_acquire); }

    /**
     * @brief   Retrieve a pointer to an element for dequeue.
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
    inline BufferElement* GetForRead() { return m_readPos.fetch_add(1, std::memory_order_acq_rel); }

    inline BufferElement* GetBatchForRead(ssize_t count) { return m_readPos.fetch_add(count, std::memory_order_acq_rel); }

    /**
     * @brief   Retrieve a pointer to an element for enqueue.
     *
     * @details This function is thread-safe and is guaranteed to return an element reserved
     *          for only the caller. There's no need to synchronize access to this element.
     *          Note, however, that the returned pointer may be beyond the end of the buffer,
     *          and it is the responsibility of the caller to handle that case by allocating a new
     *          buffer.
     *
     * @return  A pointer to an element. If the pointer is < this->GetEnd(), it is valid to write to.
     */
    inline BufferElement* GetForWrite() { return m_writePos.fetch_add(1, std::memory_order_acq_rel); }

    inline BufferElement* GetBatchForWrite(ssize_t count) { return m_writePos.fetch_add(count, std::memory_order_acq_rel); }

    /**
     * @brief   Get a pointer to the end of the queue. If a returned pointer is >= this value, it's not valid,
     *          and a reallocation or call to GetNext() is required.
     *
     * @return  A pointer to the end of the buffer.
     */
    inline BufferElement const* GetEnd() const { return m_end; }

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
    inline ssize_t DecRef() { return m_refCount.fetch_sub(1, std::memory_order_acq_rel) - 1; }

    /**
     * @brief   Special version of DecRef that will decrease the reference count multiple times with a single atomic operation
     *
     * @param   amount   the amount by which to decrement the count
     * @return  The new reference count after this operation has completed. If the result is 0, the buffer should be moved to the end of the buffer list.
     */
    inline ssize_t DecRef(ssize_t amount) { return m_refCount.fetch_sub(amount, std::memory_order_acq_rel) - amount; }

    /**
     * @brief   Clean up the buffer. This is NOT thread-safe.
     */
    void Cleanup() {
        BufferElement* element = this->GetForRead();
        while (element < m_end && element->ready) {
            element->item.~t_ElementType();
            element = this->GetForRead();
        }
    }

   private:
    NCPS_PAD_CACHELINE;
    std::atomic<Buffer*> m_next;
    NCPS_PAD_CACHELINE;
    std::atomic<ssize_t> m_refCount;
    NCPS_PAD_CACHELINE;
    std::atomic<BufferElement*> m_readPos;
    NCPS_PAD_CACHELINE;
    std::atomic<BufferElement*> m_writePos;
    NCPS_PAD_CACHELINE;

    char                       m_buffer[t_BlockSize * sizeof(BufferElement)];
    BufferElement const* const m_end;
};

/**
 * @class   NCPS::ReadReservationTicket
 *
 * @brief   Represents a reservation to read an element that hasn't been written to yet.
 *
 * @warning You must call queue.InitializeReservationTicket() on this before using it!
 */
template <typename t_ElementType, size_t t_BlockSize, bool t_EnableBatch, typename t_AllocatorType>
struct NCPS::ReadReservationTicket {
    detail::Buffer<t_ElementType, t_BlockSize>*                                        buffer{nullptr};
    typename detail::Buffer<t_ElementType, t_BlockSize>::BufferElement*                ptr{nullptr};
    NCPS::ConcurrentQueue<t_ElementType, t_BlockSize, t_EnableBatch, t_AllocatorType>* queue{nullptr};
    int                                                                                count{0};

    ReadReservationTicket() {}

    ~ReadReservationTicket();

    ReadReservationTicket(ReadReservationTicket const& other) = delete;
    ReadReservationTicket& operator=(ReadReservationTicket const& other) = delete;

    ReadReservationTicket(ReadReservationTicket&& other) noexcept : buffer(other.buffer), ptr(other.ptr), queue(other.queue) {
        other.buffer = nullptr;
        other.ptr    = nullptr;
    }
    ReadReservationTicket& operator=(ReadReservationTicket&& other) noexcept {
        buffer       = other.buffer;
        ptr          = other.ptr;
        queue        = other.queue;
        other.buffer = nullptr;
        other.ptr    = nullptr;
        return *this;
    }
};

template <typename t_ElementType, typename t_AllocatorType>
class NCPS::detail::ReservationTicketSubQueue {
   public:
    ReservationTicketSubQueue(size_t const maxConcurrentTicketlessReads) : m_buffer(maxConcurrentTicketlessReads == 0 ? nullptr : m_allocator.allocate(detail::nextPowerOf2(maxConcurrentTicketlessReads))), m_readIdx(0), m_writeIdx(0), m_mask(detail::nextPowerOf2(maxConcurrentTicketlessReads) - 1) {
        if (m_buffer) {
            memset(m_buffer, 0, maxConcurrentTicketlessReads * sizeof(*m_buffer));
        }
        for (size_t i = 0; i < maxConcurrentTicketlessReads; ++i) {
            m_buffer[i].pos = -1;
        }
    }

    ~ReservationTicketSubQueue() {
        if (m_buffer) {
            m_allocator.deallocate(m_buffer, m_mask + 1);
        }
    }

    ssize_t Enqueue(t_ElementType& ticket) {
        ssize_t pos = m_writeIdx.load(std::memory_order_acquire);
        for (;;) {
            ssize_t  idx        = pos & m_mask;
            Element& failedRead = m_buffer[idx];
            if (m_writeIdx.compare_exchange_weak(pos, pos + 1, std::memory_order_acq_rel)) {
                while (failedRead.pos.load(std::memory_order_acquire) != -1) {
                    // Another thread is likely trying to read this one still.
                    // This can happen even when max concurrent reads is not exceeded, but is rare.
                    // We will block on a loop until we're able to write.
                }
                failedRead.item = std::move(ticket);
                failedRead.pos.store(pos, std::memory_order_release);
                return pos;
            }
        }
    }

    bool Dequeue(t_ElementType& ticket, ssize_t maxPos = (std::numeric_limits<ssize_t>::max)()) {
        ssize_t pos = m_readIdx.load(std::memory_order_acquire);
        for (;;) {
            if (pos >= maxPos) {
                return false;
            }

            ssize_t  idx        = pos & m_mask;
            Element& failedRead = m_buffer[idx];
            if (failedRead.pos.load(std::memory_order_acquire) != pos) {
                return false;
            }
            if (m_readIdx.compare_exchange_weak(pos, pos + 1, std::memory_order_acq_rel)) {
                ticket = std::move(failedRead.item);
                failedRead.pos.store(-1, std::memory_order_release);
                return true;
            }
        }
    }

   private:
    struct Element {
        std::atomic<ssize_t> pos;
        t_ElementType        item;
    };

    typename t_AllocatorType::template rebind<Element>::other m_allocator;

    Element* m_buffer;
    NCPS_PAD_CACHELINE;
    std::atomic<ssize_t> m_readIdx;
    NCPS_PAD_CACHELINE;
    std::atomic<ssize_t> m_writeIdx;
    NCPS_PAD_CACHELINE;
    size_t const m_mask;
};

/**
 * class    NCPS::ConcurrentQueue
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
 *          it's wait-free population agnostic for the vast majority of enqueues and dequeues.
 *          So long as the reservation ticket used for dequeues is kept alive, this queue is extremely fast.
 *          Be warned, however, that if you don't keep the reservation ticket alive, the queue will still work,
 *          but dequeues will be somewhat slower - while the ticket stays alive, it batches reference counting
 *          operations, but each time the reservation ticket destructs it has to apply those reference count changes.
 *          Which means if it destructs after every dequeue, there's an atomic fetch_sub that will happen after each
 *          queue. It sounds like it's not a big deal, but removing one fetch_sub operation from each dequeue
 *          can have a surprisingly large performance impact.
 *
 *          Note, though, that the reservation tickets MUST BE KEPT ALIVE if dequeue returns false, or an element
 *          in the queue will become unreachable and will never be read, and memory for the buffer containing it
 *          will not be able to be reused and will cause a memory leak.
 *
 * @tparam  t_ElementType       the type of element to store in the queue
 *
 * @tparam  t_BlockSize         the number of elements to allocate at a time.
 *                              Generally speaking, most queues will end up seeing double this number in use,
 *                              assuming it's reasonably large and enqueue operations don't outpace dequeue operations.
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
 *                              must support `rebind`. For ticket-free dequeue operations, ReadReservationTickets will also
 *                              be allocated after failed reads, and deallocated on subsequent successful reads.
 */
template <typename t_ElementType, size_t t_BlockSize, bool t_EnableBatch, typename t_AllocatorType>
class NCPS::ConcurrentQueue {
   public:
    using ReadReservationTicket = NCPS::ReadReservationTicket<t_ElementType, t_BlockSize, t_EnableBatch, t_AllocatorType>;
    using Buffer                = NCPS::detail::Buffer<t_ElementType, t_BlockSize>;

    friend struct NCPS::ReadReservationTicket<t_ElementType, t_BlockSize, t_EnableBatch, t_AllocatorType>;

   protected:
    /**
     * @brief   Decrement the ref count on the buffer and move it to the end of the queue if necessary
     *
     * @param   buffer   The buffer to decref and free
     */
    inline void consume_(Buffer* buffer, ssize_t amount) {
        ssize_t ret = buffer->DecRef(amount);
        if (NCPS_UNLIKELY(ret == 0)) {
            while (m_reallocatingBuffer.exchange(true, std::memory_order_seq_cst)) {
            }
            swapToEnd_(buffer);
            m_reallocatingBuffer.store(false);
        }
    }

   protected:
    ConcurrentQueue(ConcurrentQueue const& other) = delete;
    ConcurrentQueue& operator=(ConcurrentQueue const& other) = delete;
    ConcurrentQueue(ConcurrentQueue&& other)                 = delete;
    ConcurrentQueue& operator=(ConcurrentQueue&& other) = delete;

    /**
     * @brief   Move a buffer to the end of the buffer list
     *
     * @details This needs to be called within the m_reallocatingBuffer guard.
     */
    inline void swapToEnd_(Buffer* buffer) {
        Buffer* tail = m_tail.load(std::memory_order_acquire);
        buffer->Clear();
        NCPS_CONCURRENT_QUEUE_ASSERT(tail->GetNext() == nullptr);
        NCPS_CONCURRENT_QUEUE_ASSERT(buffer != m_writeBuffer.load());
        NCPS_CONCURRENT_QUEUE_ASSERT(buffer != m_readBuffer.load());
        NCPS_CONCURRENT_QUEUE_ASSERT(buffer != tail);
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
    inline void consumeUnlocked_(Buffer* buffer) {
        ssize_t ret = buffer->DecRef();
        if (NCPS_UNLIKELY(ret == 0)) {
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
    inline void consumeUnlocked_(Buffer* buffer, ssize_t amount) {
        ssize_t ret = buffer->DecRef(amount);
        if (NCPS_UNLIKELY(ret == 0)) {
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
    NCPS_FORCE_NO_INLINE void fetchNextWriteBuffer_(typename Buffer::BufferElement*& element, Buffer*& buffer, ssize_t batchCount) {
        // Just because we won the lottery, though, doesn't mean we're the only ones who won.
        // Someone else may have already claimed the prize. We need to make sure we still
        // need to do this before we actually do it.
        // We do that by re-fetching the buffer and element and re-doing the above check.
        buffer  = m_writeBuffer.load(std::memory_order_acquire);
        element = buffer->GetBatchForWrite(batchCount);

        if (element >= buffer->GetEnd()) {
            // If we're still past the end, time to replace the write buffer.
            // First we get the next buffer in the list. If one exists, it's one
            // we've previously used up and are now taking for reuse.
            Buffer* newBuffer = buffer->GetNext();
            if (!newBuffer) {
                // If we get nullptr back from this, then we actually need to allocate.
                newBuffer = m_allocator.allocate(1);
                new (newBuffer) Buffer();
                buffer->SetNext(newBuffer);
                if (buffer == m_tail.load(std::memory_order_acquire)) {
                    m_tail.store(newBuffer, std::memory_order_release);
                }
            }
            NCPS_CONCURRENT_QUEUE_ASSERT(newBuffer != buffer);
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
            buffer  = newBuffer;
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
    NCPS_FORCE_NO_INLINE bool fetchNextReadBuffer_(typename Buffer::BufferElement*& element, Buffer*& buffer, ReadReservationTicket& ticket) {
        buffer  = m_readBuffer.load(std::memory_order_acquire);
        element = buffer->GetForRead();

        if (element >= buffer->GetEnd()) {
            Buffer* nextBuffer = buffer->GetNext();
            if (nextBuffer == nullptr) {
                // If there isn't a new buffer to read from, we're just going to return false.
                // In this case, we're not updating any information in the ticket.
                // By virtue of the fact that we're here, the ticket's ptr is already null
                // And since there's no next buffer to read from, and we don't want to allocate one when we're just reading,
                // we're just going to keep it null and redo this work next time.
                return false;
            }
            nextBuffer->SetReadPosition();
            NCPS_CONCURRENT_QUEUE_ASSERT(nextBuffer != buffer);

            m_readBuffer.store(nextBuffer, std::memory_order_release);
            consumeUnlocked_(buffer);
            buffer  = nextBuffer;
            element = buffer->GetForRead();
        }
        // This bit allows us to be very efficient about reference counting
        // by keeping the count on a non-shared variable and only performing operations on
        // the shared variable in batches. Only when a consumer thread stops reading from a buffer
        // do we adjust that buffer's reference count, meaning each buffer only has to have a DecRef()
        // performed once per consumer thread, plus 2 additional times for m_readBuffer and m_writeBuffer changing.
        // This is a fairly significant performance boost.
        if (ticket.count != 0) {
            consumeUnlocked_(ticket.buffer, ticket.count);
        }
        ticket.count = 0;
        // We then set the ticket's buffer to the new buffer we've obtained.
        ticket.buffer = buffer;
        return true;
    }

    NCPS_FORCE_NO_INLINE bool fetchNextReadBuffer_(typename Buffer::BufferElement*& element, Buffer*& buffer, ssize_t count) {
        buffer  = m_readBuffer.load(std::memory_order_acquire);
        element = buffer->GetBatchForRead(count);

        if (element >= buffer->GetEnd()) {
            Buffer* nextBuffer = buffer->GetNext();
            if (nextBuffer == nullptr) {
                // If there isn't a new buffer to read from, we're just going to return false.
                // In this case, we're not updating any information in the ticket.
                // By virtue of the fact that we're here, the ticket's ptr is already null
                // And since there's no next buffer to read from, and we don't want to allocate one when we're just reading,
                // we're just going to keep it null and redo this work next time.
                return false;
            }
            nextBuffer->SetReadPosition();
            NCPS_CONCURRENT_QUEUE_ASSERT(nextBuffer != buffer);

            m_readBuffer.store(nextBuffer, std::memory_order_release);
            consumeUnlocked_(buffer);
            buffer  = nextBuffer;
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
    inline typename Buffer::BufferElement& getNextElement_() {
        // First we try to retrieve an element for write from our write buffer.
        Buffer*                         buffer  = m_writeBuffer.load(std::memory_order_acquire);
        typename Buffer::BufferElement* element = buffer->GetForWrite();

        // The write buffer may be full. If it is, it'll return a pointer past the end of the buffer.
        // If that happens we have to retrieve or allocate a new buffer.
        // Strictly speaking, this section violates lock-free because the allocation happens within a spin-lock.
        // Practically speaking, this spin-lock happens so infrequently in a queue with a proper block size that
        // it may as well never happen at all.
        while (NCPS_UNLIKELY(element >= buffer->GetEnd())) {
            // When we get here, we use a simple atomic boolean as a spin lock.
            // We perform an exchange() on it - if it returns false, that means we won the lottery
            // because we were the first to set it true.
            if (!m_reallocatingBuffer.exchange(true, std::memory_order_seq_cst)) {
                fetchNextWriteBuffer_(element, buffer, 1);
                m_reallocatingBuffer.store(false, std::memory_order_release);
            }
        }

        // Now we've gotten an element! We can return it back to the caller!
        return *element;
    }

   public:
    ConcurrentQueue(size_t const maxConcurrentTicketlessReads = 0) : m_readBuffer(nullptr), m_reallocatingBuffer(false), m_writeBuffer(nullptr), m_tail(nullptr), m_subQueue(maxConcurrentTicketlessReads), m_failedReads(0), m_outstanding(0) {
        Buffer* buffer = m_allocator.allocate(1);
        new (buffer) Buffer();
        m_readBuffer  = buffer;
        m_writeBuffer = buffer;
        m_tail        = buffer;
    }

    ~ConcurrentQueue() {
        Buffer* buffer = m_readBuffer.load(std::memory_order_acquire);
        while (buffer) {
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
     *          when it's constructed. The main purpose of this is to save Dequeue() from having to
     *          add an if-check to detect an uninitialized buffer. Branching is expensive.
     *
     * @param   ticket   the ticket to initialize
     */
    void InitializeReservationTicket(ReadReservationTicket& ticket) {
        ticket.buffer = m_readBuffer.load(std::memory_order_acquire);
        ticket.queue  = this;
    }

    /**
     * @brief   Enqueue an item by reference, calling the copy constructor. Will not fail (unless OOM).
     *
     * @param   val   The value to equeue
     */
    inline void Enqueue(t_ElementType const& val) {
        typename Buffer::BufferElement& element = getNextElement_();
        new (&element.item) t_ElementType(val);
        NCPS_CONCURRENT_QUEUE_ASSERT(element.ready.load() == false);
        element.ready.store(true, std::memory_order_release);
        if constexpr (t_EnableBatch) {
            m_outstanding.fetch_add(1, std::memory_order_release);
        }
    }

    /**
     * @brief   Enqueue an item by rvalue, calling the move constructor. Will not fail (unless OOM).
     *
     * @param   val   The value to equeue
     */
    inline void Enqueue(t_ElementType&& val) {
        typename Buffer::BufferElement& element = getNextElement_();
        new (&element.item) t_ElementType(std::move(val));
        NCPS_CONCURRENT_QUEUE_ASSERT(element.ready.load() == false);
        element.ready.store(true, std::memory_order_release);
        if constexpr (t_EnableBatch) {
            m_outstanding.fetch_add(1, std::memory_order_release);
        }
    }

    /**
     * @brief   Enqueue a batch of items. The items will be copy-constructed from the array. Will not fail (unless OOM).
     *
     * @details Compared to Enqueue(), when enqueuing multiple items in sequence, EnqueueBatch() reduces the number of
     *          contentuous atomic variable operations to only two per batch, thus dramatically increasing performance.
     *          However, when only a single item is being enqueued, the non-batched enqueue will perform slightly better
     *          (though not better enough to warrant the cost of a branch to detect if the number is 1 when it isn't known
     *          at compile time).
     *
     * @param   vals   A C-style array of objects to enqueue
     * @param   count  The number of items in the array. (Note this is not necessarily the memory size of the array, but the number of elements that should actually be read from it.)
     */
    inline void EnqueueBatch(t_ElementType* vals, ssize_t count) {
        if constexpr (!t_EnableBatch) {
            throw std::logic_error("Batch operations are not enabled on this queue.");
        } else {
            Buffer*                               buffer  = m_writeBuffer.load(std::memory_order_acquire);
            typename Buffer::BufferElement*       element = buffer->GetBatchForWrite(count);
            typename Buffer::BufferElement const* end     = buffer->GetEnd();
            for (ssize_t i = 0; i < count; ++i) {
                // The write buffer may be full. If it is, it'll return a pointer past the end of the buffer.
                // If that happens we have to retrieve or allocate a new buffer.
                // Strictly speaking, this section violates lock-free because the allocation happens within a spin-lock.
                // Practically speaking, this spin-lock happens so infrequently in a queue with a proper block size that
                // it may as well never happen at all.
                while (NCPS_UNLIKELY(element >= end)) {
                    // When we get here, we use a simple atomic boolean as a spin lock.
                    // We perform an exchange() on it - if it returns false, that means we won the lottery
                    // because we were the first to set it true.
                    if (!m_reallocatingBuffer.exchange(true, std::memory_order_seq_cst)) {
                        fetchNextWriteBuffer_(element, buffer, count - i);
                        m_reallocatingBuffer.store(false, std::memory_order_release);
                        end = buffer->GetEnd();
                    }
                }
                new (&element->item) t_ElementType(vals[i]);
                element->ready.store(true, std::memory_order_release);
                ++element;
            }
            ssize_t outstanding = m_outstanding.fetch_add(count, std::memory_order_release);
        }
    }

    /**
     * @brief   Attempt to dequeue an item. Not guaranteed to succeed, as the queue may be empty.
     *
     * @details To improve performance, all dequeue operations will cache data in the ReadReservationTicket parameter.
     *
     *          If the dequeue operation returns false, this parameter MUST be held onto and passed back into Dequeue()
     *          or an element in the queue will become permanently inaccessible.
     *
     *          It doesn't matter what thread passes the ticket back in, but it cannot be disposed of so long as
     *          Dequeue() has returned false.
     *
     *          For emphasis: The ticket MUST be passed back to the queue again in order to read all elements from the queue.
     *          Ticketed dequeues operate like a backorder system. If you make a dequeue and an item is ready to read, it will
     *          be given to you on the spot. If the queue is empty, it populates the passed ReadReservationTicket with a
     *          *reservation* for the spot it tried to read. When that spot is later written to, you must return with the same
     *          ticket - with the receipt, to continue the backorder metaphor - in order to read it. It will not be given
     *          to another customer, no matter what!
     *
     *          The reason for this is that, to achieve its speed, NCPSQueue dequeues items *optimistically*, assuming something
     *          is ready to read when you attempt to read it. It increments the read head based on this assumption. This
     *          allows NCPSQueue to avoid complex compare-and-swap operations and keep its common-case operation to a single
     *          atomic increment per enqueue or dequeue. The downside, though, is when it's incorrect on its optimistic dequeue,
     *          it cannot safely correct - it can't simply decrement the read head because a race condition exists where thread
     *          A attempts to read index 0, to find it not yet written, then thread B enqueues indexes 0 and 1, and then thread
     *          C successfully reads index 1, believing index 0 to already have been read because thread A incremented the read
     *          head already. The read head is now at 2, with index 1 consumed and index 0 not consumed. Decrementing the read
     *          head would set it back to index 1, thus resulting in index 0 not being read on the next dequeue, and index 1
     *          being read twice.
     *
     *          In order to resolve that problem, the ReadReservationTicket is used to record locally (so as to avoid the need
     *          for something like a secondary concurrent queue to store failed read indices in) that index 0 was claimed but
     *          not yet read. In order to actually READ index 0, that ticket must be passed back into Dequeue() again.
     *
     *          It is vitally important, however, to stress that ReadReservationTicket *is not thread-safe* and *must only
     *          be accessed by one thread at a time.* This DOES limit the use cases for ticketed dequeues to those where either
     *          only one consumer is active, or each consumer is assigned its own ticket, possibly in stack memory or thread-local
     *          storage.
     *
     *          It's also worth emphasizing that the ticket is a permanent reservation for a specific index in the queue and cannot
     *          be returned to the queue, so doing something like emptying out the ticket by looping until Dequeue() returns false
     *          will result in one item in the queue being permanently associated with the ticket used, so if other Dequeue() forms
     *          are used to read from the queue later, or if a different ticket is used later, one item will have been rendered
     *          unavailable.
     *
     *          If these limitations do not suit your use case (and, in many circumstances, they won't), then consider using
     *          the ticket-free Dequeue() or BatchDequeue(). In fact, BatchDequeue() is often preferable to ticketed dequeues,
     *          as well - if you're reading more than one or two elements at a time, you'll likely find BatchDequeue() to perform
     *          faster than Dequeue() and have fewer limitations. (Please see the benchmarks for a better understanding of where
     *          BatchDequeue with small batch sizes exceeds or falls behind ticketed dequeues.)
     *
     *          An additional word of warning: Ticket-Free dequeues do, in fact, use a secondary queue under the hood to
     *          store tickets that are shared between threads. This secondary queue is fast in most use cases, because
     *          it only stores tickets when a dequeue fails and dequeue-from-empty in the secondary queue is the optimal
     *          path. However, because dequeues when it's not empty are much slower, the overall amortized performance of
     *          ticket-free dequeues will be somewhat worse than ticketed dequeues.
     *
     *          Additionally, and vitally: The Ticket-Free Dequeue API is ticket-free in name only and does use tickets
     *          under the hood. However, BatchDequeue() is actually ENTIRELY ticket-free and DOES NOT use tickets. Which means
     *          that the Ticket-Free and BatchDequeue APIs *do not mix very well* unless you are *very careful* about your
     *          usage - any time the ticket-free Dequeue() returns false, an element in the queue has been made inaccessible
     *          for batch dequeueing and may then only be retrieved via another ticket-free dequeue. The same is true for
     *          mixing ticket-free and ticketed dequeues - any time either returns false, an element has been made inaccessible
     *          to the other.
     *
     *          If Dequeue() returns true, it is still highly recommended to keep the ticket alive and pass it back in.
     *          The only reason for this is performance - the performance drop from having to adjust reference counts
     *          on each dequeue operation isn't crippling, but it is noticeable.
     *
     *
     * @param   val      A reference to a value, which will be filled with the contents of the dequeued element, if any.
     *                   The move assignment operator will be called on the value, if one exists.
     * @param   ticket   A reservation ticket which will hold cached data to improve performance.
     *
     * @return  true if the dequeue succeeded and tha value holds a valid item, false if the dequeue failed.
     */
    inline bool Dequeue(t_ElementType& val, ReadReservationTicket& ticket) {
        // For reads, we'll start out by checking our reservation ticket. If it's got cached data, we can skip a lot of work we already did.
        typename Buffer::BufferElement* element = ticket.ptr;
        Buffer*                         buffer  = ticket.buffer;

        // There are a few cases we can run into in the dequeue operation.
        // The easiest case is after a failed dequeue, in which case we already have our element and can check it again.
        if (NCPS_LIKELY(!element)) {
            // The second case is when the ticket passed in has been held over from a previous successful dequeue.
            // In this case we don't have to worry about acquiring the read buffer, because it's cached. We only have
            // to do that if the current one is exhausted.

            // Step one, get the next element and determine if the current buffer is exhausted!
            element = buffer->GetForRead();
            while (NCPS_UNLIKELY(element >= buffer->GetEnd())) {
                Buffer* readBuffer = m_readBuffer.load(std::memory_order_acquire);
                if (readBuffer->GetNext() == nullptr) {
                    return false;
                }
                // If the buffer is exhausted, we have to acquire the next one.
                // This is done under the same spin-lock as allocating a new buffer for writes, and the logic is almost identical.
                // The only difference is that, if buffer->GetNext() returns nullptr, instead of allocating a new one,
                // we just return false; for more details on this logic, see the comments in getNextElement_()
                if (!m_reallocatingBuffer.exchange(true, std::memory_order_seq_cst)) {
                    if (!fetchNextReadBuffer_(element, buffer, ticket)) {
                        m_reallocatingBuffer.store(false, std::memory_order_release);
                        return false;
                    }
                    m_reallocatingBuffer.store(false, std::memory_order_release);
                }
            }
        }

        if constexpr (t_EnableBatch) {
            m_outstanding.fetch_add(-1, std::memory_order_relaxed);
        }

        // Now that we have an element to read, we have to check if there's any actual data in it.
        // If not, we're going to remember this element in the reservation ticket and come back to it later.
        // This definitively prevents any race conditions involved in attempting to correct for overcommit.
        bool ready = element->ready.load(std::memory_order_acquire);
        if (NCPS_LIKELY(ready == true)) {
            // If the element did have valid data, we need to make sure our ticket's not holding any cache information.
            // Otherwise we'd just keep ending up reading the same cached element over and over.
            ticket.ptr = nullptr;

            // Increase the ticket's read count, which is used in the block above to perform bulk DecRefs
            ++ticket.count;

            // Finally, we'll go ahead and pull the data from the element, destroy it, and decrement and possibly free the buffer.
            // Then we can return true - success!
            val = std::move(element->item);
            element->item.~t_ElementType();
            NCPS_CONCURRENT_QUEUE_ASSERT(element->ready.exchange(false) == true);

            return true;
        }
        ticket.ptr = element;
        return false;
    }

    /**
     * @brief   Attempt to dequeue an item without passing in any tickets.
     *
     * @details This version of Dequeue() does not require user-provided tickets to complete the dequeue operation,
     *          making it more suitable for certain use cases that can't meet the riged requirements of the ticketed
     *          API. Do note, however, that while dequeue-from-empty is quite fast with the ticketed API, the ticket-free
     *          API suffers greatly with the ticket-free API. Dequeue-from-empty, in general, gets roughly 1/3 the throughput
     *          of non-empty dequeues.
     *
     *          HOWEVER, there is a word of warning: Ticket-Free dequeues do, in fact, use a secondary queue under the hood to
     *          store tickets that are shared between threads. This secondary queue is fast in most use cases, because
     *          it only stores tickets when a dequeue fails and dequeue-from-empty in the secondary queue is the optimal
     *          path. However, because dequeues when it's not empty are much slower, the overall amortized performance of
     *          ticket-free dequeues will be somewhat worse than ticketed dequeues.
     *
     *          Additionally, and vitally: The Ticket-Free Dequeue API is ticket-free in name only and does use tickets
     *          under the hood. However, BatchDequeue() is actually ENTIRELY ticket-free and DOES NOT use tickets. Which means
     *          that the Ticket-Free and BatchDequeue APIs *do not mix very well* unless you are *very careful* about your
     *          usage - any time the ticket-free Dequeue() returns false, an element in the queue has been made inaccessible
     *          for batch dequeueing and may then only be retrieved via another ticket-free dequeue. The same is true for
     *          mixing ticket-free and ticketed dequeues - any time either returns false, an element has been made inaccessible
     *          to the other.
     *
     *          See the documentation for Dequeue(t_ElementType& val, ReadReservationTicket& ticket) for more information.
     *
     * @param   val      A reference to a value, which will be filled with the contents of the dequeued element, if any.
     *                   The move assignment operator will be called on the value, if one exists.
     *
     * @return  true if the dequeue succeeded and tha value holds a valid item, false if the dequeue failed.
     */
    inline bool Dequeue(t_ElementType& val) {
        ReadReservationTicket ticket;
        bool                  reattempt = m_subQueue.Dequeue(ticket);
        if (!reattempt) {
            if (m_failedReads.load(std::memory_order_acquire) != 0) {
                return false;
            }
            InitializeReservationTicket(ticket);
        }
        if (Dequeue(val, ticket)) {
            if (reattempt) {
                m_failedReads.fetch_sub(1, std::memory_order_acq_rel);
            }
            return true;
        }
        if (!reattempt) {
            m_failedReads.fetch_add(1, std::memory_order_acq_rel);
        }
        ssize_t pos = m_subQueue.Enqueue(ticket);
        for (;;) {
            if (m_subQueue.Dequeue(ticket, pos) == false) {
                return false;
            }
            if (Dequeue(val, ticket)) {
                m_failedReads.fetch_sub(1, std::memory_order_acq_rel);
                return true;
            }
            m_subQueue.Enqueue(ticket);
        }
    }

    /**
     * @brief Stores state and provides logic for iterating through the results of a BatchDequeue.
     *
     * @details The BatchDequeueList is an iterator-like class that allows for the consumption of elements
     *          returned via BatchDequeue(). Because the queue uses multiple buffers under the hood, there is
     *          a possibility that the results of the BatchDequeue() will span two more more buffers. In
     *          that situation, BatchDequeueList will contain the contiguous elements retrieved from only
     *          one buffer at a time. When the end of the buffer is reached, it will lazy-fetch elements from
     *          the next buffer until the entire batch has been consumed.
     *
     *          WARNING: Iterating the BatchDequeueList is important to trigger reference counting logic on
     *          the queue buffers to enable them to be recycled. If you dequeue but don't iterate the list,
     *          you may cause the queue to experience a memory leak. When BatchDequeueList is destroyed, it
     *          will automatically perform this iteration for you to update the reference counts. The iteration
     *          will also be performed automatically if you pass a non-consumed iterator back into BatchDequeue
     *          to retrieve more items. However, if you do neither of those things and an iterator is left sitting
     *          somewhere unconsumed, it will prevent the reference counting from occurring and memory will not
     *          be restored to the reusable buffer list, resulting in a leak.
     */
    class BatchDequeueList {
       public:
        /**
         * @brief Fetch the next element in the batch
         *
         * @details Normally, this function amounts to a pointer increment and a copy constructor and destructor
         *          for t_ElementType. However, in scenarios where a batch spans the boundaries of two buffers,
         *          this will iterate until it reaches the end of the current buffer, then lazy fetch elements
         *          from successive buffers until the batch is exhausted.
         */
        inline t_ElementType Next() {
            while (NCPS_UNLIKELY(m_element >= m_end)) {
                // If the buffer is exhausted, we have to acquire the next one.
                // This is done under the same spin-lock as allocating a new buffer for writes, and the logic is almost identical.
                // The only difference is that, if buffer->GetNext() returns nullptr, instead of allocating a new one,
                // we just return false; for more details on this logic, see the comments in getNextElement_()
                Buffer* buffer = m_buffer;
                for (;;) {
                    Buffer* readBuffer = m_queue->m_readBuffer.load(std::memory_order_acquire);
                    if (readBuffer->GetNext() == nullptr) {
                        continue;
                    }
                    if (!m_queue->m_reallocatingBuffer.exchange(true, std::memory_order_seq_cst)) {
                        if (!m_queue->fetchNextReadBuffer_(m_element, m_buffer, m_remaining)) {
                            m_queue->m_reallocatingBuffer.store(false, std::memory_order_release);
                            continue;
                        }
                        if (m_consumed != 0) {
                            m_queue->consumeUnlocked_(buffer, m_consumed);
                            m_consumed = 0;
                        }
                        m_end = m_buffer->GetEnd();
                        m_queue->m_reallocatingBuffer.store(false, std::memory_order_release);
                        break;
                    }
                }
            }
            while (!m_element->ready.load(std::memory_order_acquire)) {
            }
            ++m_consumed;
            t_ElementType val(std::move(m_element->item));
            m_element->item.~t_ElementType();
            --m_remaining;
            ++m_element;
            return val;
        }

        /**
         * @brief Check if there are more items to iterate.
         *
         * @return true if there are elements left in the batch, false if the batch is exhausted
         */
        inline bool More() { return (m_remaining > 0); }

        ~BatchDequeueList() {
            while (NCPS_UNLIKELY(More())) {
                Next();
            }
            if (NCPS_LIKELY(m_consumed != 0)) {
                m_queue->consume_(m_buffer, m_consumed);
            }
        }

        BatchDequeueList(){};

        BatchDequeueList(ConcurrentQueue* queue, typename Buffer::BufferElement* element, typename Buffer::BufferElement const* end, Buffer* buffer, ssize_t count) : m_queue(queue), m_element(element), m_end(end), m_buffer(buffer), m_remaining(count), m_count(count) {}

       protected:
        BatchDequeueList(BatchDequeueList const& other) = delete;
        BatchDequeueList(BatchDequeueList& other)       = delete;
        BatchDequeueList& operator=(BatchDequeueList const& other) = delete;
        BatchDequeueList& operator=(BatchDequeueList& other) = delete;

        friend class ConcurrentQueue;
        ConcurrentQueue*                      m_queue;
        typename Buffer::BufferElement*       m_element;
        typename Buffer::BufferElement const* m_end;
        Buffer*                               m_buffer{nullptr};
        ssize_t                               m_remaining{0};
        ssize_t                               m_count{0};
        ssize_t                               m_consumed{0};
    };

    /**
     * @brief Retrieve multiple items from the queue. When maxCount is more than 1 or 2, DequeueBatch can offer orders of
     *        magnitude greater performance than either Dequeue option.
     *
     * @details In contrast with the other two Dequeue() options, DequeueBatch() takes advantage of the contiguous storage
     *          structure of NCPSQueue to reduce contention by allowing the retrieval of multiple items from the queue with
     *          only a single atomic increment. A second atomic operation is used to keep track of how many elements it's allowed
     *          to read to ensure it doesn't over-consume the queue. When it does, a third atomic operation is used to correct.
     *
     *          However, while the additional atomic operations on the queue result in slower performance for individual item
     *          dequeues, this is vastly made up for when reading larger numbers of items by reducing the contention on each
     *          individual read - while 100 normal dequeue operations would involve a total of 100 atomic increments on contentuous
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
     *          First, simply the act of enabling batch enqueue and dequeue makes the non-batched operations a little bit slower,
     *          as it adds a requirement for them to update the outstanding count in order for batched operations to function properly
     *          when the two are mixed.
     *
     *          Second, batched operations with a maxCount of 1 are slower than ticketed operations. In general, batch size of 1 will see
     *          close to the same performance as the ticket-free API for successful dequeues when batch mode is enabled, and will be slightly
     *          slower than ticket-free dequeues with batch mode disabled. However...
     *
     *          Third (to be taken with a LARGE grain of salt), while successful dequeues in batch mode are extremely fast,
     *          dequeue-from-empty can be much slower than other options depending on your use case. If you're doing other processing
     *          when the queue is empty, or sleeping when the queue is empty, and thus keeping contention low, you'll likely see
     *          dequeue-from-empty performing as well as a successful dequeue. But if your threads are all looping on trying to read
     *          from the empty queue, the number of attempts they can do per second will be dramatically lower due to the increased
     *          contention this causes. (However, if you're in that situation, you're not really DOING anything, so practically
     *          speaking... does it really matter that you're doing less of nothing?)
     *
     *          Finally, mixing the normal API and the batch API can lead to unexpected behavior. The non-batch API removes items from
     *          the pool that the batch API can read from *even when their reads fail*, so if you perform a non-batch read that returns false,
     *          then enqueue an item, then attempt to dequeue that item using the batch API, you will find the batch API returns 0 items
     *          instead of the expected 1, because that item was already reserved by the non-batch API before it was written.
     *          See the documentation for Dequeue(t_ElementType& val, ReadReservationTicket& ticket) for more information.
     *
     * @param   result    Out variable in which to store the retrieved batch data. May safely be reused once all items have been consumed.
     *
     * @param   maxCount  Maximum number of elements to retrieve. If the full requested amount doesn't exist in the queue, a partial result
     *                    will be returned.
     */
    void DequeueBatch(BatchDequeueList& result, ssize_t maxCount) {
        if constexpr (!t_EnableBatch) {
            throw std::logic_error("Batch operations are not enabled on this queue.");
        } else {
            while (NCPS_UNLIKELY(result.More())) {
                result.Next();
            }
            ssize_t newOutstanding = m_outstanding.fetch_sub(maxCount, std::memory_order_acq_rel) - maxCount;
            ssize_t batchSize      = maxCount;
            if (NCPS_UNLIKELY(newOutstanding < 0)) {
                batchSize += newOutstanding;
                newOutstanding = m_outstanding.fetch_sub(newOutstanding, std::memory_order_release) - newOutstanding;
                if (NCPS_LIKELY(batchSize <= 0)) {
                    return;
                }
            }
            Buffer*                         buffer  = m_readBuffer.load(std::memory_order_acquire);
            typename Buffer::BufferElement* element = buffer->GetBatchForRead(batchSize);
            if ((result.m_buffer != buffer) & (result.m_consumed != 0)) {
                consume_(result.m_buffer, result.m_consumed);
                result.m_consumed = 0;
            }
            result.m_queue     = this;
            result.m_element   = element;
            result.m_end       = buffer->GetEnd();
            result.m_buffer    = buffer;
            result.m_remaining = batchSize;
            result.m_count     = batchSize;
        }
    }

   protected:
    // Cacheline padding prevents false sharing.
    NCPS_PAD_CACHELINE;
    // Read head, not necessarily the same as the write head
    std::atomic<Buffer*> m_readBuffer;
    NCPS_PAD_CACHELINE;
    // Spin lock used when swapping buffers - not technically lock free, but lock free isn't always faster.
    // And this is used rarely enough that the simplicity of the code around it is far more valuable.
    // The performance improvement of making this lock free would be imperceptible, and the increased amount
    // of code to get it to work right would likely bloat code size and cause more cache misses in execution.
    std::atomic<bool> m_reallocatingBuffer;
    NCPS_PAD_CACHELINE;
    // Write head, not necessarily the same as the read head
    std::atomic<Buffer*> m_writeBuffer;
    NCPS_PAD_CACHELINE;
    // Tail. Obviously.
    std::atomic<Buffer*> m_tail;
    NCPS_PAD_CACHELINE;
    detail::ReservationTicketSubQueue<ReadReservationTicket, t_AllocatorType> m_subQueue;
    NCPS_PAD_CACHELINE;
    std::atomic<ssize_t> m_failedReads;
    NCPS_PAD_CACHELINE;
    std::atomic<ssize_t> m_outstanding;
    NCPS_PAD_CACHELINE;

    typename t_AllocatorType::template rebind<Buffer>::other m_allocator;
};

template <typename t_ElementType, size_t t_BlockSize, bool t_EnableBatch, typename t_AllocatorType>
NCPS::ReadReservationTicket<t_ElementType, t_BlockSize, t_EnableBatch, t_AllocatorType>::~ReadReservationTicket() {
    if (buffer && count != 0) {
        queue->consume_(buffer, count);
    }
}

/**
 * @class NCPS::BoundedReadReservationTicket
 *
 * @brief Represents a reservation to read an element that hasn't been written to yet.
 */
template <typename t_ElementType>
struct NCPS::BoundedReadReservationTicket {
    void* ptr{nullptr};

    BoundedReadReservationTicket() {}

    BoundedReadReservationTicket(BoundedReadReservationTicket const& other) = delete;
    BoundedReadReservationTicket& operator=(BoundedReadReservationTicket const& other) = delete;

    BoundedReadReservationTicket(BoundedReadReservationTicket&& other) noexcept : ptr(other.ptr) { other.ptr = nullptr; }
    BoundedReadReservationTicket& operator=(BoundedReadReservationTicket&& other) noexcept {
        ptr       = other.ptr;
        other.ptr = nullptr;
        return *this;
    }
};

/**
 * @class NCPS::BoundedReadReservationTicket
 *
 * @brief Represents a reservation to write an element that's already holding unread data
 */
template <typename t_ElementType>
struct NCPS::BoundedWriteReservationTicket {
    void* ptr{nullptr};

    BoundedWriteReservationTicket() {}

    BoundedWriteReservationTicket(BoundedWriteReservationTicket const& other) = delete;
    BoundedWriteReservationTicket& operator=(BoundedWriteReservationTicket const& other) = delete;

    BoundedWriteReservationTicket(BoundedWriteReservationTicket&& other) noexcept : ptr(other.ptr) { other.ptr = nullptr; }
    BoundedWriteReservationTicket& operator=(BoundedWriteReservationTicket&& other) noexcept {
        ptr       = other.ptr;
        other.ptr = nullptr;
        return *this;
    }
};

/**
 * @class   NCPS::ConcurrentBoundedQueue
 *
 * @brief   A bounded implementation of ConcurrentQueue.
 *
 * @details The core algorithm of this queue is essentially the same algorithm as the
 *          unbounded version of this queue - however, there are a few key differences:
 *
 *          First, and probably most importantly, this queue cannot grow. It works as
 *          a circular buffer, and can only hold the specified number of elements at
 *          one time. Elements that are read by Dequeue() become available to be
 *          written again, but if no consumer threads are running, or producer threads
 *          significantly outpace consumer threads, the queue can become full,
 *          causing Enqueue() to return false.
 *
 *          Secondly, unlike the unbounded version, this queue is truly lock-free
 *          and wait-free. There are no situations that involve taking a lock.
 *
 *          Thirdly, reservation tickets are required for both enqueue AND dequeue;
 *          however, they only need to be kept alive after a return of false from either
 *          method. If the return value is true, the ticket can be safely thrown away.
 *
 *          Note that there is one situation that can cause an enqueue thread to become
 *          blocked: if a dequeue thread gets a return of false and doesn't call Dequeue()
 *          again with that ticket, an enqueue thread will be blocked waiting for that
 *          spot to be read, even after other enqueue threads successfully move on and continue
 *          writing.
 *
 *          Also note that t_QueueSize will be adjusted up to the nearest power of 2 for performance
 *          reasons.
 *
 *          Finally, note that ConcurrentBoundedQueue does NOT support a batched API.
 *          The reason for this is that the fact that enqueues can fail increases the bookkeeping
 *          requirements for the batch API beyond the point that can be reasonably, correctly,
 *          and performantly handled in a lock-free concurrent context.
 *
 * @tparam  t_ElementType       the type of element to store in the queue
 *
 * @tparam  t_QueueSize         the maximum number of elements that can be in the queue at a time.
 *                              Once this number has been reached, enqueue() operations will fail until
 *                              elements have been dequeued. This is not a maximum number of elements
 *                              ever inserted, only a maximum number that can be held unread at a time -
 *                              representing overhead between enqueue and dequeue operations.
 *
 * @tparam  t_AllocatorType     Allocator used to allocate tickets for the ticket-free enqueue
 *                              and dequeue operations. The allocators are NOT used in the operations
 *                              that do accept ticket parameters; those are alloc-free.
 */
template <typename t_ElementType, size_t t_QueueSize, typename t_AllocatorType>
class NCPS::ConcurrentBoundedQueue {
   public:
    using ReadReservationTicket  = NCPS::BoundedReadReservationTicket<t_ElementType>;
    using WriteReservationTicket = BoundedWriteReservationTicket<t_ElementType>;

    struct BufferElement {
        std::atomic<bool> ready;
        t_ElementType     item;
    };

    ConcurrentBoundedQueue(ssize_t maxConcurrentTicketFreeReads = 0, ssize_t maxConcurrentTicketFreeWrites = 0) : m_readIdx(0), m_writeIdx(0), m_readSubQueue(maxConcurrentTicketFreeReads), m_failedReads(0), m_writeSubQueue(maxConcurrentTicketFreeWrites), m_failedWrites(0) { memset(m_buffer, 0, c_adjustedSize * sizeof(BufferElement)); }

    ~ConcurrentBoundedQueue() {
        BufferElement* buffer = reinterpret_cast<BufferElement*>(m_buffer);
        for (size_t idx = 0; idx < c_adjustedSize; ++idx) {
            BufferElement* element = buffer + (idx & (c_adjustedSize - 1));
            if (element->ready.load()) {
                element->item.~t_ElementType();
            }
        }
    }

    /**
     * @brief   Enqueue an item by reference, calling the copy constructor. Will fail if the queue is full.
     *
     * @param   val      The value to equeue
     * @param   ticket   A reservation ticket that will hold cached data in the event of a return of false
     *
     * @return  true if the element was successfully enqueued, false otherwise
     */
    inline bool Enqueue(t_ElementType const& val, WriteReservationTicket& ticket) {
        // This case is much simpler than the unbounded case!
        // First we check to see if the reservation ticket contains an element we're supposed to retry a write to
        BufferElement* element = reinterpret_cast<BufferElement*>(ticket.ptr);

        if (NCPS_LIKELY(!element)) {
            // If not, then we get a new one with a simple fetch_add on the write index, wrapping it appropriately.
            size_t idx = m_writeIdx.fetch_add(1, std::memory_order_acq_rel);
            element    = m_buffer + (idx & (c_adjustedSize - 1));
        }

        // Check the ready flag. If it's already set, we can't overwrite it and have to return false,
        // storing this element on the reservation ticket to make sure we try it again later.
        bool ready = element->ready.load(std::memory_order_acquire);
        if (NCPS_LIKELY(ready == false)) {
            // If it's not already ready, we make sure the reservation ticket is clear so we don't write it again...
            ticket.ptr = nullptr;

            // ...then we construct the new element...
            new (&element->item) t_ElementType(val);
            NCPS_CONCURRENT_QUEUE_ASSERT(element->ready.load() == false);

            // ...then we signal that the element is ready to read and return true.
            element->ready.store(true, std::memory_order_release);
            return true;
        }
        ticket.ptr = element;
        return false;
    }

    /**
     * @brief   Enqueue an item by rvalue reference, calling the move constructor. Will fail if the queue is full.
     *
     * @param   val      The value to equeue
     * @param   ticket   A reservation ticket that will hold cached data in the event of a return of false
     *
     * @return  true if the element was successfully enqueued, false otherwise
     */
    inline bool Enqueue(t_ElementType&& val, WriteReservationTicket& ticket) {
        // See above for comments; this algorithm is identical except for construction via move.
        BufferElement* element = reinterpret_cast<BufferElement*>(ticket.ptr);

        if (NCPS_LIKELY(!element)) {
            size_t idx = m_writeIdx.fetch_add(1, std::memory_order_acq_rel);
            element    = m_buffer + (idx & (c_adjustedSize - 1));
        }

        bool ready = element->ready.load(std::memory_order_acquire);
        if (NCPS_LIKELY(ready == false)) {
            ticket.ptr = nullptr;

            new (&element->item) t_ElementType(std::move(val));
            NCPS_CONCURRENT_QUEUE_ASSERT(element->ready.load() == false);

            element->ready.store(true, std::memory_order_release);
            return true;
        }
        ticket.ptr = element;
        return false;
    }

    /**
     * @brief   Dequeue an item.  Will fail if the queue is empty.
     *
     * @param   val      A reference to a value, which will be filled with the contents of the dequeued element, if any.
     *                   The move assignment operator will be called on the value, if one exists.
     * @param   ticket   A reservation ticket which will hold cached data to improve performance.
     *
     * @return  true if the element was successfully enqueued, false otherwise
     */
    inline bool Dequeue(t_ElementType& val, ReadReservationTicket& ticket) {
        // See above for comments; this algorithm is identical except we're operating on m_readIdx
        // instead of m_writeIdx, and destructing the element instead of constructing it.
        BufferElement* element = reinterpret_cast<BufferElement*>(ticket.ptr);

        if (NCPS_LIKELY(!element)) {
            size_t idx = m_readIdx.fetch_add(1, std::memory_order_acq_rel);
            element    = m_buffer + (idx & (c_adjustedSize - 1));
        }

        bool ready = element->ready.load(std::memory_order_acquire);
        if (NCPS_LIKELY(ready == true)) {
            ticket.ptr = nullptr;

            val = std::move(element->item);
            element->item.~t_ElementType();
            NCPS_CONCURRENT_QUEUE_ASSERT(element->ready.load() == true);
            element->ready.store(false, std::memory_order_release);
            return true;
        }
        ticket.ptr = element;
        return false;
    }

    /**
     * @brief   Attempt to enqueue an item without passing in any tickets.
     *
     * @details This version of Enqueue() does not require persistent tickets even on a return value of false
     *          (or any tickets, for that matter). The performance of the common case will be similar to the other
     *          version of Enqueue(). In the case of failed writes, performance will be somewhat hampered,
     *          but still superior to the performance of a successful write.
     *
     *
     * @param   val      The value to equeue
     *
     * @return  true if the enqueue succeeded, false if the enqueue failed.
     */
    inline bool Enqueue(t_ElementType& val) {
        WriteReservationTicket ticket;
        bool                   reattempt = m_writeSubQueue.Dequeue(ticket);
        if (!reattempt && m_failedWrites.load(std::memory_order_acquire) != 0) {
            return false;
        }
        if (Enqueue(val, ticket)) {
            if (reattempt) {
                m_failedWrites.fetch_sub(1, std::memory_order_acq_rel);
            }
            return true;
        }
        if (!reattempt) {
            m_failedWrites.fetch_add(1, std::memory_order_acq_rel);
        }
        ssize_t enqueuePos = m_writeSubQueue.Enqueue(ticket);
        for (;;) {
            if (m_writeSubQueue.Dequeue(ticket, enqueuePos) == false) {
                return false;
            }
            if (Enqueue(val, ticket)) {
                m_failedWrites.fetch_sub(1, std::memory_order_acq_rel);
                return true;
            }
            m_writeSubQueue.Enqueue(ticket);
        }
    }

    /**
     * @brief   Attempt to dequeue an item without passing in any tickets.
     *
     * @details This version of Dequeue() does not require persistent tickets even on a return value of false
     *          (or any tickets, for that matter). The performance of the common case will be similar to the other
     *          version of Dequeue(). In the case of failed reads, performance will be somewhat hampered,
     *          but still superior to the performance of a successful read.
     *
     *
     * @param   val      A reference to a value, which will be filled with the contents of the dequeued element, if any.
     *                   The move assignment operator will be called on the value, if one exists.
     *
     * @return  true if the dequeue succeeded and tha value holds a valid item, false if the dequeue failed.
     */
    inline bool Dequeue(t_ElementType& val) {
        ReadReservationTicket ticket;
        bool                  reattempt = m_readSubQueue.Dequeue(ticket);
        if (!reattempt && m_failedReads.load(std::memory_order_acquire) != 0) {
            return false;
        }
        if (Dequeue(val, ticket)) {
            if (reattempt) {
                m_failedReads.fetch_sub(1, std::memory_order_acq_rel);
            }
            return true;
        }
        if (!reattempt) {
            m_failedReads.fetch_add(1, std::memory_order_acq_rel);
        }
        ssize_t pos = m_readSubQueue.Enqueue(ticket);
        for (;;) {
            if (m_readSubQueue.Dequeue(ticket, pos) == false) {
                return false;
            }
            if (Dequeue(val, ticket)) {
                m_failedReads.fetch_sub(1, std::memory_order_acq_rel);
                return true;
            }
            m_readSubQueue.Enqueue(ticket);
        }
    }

   private:
    constexpr static size_t c_adjustedSize = detail::nextPowerOf2(t_QueueSize);

    NCPS_PAD_CACHELINE;
    std::atomic<size_t> m_readIdx;
    NCPS_PAD_CACHELINE;
    std::atomic<size_t> m_writeIdx;
    NCPS_PAD_CACHELINE;
    BufferElement m_buffer[c_adjustedSize];
    NCPS_PAD_CACHELINE;
    detail::ReservationTicketSubQueue<ReadReservationTicket, t_AllocatorType> m_readSubQueue;
    NCPS_PAD_CACHELINE;
    std::atomic<ssize_t> m_failedReads;
    NCPS_PAD_CACHELINE;
    detail::ReservationTicketSubQueue<WriteReservationTicket, t_AllocatorType> m_writeSubQueue;
    NCPS_PAD_CACHELINE;
    std::atomic<ssize_t> m_failedWrites;
    NCPS_PAD_CACHELINE;
};
