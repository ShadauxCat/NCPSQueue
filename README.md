# NCPSQueue

Reference implementation for the N-Core Positive Scaling Concurrent Queue, which provides fast performance and scalability with increased producer and consumer counts.

`NCPS::ConcurrentQueue` is a generic queue that comes in both bounded and non-bounded formats, and uses the concept of a ReservationTicket to provide wait-free performance in 99% of cases with the unbounded queue (a spin-lock must be taken when the queue needs to resize, which happens once per N enqueues, where N is a configurable bucket size - by default, 8192) and in 100% of cases with the bounded queue. 


## Scaling

As indicated by the name (N-Core Positive Scaling Concurrent Queue), `NCPS::ConcurrentQueue` has a unique property among popular concurrent queue implementations in that it is capable of scaling positively as more cores are added. Other tested implementations achieve flat performance with more cores - the overall system throughput doesn't change as more cores are added, but instead, the throughput just gets spread out as each thread individually performs slower due to the extra activity in the system. `NCPS::ConcurrentQueue`, like most queues, operates at its fastest total system throughput in the single-producer, single-consumer case; however, unlike other tested implementations, the overall throughput of the system increases as more cores are added. (Though it takes a large number of cores in the multi-producer and/or multi-consumer cases to reach the throughput of the single-producer/single-consumer case.)

![Positive Scaling](https://raw.githubusercontent.com/ShadauxCat/NCPSQueue/master/benchmarks/int64_t/heatmaps/NCPS.png)
![Comparison](https://raw.githubusercontent.com/ShadauxCat/NCPSQueue/master/benchmarks/int64_t/comparisons/symmetrical.png)

## Bounded vs Unbounded

In practice, the unbounded queue actually tends to be faster than the bounded queue because enqueuing to the unbounded queue can never fail, meaning there are fewer edge cases it has to consider. However, the bounded queue's performance will be more consistent as it will never have to allocate a new buffer.

## Memory usage

One benefit of the bounded queue over the unbounded one is predictable memory performance. The bounded queue will use memory equal to `N * (sizeof(T) + sizeof(bool))` and will retain that memory usage for its entire lifetime. Conversely, the unbounded queue will *start* at `N * (sizeof(T) + sizeof(bool))`, just like the bounded queue, but will experience at least one growth in its lifetime even if you don't exceed N elements in the queue at a time. The result is that its memory usage in the best case ends up being `2 * N * (sizeof(T) + sizeof(bool))`. In the worst case, if you consistently enqueue faster than you dequeue, the unbounded queue will grow infinitely - however, this is unlikely to happen in practice with well-written code.

Another thing to be aware of with the unbounded queue is that its memory usage will always remain at its high watermark. While the queue is in use, there is no safe way to deallocate buffers without incurring the cost of reference counting (which is significant), so the memory isn't released until the queue itself is destroyed.

## Reservation Tickets

As mentioned above, `NCPS::ConcurrentQueue` achieves its performance gains by means of the ReservationTicket system. A ReservationTicket is a thread-specific (but not thread-local) value that contains some information about the state of the queue in a way that won't incur sharing and synchronization costs. *Note that NCPS::ConcurrentQueue also provides a ticket-free API, which will be discussed in the next section.*

When reading from the unbounded queue, and when both reading from and writing to the bounded queue, there is a chance the operation will fail - a read will fail if nothing has been enqueued, and a write will fail if the bounded queue is full and has no space. In this case, the ReservationTicket "reserves" a spot in the queue for that specific thread - the next time that reservation ticket is passed in, the owner will read from or write to the same spot they failed on before. This alleviates the need for the queue to do internal bookkeeping about failed operations, which is expensive, and also enables it to maintain wait-free performance by avoiding costly operations like Compare-And-Swap.

The downside is that it places more burden on the user. The properties of reservation tickets are as follows:

- A successful operation (one that returns true) leaves the reservation ticket empty. It is safe to destroy the reservation ticket in this case. For the unbounded queue, it's more efficient to keep the ticket alive where it's feasible, but not required - this is known as Ephemeral Tickets; the ticket only remains alive while it is necessary and then goes away.
- A failed operation (one that returns false) stores its reservation information on the ticket and continues on as if a successful read or write were made. *This means that that spot in the queue is reserved for the holder of that ticket, and if the ticket is destroyed, that spot in the queue will never be used.* 
  - For a read, that means an element in the queue will never be read and will effectively disappear into the aether. 
  - For a write, it means that the element in the queue will not get written to, so the next attempt to read it will return false every time because no one is ever allowed to write it again.
  - As a result, a ticket returned from a failed read or write MUST stay alive and be passed as-is to the next call to `Enqueue()` or `Dequeue()`
- For the unbounded queue only, *tickets must be initialized via queue.InitializeReservationTicket(ticket) before they are used.*
- Tickets *are not thread safe and cannot be shared between threads*. Each thread must have its own ticket, ideally stored in stack memory. A ticket is not pinned to a specific thread and may be transferred to another thread, but *may not be accessed by multiple threads simultaneously or shared by multiple threads calling `Enqueue()` or `Dequeue()`*

Another downside of this system is that a thread that's been assigned a ticket for a specific spot in a bucket becomes the only thread that can read from that spot in the bucket. As a result, care must be taken - a system where threads go to sleep on a failed read and are awakened by a semaphore when data is ready, for example, may end up waking a different thread than the one that failed the read. Since the reservation ticket is owned by another thread, this new thread will also fail the read because it will read from a different position in the queue, even though there is data ready to be read.

## Ticket-Free API

The reservation ticket API is definitely the most performant option for using `NCPS::ConcurrentQueue`, but it's not always feasible to maintain tickets. For this case, there's a slightly slower ticket-free API. This API uses a less efficient sub-queue to store tickets after failed operations. Successful operations use ephemeral tickets, and only incur the extra cost of a dequeue-from-empty on the sub-queue, which is a very efficient operation even in the less efficient queue. Failed operations, as well as the first subsequent operation after the failed one, will incur the increased cost of interfacing with the sub-queue. Even with this cost, however, `NCPS::ConcurrentQueue` still maintains high performance characteristics, as well as its ability to scale positively across multiple cores.

## Benchmarks

A number of benchmark graphs have been included in the 'benchmarks' section of the repository, comparing NCPS::ConcurrentQueue against other commonly-used concurrent queue implementations. The benchmarks are broken down as follows:

- Each queue was tested on a 24-core, 64-bit Google Compute instance on every combination of producer and consumer counts from 1/1 to 24/24. They were tested on element types of char, int64_t (sometimes indicated as 'long'), and a FixedStaticString type containing 64 bytes of data. 1,000,000 elements were enqueued and dequeued and the total throughput of the queues was measured.
- The queues tested were:
  - Intel Thread Building Blocks (TBB): tbb::concurrent_queue and tbb::concurrent_bounded_queue
  - Boost: boost::lockfree::queue (boost is not present for FixedStaticString because it fails to compile!)
  - 1024cores mpmc_bounded_queue (from http://www.1024cores.net/home/lock-free-algorithms/queues/bounded-mpmc-queue )
  - std::deque guarded by std::mutex (as a control)
- The results of each of those tests is stored as both a dot chart (where larger dots represent higher throughput) and a heatmap chart (where colors range from dark blue for low throughput up to red for high throughput).
- These graphs have been divided up based on the type of data consumed
- Additionally, a number of "cross-section" line graphs were made, showing direct comparisons. The cross sections cover:
  - Symmetrical (C = P)
  - Consumer Heavy (C = 2P)
  - Very consumer heavy (C = 3P)
  - Producer heavy (P = 2C)
  - Very producer heavy (P = 3C)
- Finally, comparison graphs were made comparing the raw enqueue, dequeue, and dequeue-from-empty performance of each queue type
- As the NCPS queue can be used in many different configurations, each of those is shown, and on the comparison graphs, the legends indicate them with suffixes:
  - [P] on the unbounded queue means the queue was allocated to hold the entire 1000000 elements in a single bucket
  - [ET] indicates ephemeral tickets were used - that is, after every successful operation, the ticket was destroyed and recreated.
  - [NT] indicates no tickets were used, demonstrating the ticket-free API

As a note, you may notice that the 1:1 spot is missing from all of the graphs. This is because the performance in the 1:1 case is so great in the NCPS and 1024cores queues that it makes it almost impossible to see the other cases! Some of the data from the original run of these benchmarks was lost due to a hard drive failure after the graphs were made, but new benchmarks are being run and the data will be updated with new graphs that include the 1:1 case as well.
  
The code used to run these tests is also included in the benchmarks section.
