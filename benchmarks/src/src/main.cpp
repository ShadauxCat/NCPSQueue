#include <thread>
#include <vector>
#include <iostream>
#include <string>
#include <limits>
#include <functional>
#include <mutex>
#include <assert.h>
#include <unordered_map>

#include "config.hpp"

#include "util/time.hpp"
#include "util/typename.hpp"
#include "util/math.hpp"
#include "util/FixedStaticString.hpp"

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


template<typename t_ElementType, typename t_QueueType, TicketType t_TicketType = TicketType::NONE, size_t t_BatchSize = 0>
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
	std::vector<int64_t> times[5];
	for (auto& timeVect : times)
	{
		timeVect.resize(nIters);
	}

	for (int iter = 0; iter < nIters; ++iter)
	{
		QueueWrapper<t_QueueType, t_TicketType, t_BatchSize> separateEnqueueDequeueWrapper;
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
				std::function<void()> enqueueFunc = std::bind(&QueueWrapper<t_QueueType, t_TicketType, t_BatchSize>::enqueue, &separateEnqueueDequeueWrapper, actualNEnqueueElements, actualNEnqueueElements*i);
				threads.emplace_back(
					std::bind(
						timeFn,
						enqueueFunc
					)
				);
	#if PIN_THREADS
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
				std::function<void()> dequeueFunc = std::bind(&QueueWrapper<t_QueueType, t_TicketType, t_BatchSize>::dequeue, &separateEnqueueDequeueWrapper, nDequeueElements);
				threads.emplace_back(
					std::bind(
						timeFn,
						dequeueFunc
					)
				);
#if PIN_THREADS
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
			verify(TypeName<t_QueueType>::GetName(useMoves, t_TicketType, t_BatchSize), 12, enqueueThreads, dequeueThreads, adjustedNumElements);
#endif
		}

		{
			// Time both happening concurrently.
			QueueWrapper<t_QueueType, t_TicketType, t_BatchSize> dualWrapper;
			std::vector<std::thread> threads;
			threads.reserve(enqueueThreads + dequeueThreads);

			size_t enq = 0;
			size_t deq = 0;
			for (;;)
			{
				if (++deq <= dequeueThreads)
				{
					std::function<void()> fn = std::bind(&QueueWrapper<t_QueueType, t_TicketType, t_BatchSize>::dequeue, &dualWrapper, nDequeueElements);
					threads.emplace_back(
						std::bind(
							timeFn,
							fn
						)
					);
#if PIN_THREADS
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
					std::function<void()> fn = std::bind(&QueueWrapper<t_QueueType, t_TicketType, t_BatchSize>::enqueue, &dualWrapper, nEnqueueElements, nEnqueueElements*(enq - 1));
					threads.emplace_back(
						std::bind(
							timeFn,
							fn
						)
					);
#if PIN_THREADS
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
			verify(TypeName<t_QueueType>::GetName(useMoves, t_TicketType, t_BatchSize), 3, enqueueThreads, dequeueThreads, adjustedNumElements);
#endif
		}

		if(enqueueThreads == 1)
		{
			// Time dequeues from an empty queue
			QueueWrapper<t_QueueType, t_TicketType, t_BatchSize> emptyWrapper;
			std::vector<std::thread> threads;
			threads.reserve(dequeueThreads);

			for (size_t i = 0; i < dequeueThreads; ++i)
			{
				std::function<void()> fn = std::bind(&QueueWrapper<t_QueueType, t_TicketType, t_BatchSize>::dequeueEmpty, &emptyWrapper, nDequeueElements * 10);
				threads.emplace_back(
					std::bind(
						timeFn,
						fn
					)
				);
#if PIN_THREADS
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

		if (enqueueThreads == 1 && dequeueThreads == 1)
		{
			// Time latency
			QueueWrapper<t_QueueType, t_TicketType, t_BatchSize> wrapper1;
			QueueWrapper<t_QueueType, t_TicketType, t_BatchSize> wrapper2;

			auto pingThread = std::thread(
				std::bind(
					latencyTestPing<QueueWrapper<t_QueueType, t_TicketType, t_BatchSize>>,
					&wrapper1,
					&wrapper2
				)
			);
			auto pongThread = std::thread(
				std::bind(
					latencyTestPong<QueueWrapper<t_QueueType, t_TicketType, t_BatchSize>>,
					&wrapper1,
					&wrapper2
				)
			);
#if PIN_THREADS
#ifdef _WIN32
			if (!SetThreadAffinityMask(pingThread.native_handle(), 1 << (0 % std::thread::hardware_concurrency())))
			{
				abort();
			}
			if (!SetThreadAffinityMask(pongThread.native_handle(), 1 << (1 % std::thread::hardware_concurrency())))
			{
				abort();
			}
#else
			cpu_set_t cpuset;
			pthread_t thread = pingThread.native_handle();

			CPU_ZERO(&cpuset);
			CPU_SET((0 % std::thread::hardware_concurrency()), &cpuset);
			if (pthread_setaffinity_np(thread, sizeof(cpu_set_t), &cpuset) != 0)
			{
				abort();
			}
			
			thread = pongThread.native_handle();

			CPU_ZERO(&cpuset);
			CPU_SET((1 % std::thread::hardware_concurrency()), &cpuset);
			if (pthread_setaffinity_np(thread, sizeof(cpu_set_t), &cpuset) != 0)
			{
				abort();
			}
#endif
#endif
			while (started.load() < dequeueThreads) {}
			started.store(0);
			int64_t start = SteadyNow();
			timer.store(start);
			pingThread.join();
			pongThread.join();
			times[4][iter] = timer.exchange(-1) - start;
		}
	}

	if(dequeueThreads == 1)
	{
		std::cout << TypeName<t_QueueType>::GetName(useMoves, t_TicketType, t_BatchSize) << "\t" << 1 << "\t" << enqueueThreads << "\t" << dequeueThreads << "\t" <<
			OpsPerSecond(mean(times[0]), adjustedNumElements) << "\t" <<
			OpsPerSecond(Max(times[0]), adjustedNumElements) << "\t" <<
			OpsPerSecond(Min(times[0]), adjustedNumElements) << "\t" <<
			OpsPerSecond(median(times[0]), adjustedNumElements) << std::endl;
	}
		
	if(enqueueThreads == 1)
	{
		std::cout << TypeName<t_QueueType>::GetName(useMoves, t_TicketType, t_BatchSize) << "\t" << 2 << "\t" << enqueueThreads << "\t" << dequeueThreads << "\t" <<
			OpsPerSecond(mean(times[1]), adjustedNumElements) << "\t" <<
			OpsPerSecond(Max(times[1]), adjustedNumElements) << "\t" <<
			OpsPerSecond(Min(times[1]), adjustedNumElements) << "\t" <<
			OpsPerSecond(median(times[1]), adjustedNumElements) << std::endl;
	}
		
	std::cout << TypeName<t_QueueType>::GetName(useMoves, t_TicketType, t_BatchSize) << "\t" << 3 << "\t" << enqueueThreads << "\t" << dequeueThreads << "\t" <<
		OpsPerSecond(mean(times[2]), adjustedNumElements) << "\t" <<
		OpsPerSecond(Max(times[2]), adjustedNumElements) << "\t" <<
		OpsPerSecond(Min(times[2]), adjustedNumElements) << "\t" <<
		OpsPerSecond(median(times[2]), adjustedNumElements) << std::endl;
		

	if (enqueueThreads == 1)
	{
		std::cout << TypeName<t_QueueType>::GetName(useMoves, t_TicketType, t_BatchSize) << "\t" << 4 << "\t" << enqueueThreads << "\t" << dequeueThreads << "\t" <<
			OpsPerSecond(mean(times[3]), adjustedNumElements * 10) << "\t" <<
			OpsPerSecond(Max(times[3]), adjustedNumElements * 10) << "\t" <<
			OpsPerSecond(Min(times[3]), adjustedNumElements * 10) << "\t" <<
			OpsPerSecond(median(times[3]), adjustedNumElements) << std::endl;
	}
	if (enqueueThreads == 1 && dequeueThreads == 1)
	{
		std::cout << TypeName<t_QueueType>::GetName(useMoves, t_TicketType, t_BatchSize) << "\t" << 5 << "\t" << enqueueThreads << "\t" << dequeueThreads << "\t" <<
			OpsPerSecond(mean(times[4]), adjustedNumElements * 10) << "\t" <<
			OpsPerSecond(Max(times[4]), adjustedNumElements * 10) << "\t" <<
			OpsPerSecond(Min(times[4]), adjustedNumElements * 10) << "\t" <<
			OpsPerSecond(median(times[4]), adjustedNumElements) << std::endl;
	}
}

template<typename t_ElementType, typename t_QueueType, TicketType t_TicketType = TicketType::NONE, size_t t_BatchSize = 0>
void RunTestsOnQueueType(bool useMoves = false)
{
	for (size_t i = MIN_PRODUCERS; i <= MAX_PRODUCERS; ++i) {
		for (size_t j = MIN_CONSUMERS; j <= MAX_CONSUMERS; ++j) {
			RunTestsOnQueueTypeWithThreadCounts<t_ElementType, t_QueueType, t_TicketType, t_BatchSize>(i, j, useMoves);
		}
	}
}

template<typename t_ElementType, typename t_QueueType>
void PrintEmpty()
{
	for (size_t i = MIN_PRODUCERS; i <= MAX_PRODUCERS; ++i) {
		for (size_t j = MIN_CONSUMERS; j <= MAX_CONSUMERS; ++j) {
			std::cout << TypeName<t_QueueType>::GetName(false, TicketType::NONE, 0) << "\t" << 0 << "\t" << 0 << "\t" << 0 << "\t" << 0 << std::endl;
		}
	}
}

template<typename t_ElementType, bool t_IsPod = true>
void RunTestsOnElementType()
{
#ifdef HAS_DEQUE
	RunTestsOnQueueType<t_ElementType, std::deque<t_ElementType>>();
#endif

#ifdef HAS_1024CORES
	RunTestsOnQueueType<t_ElementType, ext_1024cores::mpmc_bounded_queue<t_ElementType>>();
#endif

#ifdef HAS_TBB
	RunTestsOnQueueType<t_ElementType, tbb::concurrent_bounded_queue<t_ElementType>>();
	RunTestsOnQueueType<t_ElementType, tbb::concurrent_queue<t_ElementType>>();
#endif

#ifdef HAS_BOOST
	if constexpr (t_IsPod)
	{
		RunTestsOnQueueType<t_ElementType, boost::lockfree::queue<t_ElementType>>();
	}
	else
	{
		PrintEmpty<t_ElementType, boost::lockfree::queue<t_ElementType>>();
	}
#endif

#ifdef HAS_BITNEXT
	RunTestsOnQueueType<t_ElementType, BitNextQueue<t_ElementType>>();
	RunTestsOnQueueType<t_ElementType, BitNextLazyHeadQueue<t_ElementType>>();
#endif

#ifdef HAS_CR
	// Excluded: Crashes
	//RunTestsOnQueueType<t_ElementType, CRDoubleLinkQueue<t_ElementType>>();
	RunTestsOnQueueType<t_ElementType, CRTurnQueue<t_ElementType>>();
#endif

#ifdef HAS_FAAARRAYQUEUE
	RunTestsOnQueueType<t_ElementType, FAAArrayQueue<t_ElementType>>();
#endif

#ifdef HAS_KOGANPETRANK
	RunTestsOnQueueType<t_ElementType, KoganPetrankQueueCHP<t_ElementType>>();
#endif

#ifdef HAS_LAZYINDEXARRAYQUEUE
	RunTestsOnQueueType<t_ElementType, LazyIndexArrayQueue<t_ElementType>>();
#endif

#ifdef HAS_LCRQ
	RunTestsOnQueueType<t_ElementType, LCRQueue<t_ElementType>>();
#endif

#ifdef HAS_LINEARARRAYQUEUE
	RunTestsOnQueueType<t_ElementType, LinearArrayQueue<t_ElementType>>();
#endif

#ifdef HAS_LOG2ARRAYQUEUE
	RunTestsOnQueueType<t_ElementType, Log2ArrayQueue<t_ElementType>>();
#endif

#ifdef HAS_MICHAELSCOTTQUEUE
	RunTestsOnQueueType<t_ElementType, MichaelScottQueue<t_ElementType>>();
#endif

#ifdef HAS_CHASEWORKSTEALINGDEQUE
	RunTestsOnQueueType<t_ElementType, xenium::chase_work_stealing_deque<t_ElementType, xenium::policy::reclaimer<xenium::reclamation::epoch_based<>>, xenium::policy::entries_per_node<8192>>>();
#endif

#ifdef HAS_KIRSCH
	RunTestsOnQueueType<t_ElementType, xenium::kirsch_bounded_kfifo_queue<t_ElementType*, xenium::policy::reclaimer<xenium::reclamation::epoch_based<>>, xenium::policy::entries_per_node<8192>>>();
	RunTestsOnQueueType<t_ElementType, xenium::kirsch_kfifo_queue<t_ElementType*, xenium::policy::reclaimer<xenium::reclamation::epoch_based<>>, xenium::policy::entries_per_node<8192>>>();
#endif

#ifdef HAS_XENIUM_MICHAELSCOTT
	RunTestsOnQueueType<t_ElementType, xenium::michael_scott_queue<t_ElementType, xenium::policy::reclaimer<xenium::reclamation::epoch_based<>>, xenium::policy::entries_per_node<8192>>>();
#endif

#ifdef HAS_NIKOLAEV
	RunTestsOnQueueType<t_ElementType, xenium::nikolaev_bounded_queue<t_ElementType, xenium::policy::reclaimer<xenium::reclamation::epoch_based<>>, xenium::policy::entries_per_node<8192>>>();
	//Hangs in release builds
	//RunTestsOnQueueType<t_ElementType, xenium::nikolaev_queue<t_ElementType, xenium::policy::reclaimer<xenium::reclamation::epoch_based<>>, xenium::policy::entries_per_node<8192>>>();
#endif

#ifdef HAS_RAMALHETE
	RunTestsOnQueueType<t_ElementType, xenium::ramalhete_queue<t_ElementType*, xenium::policy::reclaimer<xenium::reclamation::epoch_based<>>, xenium::policy::entries_per_node<8192>>>();
#endif

#ifdef HAS_VYUKOVBOUNDEDQUEUE
	RunTestsOnQueueType<t_ElementType, xenium::vyukov_bounded_queue<t_ElementType, xenium::policy::reclaimer<xenium::reclamation::epoch_based<>>, xenium::policy::entries_per_node<8192>>>();
#endif

#ifdef HAS_BEFAST_UNBOUNDED
	RunTestsOnQueueType<t_ElementType, BEFAST::ConcurrentQueue<t_ElementType, 8192, true>>();
	RunTestsOnQueueType<t_ElementType, BEFAST::ConcurrentQueue<t_ElementType, 8192, false>>();
	RunTestsOnQueueType<t_ElementType, BEFAST::ConcurrentQueue<t_ElementType, 8192, true>, TicketType::BATCH, 1>();
	RunTestsOnQueueType<t_ElementType, BEFAST::ConcurrentQueue<t_ElementType, 8192, true>, TicketType::BATCH, 10>();
	RunTestsOnQueueType<t_ElementType, BEFAST::ConcurrentQueue<t_ElementType, 8192, true>, TicketType::BATCH, 100>();
	RunTestsOnQueueType<t_ElementType, BEFAST::ConcurrentQueue<t_ElementType, 8192, true>, TicketType::BATCH, 1000>();

	RunTestsOnQueueType<t_ElementType, BEFAST::ConcurrentQueue<t_ElementType, NUM_ELEMENTS, true>>();
	RunTestsOnQueueType<t_ElementType, BEFAST::ConcurrentQueue<t_ElementType, NUM_ELEMENTS, false>>();
	RunTestsOnQueueType<t_ElementType, BEFAST::ConcurrentQueue<t_ElementType, NUM_ELEMENTS, true>, TicketType::BATCH, 1>();
	RunTestsOnQueueType<t_ElementType, BEFAST::ConcurrentQueue<t_ElementType, NUM_ELEMENTS, true>, TicketType::BATCH, 10>();
	RunTestsOnQueueType<t_ElementType, BEFAST::ConcurrentQueue<t_ElementType, NUM_ELEMENTS, true>, TicketType::BATCH, 100>();
	RunTestsOnQueueType<t_ElementType, BEFAST::ConcurrentQueue<t_ElementType, NUM_ELEMENTS, true>, TicketType::BATCH, 1000>();

	RunTestsOnQueueType<t_ElementType, BEFAST::ConcurrentQueue<t_ElementType, 8192, true>, TicketType::EPHEMERAL>();
	RunTestsOnQueueType<t_ElementType, BEFAST::ConcurrentQueue<t_ElementType, NUM_ELEMENTS, true>, TicketType::EPHEMERAL>();
	RunTestsOnQueueType<t_ElementType, BEFAST::ConcurrentQueue<t_ElementType, 8192, false>, TicketType::EPHEMERAL>();
	RunTestsOnQueueType<t_ElementType, BEFAST::ConcurrentQueue<t_ElementType, NUM_ELEMENTS, false>, TicketType::EPHEMERAL>();

	RunTestsOnQueueType<t_ElementType, BEFAST::ConcurrentQueue<t_ElementType, 8192, true>, TicketType::NONE>();
	RunTestsOnQueueType<t_ElementType, BEFAST::ConcurrentQueue<t_ElementType, NUM_ELEMENTS, true>, TicketType::NONE>();
	RunTestsOnQueueType<t_ElementType, BEFAST::ConcurrentQueue<t_ElementType, 8192, false>, TicketType::NONE>();
	RunTestsOnQueueType<t_ElementType, BEFAST::ConcurrentQueue<t_ElementType, NUM_ELEMENTS, false>, TicketType::NONE>();
#endif

#ifdef HAS_BEFAST_BOUNDED
	/*RunTestsOnQueueType<t_ElementType, BEFAST::ConcurrentBoundedQueue<t_ElementType, 8192, true>>();
	RunTestsOnQueueType<t_ElementType, BEFAST::ConcurrentBoundedQueue<t_ElementType, 8192, false>>();
	RunTestsOnQueueType<t_ElementType, BEFAST::ConcurrentBoundedQueue<t_ElementType, 8192, true>, TicketType::BATCH, 1>();
	RunTestsOnQueueType<t_ElementType, BEFAST::ConcurrentBoundedQueue<t_ElementType, 8192, true>, TicketType::BATCH, 10>();
	RunTestsOnQueueType<t_ElementType, BEFAST::ConcurrentBoundedQueue<t_ElementType, 8192, true>, TicketType::BATCH, 100>();
	RunTestsOnQueueType<t_ElementType, BEFAST::ConcurrentBoundedQueue<t_ElementType, 8192, true>, TicketType::BATCH, 1000>();
	RunTestsOnQueueType<t_ElementType, BEFAST::ConcurrentBoundedQueue<t_ElementType, 8192>, TicketType::NONE>();*/

	RunTestsOnQueueType<t_ElementType, BEFAST::ConcurrentBoundedQueue<t_ElementType, NUM_ELEMENTS, true>>();
	RunTestsOnQueueType<t_ElementType, BEFAST::ConcurrentBoundedQueue<t_ElementType, NUM_ELEMENTS, false>>();
	RunTestsOnQueueType<t_ElementType, BEFAST::ConcurrentBoundedQueue<t_ElementType, NUM_ELEMENTS, true>, TicketType::BATCH, 1>();
	RunTestsOnQueueType<t_ElementType, BEFAST::ConcurrentBoundedQueue<t_ElementType, NUM_ELEMENTS, true>, TicketType::BATCH, 10>();
	RunTestsOnQueueType<t_ElementType, BEFAST::ConcurrentBoundedQueue<t_ElementType, NUM_ELEMENTS, true>, TicketType::BATCH, 100>();
	RunTestsOnQueueType<t_ElementType, BEFAST::ConcurrentBoundedQueue<t_ElementType, NUM_ELEMENTS, true>, TicketType::BATCH, 1000>();
	RunTestsOnQueueType<t_ElementType, BEFAST::ConcurrentBoundedQueue<t_ElementType, NUM_ELEMENTS>, TicketType::NONE>();
#endif
}

int main()
{
	std::cout << std::fixed;
#ifdef VERIFY
	RunTestsOnElementType<int>();
#else
#if BENCHMARK_CHAR
	RunTestsOnElementType<char>();
#endif

#if BENCHMARK_INT64
	RunTestsOnElementType<int64_t>();
#endif

#if BENCHMARK_FIXEDSTRING64BYTES
	RunTestsOnElementType<FixedStaticString<64>, false>();
#endif
#endif
	std::cout << "Done testing, press any key to exit." << std::endl;
	std::string discard;
	std::cin >> discard;
}

