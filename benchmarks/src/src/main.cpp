#include <thread>
#include <vector>
#include <iostream>
#include <string>
#include <limits>
#include <functional>
#include <mutex>
#include <assert.h>
#include <unordered_map>
#include <sstream>
#include <iomanip>
#include "util/math.hpp"

#include "config.hpp"

#include "util/time.hpp"
#include "util/typename.hpp"
#include "util/FixedStaticString.hpp"

#ifdef _WIN32
#define COLOR_RED ""
#define COLOR_GREEN ""
#define COLOR_YELLOW ""
#define COLOR_CYAN ""
#define COLOR_MAGENTA ""
#define COLOR_RESET ""
#else
#define COLOR_RED "\033[1;31m"
#define COLOR_GREEN "\033[1;32m"
#define COLOR_YELLOW "\033[1;33m"
#define COLOR_CYAN "\033[1;36m"
#define COLOR_MAGENTA "\033[1;35m"
#define COLOR_RESET "\033[0m"
#endif


#ifdef VERIFY
void verify(std::string type, int operation, int producers, int consumers, int count)
{
	bool valid = true;
	int totalCount = 0;
	for (int i = 0; i < count; ++i)
	{
		if (values.find(i) == values.end())
		{
			std::cout << COLOR_RED "--> ERROR: VALUE " << i << " WAS NOT FOUND IN THE QUEUE RESULTS." COLOR_RESET << std::endl;
			valid = false;
			continue;
		}
		if (values.at(i) != 1)
		{
			std::cout << COLOR_RED "--> ERROR: VALUE " << i << " WAS DEQUEUED " << values.at(i) << " TIMES!" COLOR_RESET << std::endl;
			valid = false;
		}
		totalCount += values.at(i);
	}
	if (totalCount != count)
	{
		std::cout << COLOR_RED "--> ERROR: Total dequeue count " << totalCount << " does not match expected " << count << COLOR_RESET << std::endl;
		valid = false;
	}
	if (!valid)
	{
#if _WIN32
		__debugbreak();
#endif
		exit(1);
	}
	values.clear();
	//std::cout << COLOR_GREEN "--> Verified! " << count << " elements (" << benchmarkConfig::numElements << " adjusted for thread count) are valid." COLOR_RESET << std::endl;
}
#endif

template<typename t_QueueType>
struct BEAST_QueueSize
{
	static constexpr size_t size = 0;
};

template <typename t_ElementType, size_t t_BlockSize, bool t_EnableBatch, template<typename> typename t_AllocatorType>
struct BEAST_QueueSize<BEAST::ConcurrentQueue<t_ElementType, t_BlockSize, t_EnableBatch, t_AllocatorType>>
{
	static constexpr size_t size = t_BlockSize;
};

template <typename t_ElementType, size_t t_QueueSize, bool t_EnableBatch, template<typename> typename t_AllocatorType>
struct BEAST_QueueSize<BEAST::ConcurrentBoundedQueue<t_ElementType, t_QueueSize, t_EnableBatch, t_AllocatorType>>
{
	static constexpr size_t size = t_QueueSize;
};

template<typename t_QueueType>
struct BEAST_BatchEnabled
{
	static constexpr bool enabled = false;
};

template <typename t_ElementType, size_t t_BlockSize, bool t_EnableBatch, template<typename> typename t_AllocatorType>
struct BEAST_BatchEnabled<BEAST::ConcurrentQueue<t_ElementType, t_BlockSize, t_EnableBatch, t_AllocatorType>>
{
	static constexpr bool enabled = t_EnableBatch;
};

template <typename t_ElementType, size_t t_QueueSize, bool t_EnableBatch, template<typename> typename t_AllocatorType>
struct BEAST_BatchEnabled<BEAST::ConcurrentBoundedQueue<t_ElementType, t_QueueSize, t_EnableBatch, t_AllocatorType>>
{
	static constexpr bool enabled = t_EnableBatch;
};

template<typename t_ElementType, typename t_QueueType, TicketType t_TicketType = TicketType::NA, size_t t_BatchSize = 0, PointerQueuePolicy t_PointerQueuePolicy = PointerQueuePolicy::None>
void RunTestsOnQueueTypeWithThreadCounts(size_t enqueueThreads, size_t dequeueThreads, bool canDoEnqueueAndDequeueOnly = true)
{
	size_t adjustedNumElements = benchmarkConfig::numElements;
	while (adjustedNumElements % enqueueThreads != 0 || adjustedNumElements % dequeueThreads != 0)
	{
		--adjustedNumElements;
	}
	size_t nEnqueueElements = adjustedNumElements / enqueueThreads;
	size_t nDequeueElements = adjustedNumElements / dequeueThreads;

	size_t batchSize = t_BatchSize == 0 ? 1 : t_BatchSize;

	std::vector<int64_t> dequeues;
	dequeues.resize(dequeueThreads);
	std::vector<int64_t> enqueues;
	enqueues.resize(enqueueThreads);
	std::vector<int64_t> times[5];
	for (auto& timeVect : times)
	{
		timeVect.resize(benchmarkConfig::nIters);
	}

	std::string name = TypeName<t_QueueType>::GetName(t_PointerQueuePolicy, t_TicketType, t_BatchSize, true);
	std::string elementName = TypeName<t_ElementType>::GetName(PointerQueuePolicy::None, TicketType::NA, 0);
	std::stringstream outputLabelSS;
	outputLabelSS << name << " (" << elementName;
	if (BEAST_QueueSize<t_QueueType>::size != 0)
	{
		outputLabelSS << ", size " << BEAST_QueueSize<t_QueueType>::size;
	}
	if (BEAST_BatchEnabled<t_QueueType>::enabled)
	{
		outputLabelSS << ", +batch";
	}
	outputLabelSS << ")";
	std::string outputLabel = outputLabelSS.str();
	char progress[5] = "|/-\\";

	for (int iter = 0; iter < benchmarkConfig::nIters; ++iter)
	{
		std::cout << "(" << progress[iter % 4] << ") " COLOR_YELLOW "RUNNING " COLOR_MAGENTA << outputLabel;
		std::cout << COLOR_CYAN " [Producers: " << enqueueThreads << " | Consumers: " << dequeueThreads << "] " COLOR_GREEN "[Iteration " << iter << "]" COLOR_RESET " tests : ";
		QueueWrapper<t_QueueType, t_TicketType, t_BatchSize, t_PointerQueuePolicy> separateEnqueueDequeueWrapper;
		if constexpr (benchmarkTests::EnqueueOnly)
		{
#if RUNMODE == MODE_VERIFY
			if (canDoEnqueueAndDequeueOnly)
#else
			if ((enqueueThreads == 1 || dequeueThreads == 1) && canDoEnqueueAndDequeueOnly)
#endif
			{
				std::cout << "enq..." << std::flush;
				// Time the enqueues only.
				std::vector<std::thread> threads;

				size_t numEnqueuesToActuallyDo = enqueueThreads;
				size_t actualNEnqueueElements = nEnqueueElements;
				if (dequeueThreads != 1)
				{
					// Most queues operate faster single-threaded, and since we're only measuring raw enqueue performance once (when dequeue threads == 1),
					// we can just set it to 1 thread on all the other scenarios to make the benchmarks run faster.
					numEnqueuesToActuallyDo = 1;
					actualNEnqueueElements = adjustedNumElements;
				}
				threads.reserve(numEnqueuesToActuallyDo);

				for (size_t i = 0; i < numEnqueuesToActuallyDo; ++i)
				{
					std::function<void()> enqueueFunc = std::bind(&QueueWrapper<t_QueueType, t_TicketType, t_BatchSize, t_PointerQueuePolicy>::enqueue, &separateEnqueueDequeueWrapper, actualNEnqueueElements, actualNEnqueueElements * i, (int)i);
					threads.emplace_back(
						std::bind(
							timeFn,
							enqueueFunc
						)
					);
					if constexpr (benchmarkConfig::pinThreads)
					{
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
					}
				}
				while (started.load() < numEnqueuesToActuallyDo) {}
				started.store(0);
				int64_t start = SteadyNow();
				timer.store(start);
				for (auto& thread : threads)
				{
					thread.join();
				}
				times[0][iter] = timer.exchange(-1) - start;
			}
		}
		if constexpr (benchmarkTests::DequeueOnly)
		{
#if RUNMODE == MODE_VERIFY
			if (canDoEnqueueAndDequeueOnly)
#else
			if (enqueueThreads == 1 && canDoEnqueueAndDequeueOnly)
#endif
			{
				std::cout << "deq..." << std::flush;
				// Time the dequeues only.
				std::vector<std::thread> threads;
				threads.reserve(dequeueThreads);

				for (size_t i = 0; i < dequeueThreads; ++i)
				{
					std::function<void()> dequeueFunc = std::bind(&QueueWrapper<t_QueueType, t_TicketType, t_BatchSize, t_PointerQueuePolicy>::dequeue, &separateEnqueueDequeueWrapper, nDequeueElements, (int)i);
					threads.emplace_back(
						std::bind(
							timeFn,
							dequeueFunc
						)
					);
					if constexpr (benchmarkConfig::pinThreads)
					{
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
					}
				}
				while (started.load() < dequeueThreads) {}
				started.store(0);
				int64_t start = SteadyNow();
				timer.store(start);
				for (auto& thread : threads)
				{
					thread.join();
				}
				times[1][iter] = timer.exchange(-1) - start;
#ifdef VERIFY
				verify(outputLabel, 12, enqueueThreads, dequeueThreads, adjustedNumElements);
				std::cout << "\33[2K\r";
				std::cout << std::setw(80) << std::left << outputLabel << std::setw(0) << "\tseparate  " << std::setw(0) << "\t" << enqueueThreads << "\t" << dequeueThreads << "\t" COLOR_GREEN << "VALID!" << COLOR_RESET << std::endl;
#endif
			}
		}

		if constexpr (benchmarkTests::Concurrent)
		{
			std::cout << "enq+deq..." << std::flush;
			// Time both happening concurrently.
			QueueWrapper<t_QueueType, t_TicketType, t_BatchSize, t_PointerQueuePolicy> dualWrapper;
			std::vector<std::thread> threads;
			threads.reserve(enqueueThreads + dequeueThreads);

			int tid = 0;
			size_t enq = 0;
			size_t deq = 0;
			for (;;)
			{
				if (++deq <= dequeueThreads)
				{
					std::function<void()> fn = std::bind(&QueueWrapper<t_QueueType, t_TicketType, t_BatchSize, t_PointerQueuePolicy>::dequeue, &dualWrapper, nDequeueElements, tid++);
					threads.emplace_back(
						std::bind(
							timeFn,
							fn
						)
					);
					if constexpr (benchmarkConfig::pinThreads)
					{
#ifdef _WIN32
						if (!SetThreadAffinityMask(threads.back().native_handle(), 1 << ((enq + deq) % std::thread::hardware_concurrency())))
						{
							abort();
						}
#else
						cpu_set_t cpuset;
						pthread_t thread = threads.back().native_handle();

						CPU_ZERO(&cpuset);
						CPU_SET(((enq + deq) % std::thread::hardware_concurrency()), &cpuset);
						if (pthread_setaffinity_np(thread, sizeof(cpu_set_t), &cpuset) != 0)
						{
							abort();
						}
#endif
					}
				}
				if (++enq <= enqueueThreads)
				{
					std::function<void()> fn = std::bind(&QueueWrapper<t_QueueType, t_TicketType, t_BatchSize, t_PointerQueuePolicy>::enqueue, &dualWrapper, nEnqueueElements, nEnqueueElements * (enq - 1), tid++);
					threads.emplace_back(
						std::bind(
							timeFn,
							fn
						)
					);
					if constexpr (benchmarkConfig::pinThreads)
					{
#ifdef _WIN32
						if (!SetThreadAffinityMask(threads.back().native_handle(), 1 << ((enq + deq) % std::thread::hardware_concurrency())))
						{
							abort();
						}
#else
						cpu_set_t cpuset;
						pthread_t thread = threads.back().native_handle();

						CPU_ZERO(&cpuset);
						CPU_SET(((enq + deq) % std::thread::hardware_concurrency()), &cpuset);
						if (pthread_setaffinity_np(thread, sizeof(cpu_set_t), &cpuset))
						{
							abort();
						}
#endif
					}
				}
				if (enq >= enqueueThreads && deq >= dequeueThreads)
				{
					break;
				}
			}
			while (started.load() < dequeueThreads + enqueueThreads) {}
			started.store(0);
			int64_t start = SteadyNow();
			timer.store(start);
			for (auto& thread : threads)
			{
				thread.join();
			}
			times[2][iter] = timer.exchange(-1) - start;
#ifdef VERIFY
			verify(outputLabel, 3, enqueueThreads, dequeueThreads, adjustedNumElements);
			std::cout << "\33[2K\r";
			std::cout << std::setw(80) << std::left << outputLabel << std::setw(0) << "\tconcurrent" << std::setw(0) << "\t" << enqueueThreads << "\t" << dequeueThreads << "\t"  COLOR_GREEN << "VALID!" << COLOR_RESET << std::endl;
#endif
		}

		if constexpr (benchmarkTests::DequeueFromEmpty)
		{
			if (enqueueThreads == 1 && RUNMODE != MODE_VERIFY)
			{
				std::cout << "deq_empty(poll)..." << std::flush;
				// Time dequeues from an empty queue
				QueueWrapper<t_QueueType, t_TicketType, t_BatchSize, t_PointerQueuePolicy> emptyWrapper;
				std::vector<std::thread> threads;
				threads.reserve(dequeueThreads);

				for (size_t i = 0; i < dequeueThreads; ++i)
				{
					std::function<void()> fn = std::bind(&QueueWrapper<t_QueueType, t_TicketType, t_BatchSize, t_PointerQueuePolicy>::dequeueEmpty, &emptyWrapper, nDequeueElements * 10, (int)i);
					threads.emplace_back(
						std::bind(
							timeFn,
							fn
						)
					);
					if constexpr (benchmarkConfig::pinThreads)
					{
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
					}
				}
				while (started.load() < dequeueThreads) {}
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

		if constexpr (benchmarkTests::LatencyPingPong && RUNMODE != MODE_VERIFY)
		{
			if (enqueueThreads == 1 && dequeueThreads == 1)
			{
				std::cout << "latency..." << std::flush;
				// Time latency
				QueueWrapper<t_QueueType, t_TicketType, t_BatchSize, t_PointerQueuePolicy> wrapper1;
				QueueWrapper<t_QueueType, t_TicketType, t_BatchSize, t_PointerQueuePolicy> wrapper2;

				auto pingThread = std::thread(
					std::bind(
						latencyTestPing<QueueWrapper<t_QueueType, t_TicketType, t_BatchSize, t_PointerQueuePolicy>>,
						&wrapper1,
						&wrapper2,
						0,
						batchSize
					)
				);
				auto pongThread = std::thread(
					std::bind(
						latencyTestPong<QueueWrapper<t_QueueType, t_TicketType, t_BatchSize, t_PointerQueuePolicy>>,
						&wrapper1,
						&wrapper2,
						1,
						batchSize
					)
				);
				if constexpr (benchmarkConfig::pinThreads)
				{
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
				}
				while (started.load() < dequeueThreads) {}
				started.store(0);
				int64_t start = SteadyNow();
				timer.store(start);
				pingThread.join();
				pongThread.join();
				times[4][iter] = timer.exchange(-1) - start;
			}
		}
#if RUNMODE != MODE_VERIFY
		std::cout << "\33[2K\r";
#endif
	}

#if RUNMODE != MODE_VERIFY
	if constexpr (benchmarkTests::EnqueueOnly)
	{
		if (dequeueThreads == 1)
		{
			std::cout << std::setw(80) << std::left << outputLabel << std::setw(0) << "\tenqueue  \t" << enqueueThreads << "\t" << dequeueThreads << "\t" <<
				OpsPerSecond(median(times[0]), adjustedNumElements) << "\t" <<
				OpsPerSecond(Q3(times[0]), adjustedNumElements) << "\t" <<
				OpsPerSecond(Q1(times[0]), adjustedNumElements) << std::endl;
		}
	}

	if constexpr (benchmarkTests::DequeueOnly)
	{
		if (enqueueThreads == 1)
		{
			std::cout << std::setw(80) << std::left << outputLabel << std::setw(0) << "\tdequeue  \t" << enqueueThreads << "\t" << dequeueThreads << "\t" <<
				OpsPerSecond(median(times[1]), adjustedNumElements) << "\t" <<
				OpsPerSecond(Q3(times[1]), adjustedNumElements) << "\t" <<
				OpsPerSecond(Q1(times[1]), adjustedNumElements) << std::endl;
		}
	}

	if constexpr (benchmarkTests::Concurrent)
	{
		std::cout << std::setw(80) << std::left << outputLabel << std::setw(0) << "\tenq+deq  \t" << enqueueThreads << "\t" << dequeueThreads << "\t" <<
			OpsPerSecond(median(times[2]), adjustedNumElements) << "\t" <<
			OpsPerSecond(Q3(times[2]), adjustedNumElements) << "\t" <<
			OpsPerSecond(Q1(times[2]), adjustedNumElements) << std::endl;
	}


	if constexpr (benchmarkTests::DequeueFromEmpty)
	{
		if (enqueueThreads == 1)
		{
			std::cout << std::setw(80) << std::left << outputLabel << std::setw(0) << "\tdeq_empty\t" << enqueueThreads << "\t" << dequeueThreads << "\t" <<
				OpsPerSecond(median(times[3]), adjustedNumElements * 10) << "\t" <<
				OpsPerSecond(Q3(times[3]), adjustedNumElements * 10) << "\t" <<
				OpsPerSecond(Q1(times[3]), adjustedNumElements * 10) << std::endl;
		}
	}

	if constexpr (benchmarkTests::LatencyPingPong && RUNMODE != MODE_VERIFY)
	{
		if (enqueueThreads == 1 && dequeueThreads == 1)
		{
			std::cout << std::setw(80) << std::left << outputLabel << std::setw(0) << "\tlatency  \t" << enqueueThreads << "\t" << dequeueThreads << "\t" <<
				Latency(median(times[4]), benchmarkConfig::numElements / 10) / batchSize / 2 << "\t" <<
				Latency(Q1(times[4]), benchmarkConfig::numElements / 10) / batchSize / 2 << "\t" <<
				Latency(Q3(times[4]), benchmarkConfig::numElements / 10) / batchSize / 2 << std::endl;
		}
	}
#endif
}

template<typename t_ElementType, typename t_QueueType, TicketType t_TicketType = TicketType::NA, size_t t_BatchSize = 0, PointerQueuePolicy t_PointerQueuePolicy = PointerQueuePolicy::None>
void RunTestsOnQueueType(bool canDoEnqueueAndDequeueOnly = true)
{
	for (size_t i = MIN_PRODUCERS; i <= MAX_PRODUCERS; ++i) {
		for (size_t j = MIN_CONSUMERS; j <= MAX_CONSUMERS; ++j) {
			RunTestsOnQueueTypeWithThreadCounts<t_ElementType, t_QueueType, t_TicketType, t_BatchSize, t_PointerQueuePolicy>(i, j, canDoEnqueueAndDequeueOnly);
		}
	}
}

template<typename t_ElementType, typename t_QueueType>
void PrintEmpty()
{
	for (size_t i = MIN_PRODUCERS; i <= MAX_PRODUCERS; ++i) {
		for (size_t j = MIN_CONSUMERS; j <= MAX_CONSUMERS; ++j) {
			std::cout << TypeName<t_QueueType>::GetName(PointerQueuePolicy::None, TicketType::NA, 0) << "\t" << 0 << "\t" << 0 << "\t" << 0 << "\t" << 0 << std::endl;
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
	RunTestsOnQueueType<t_ElementType, BitNextQueue<t_ElementType>, TicketType::NA, 0, PointerQueuePolicy::Dynamic>();
	RunTestsOnQueueType<t_ElementType, BitNextQueue<t_ElementType>, TicketType::NA, 0, PointerQueuePolicy::Preallocate>();
	RunTestsOnQueueType<t_ElementType, BitNextLazyHeadQueue<t_ElementType>, TicketType::NA, 0, PointerQueuePolicy::Dynamic>();
	RunTestsOnQueueType<t_ElementType, BitNextLazyHeadQueue<t_ElementType>, TicketType::NA, 0, PointerQueuePolicy::Preallocate>();
#endif

#ifdef HAS_CR
	// Excluded: Crashes
	//RunTestsOnQueueType<t_ElementType, CRDoubleLinkQueue<t_ElementType>, TicketType::NA, 0, PointerQueuePolicy::Dynamic>();
	//RunTestsOnQueueType<t_ElementType, CRDoubleLinkQueue<t_ElementType>, TicketType::NA, 0, PointerQueuePolicy::Preallocate>();
	RunTestsOnQueueType<t_ElementType, CRTurnQueue<t_ElementType>, TicketType::NA, 0, PointerQueuePolicy::Dynamic>();
	RunTestsOnQueueType<t_ElementType, CRTurnQueue<t_ElementType>, TicketType::NA, 0, PointerQueuePolicy::Preallocate>();
#endif

#ifdef HAS_FAAARRAYQUEUE
	RunTestsOnQueueType<t_ElementType, FAAArrayQueue<t_ElementType>, TicketType::NA, 0, PointerQueuePolicy::Dynamic>();
	RunTestsOnQueueType<t_ElementType, FAAArrayQueue<t_ElementType>, TicketType::NA, 0, PointerQueuePolicy::Preallocate>();
#endif

#ifdef HAS_KOGANPETRANK
	RunTestsOnQueueType<t_ElementType, KoganPetrankQueueCHP<t_ElementType>, TicketType::NA, 0, PointerQueuePolicy::Dynamic>();
	RunTestsOnQueueType<t_ElementType, KoganPetrankQueueCHP<t_ElementType>, TicketType::NA, 0, PointerQueuePolicy::Preallocate>();
#endif

#ifdef HAS_LAZYINDEXARRAYQUEUE
	RunTestsOnQueueType<t_ElementType, LazyIndexArrayQueue<t_ElementType>, TicketType::NA, 0, PointerQueuePolicy::Dynamic>();
	RunTestsOnQueueType<t_ElementType, LazyIndexArrayQueue<t_ElementType>, TicketType::NA, 0, PointerQueuePolicy::Preallocate>();
#endif

#ifdef HAS_LCRQ
	RunTestsOnQueueType<t_ElementType, LCRQueue<t_ElementType>, TicketType::NA, 0, PointerQueuePolicy::Dynamic>();
	RunTestsOnQueueType<t_ElementType, LCRQueue<t_ElementType>, TicketType::NA, 0, PointerQueuePolicy::Preallocate>();
#endif

#ifdef HAS_LINEARARRAYQUEUE
	RunTestsOnQueueType<t_ElementType, LinearArrayQueue<t_ElementType>, TicketType::NA, 0, PointerQueuePolicy::Dynamic>();
	RunTestsOnQueueType<t_ElementType, LinearArrayQueue<t_ElementType>, TicketType::NA, 0, PointerQueuePolicy::Preallocate>();
#endif

#ifdef HAS_LOG2ARRAYQUEUE
	RunTestsOnQueueType<t_ElementType, Log2ArrayQueue<t_ElementType>, TicketType::NA, 0, PointerQueuePolicy::Dynamic>();
	RunTestsOnQueueType<t_ElementType, Log2ArrayQueue<t_ElementType>, TicketType::NA, 0, PointerQueuePolicy::Preallocate>();
#endif

#ifdef HAS_MICHAELSCOTTQUEUE
	RunTestsOnQueueType<t_ElementType, MichaelScottQueue<t_ElementType>, TicketType::NA, 0, PointerQueuePolicy::Dynamic>();
	RunTestsOnQueueType<t_ElementType, MichaelScottQueue<t_ElementType>, TicketType::NA, 0, PointerQueuePolicy::Preallocate>();
#endif

#ifdef HAS_CHASEWORKSTEALINGDEQUE
	RunTestsOnQueueType<
		t_ElementType,
		xenium::chase_work_stealing_deque<t_ElementType, xenium::policy::reclaimer<xenium::reclamation::epoch_based<>>, xenium::policy::entries_per_node<8192>>,
		TicketType::NA, 0, PointerQueuePolicy::Dynamic
	>();
	RunTestsOnQueueType<
		t_ElementType,
		xenium::chase_work_stealing_deque<t_ElementType, xenium::policy::reclaimer<xenium::reclamation::epoch_based<>>, xenium::policy::entries_per_node<8192>>,
		TicketType::NA, 0, PointerQueuePolicy::Preallocate
	>();
#endif

#ifdef HAS_KIRSCH
	RunTestsOnQueueType<
		t_ElementType,
		xenium::kirsch_bounded_kfifo_queue<t_ElementType*, xenium::policy::reclaimer<xenium::reclamation::epoch_based<>>, xenium::policy::entries_per_node<8192>>,
		TicketType::NA, 0, PointerQueuePolicy::Dynamic
	>();
	RunTestsOnQueueType<
		t_ElementType,
		xenium::kirsch_bounded_kfifo_queue<t_ElementType*, xenium::policy::reclaimer<xenium::reclamation::epoch_based<>>, xenium::policy::entries_per_node<8192>>,
		TicketType::NA, 0, PointerQueuePolicy::Preallocate
	>();
	RunTestsOnQueueType<
		t_ElementType,
		xenium::kirsch_kfifo_queue<t_ElementType*, xenium::policy::reclaimer<xenium::reclamation::epoch_based<>>, xenium::policy::entries_per_node<8192>>,
		TicketType::NA, 0, PointerQueuePolicy::Dynamic
	>();
	RunTestsOnQueueType<
		t_ElementType,
		xenium::kirsch_kfifo_queue<t_ElementType*, xenium::policy::reclaimer<xenium::reclamation::epoch_based<>>, xenium::policy::entries_per_node<8192>>,
		TicketType::NA, 0, PointerQueuePolicy::Preallocate
	>();
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
	RunTestsOnQueueType<
		t_ElementType,
		xenium::ramalhete_queue<t_ElementType*, xenium::policy::reclaimer<xenium::reclamation::epoch_based<>>, xenium::policy::entries_per_node<8192>>
		, TicketType::NA, 0, PointerQueuePolicy::Dynamic
	>();
	RunTestsOnQueueType<
		t_ElementType,
		xenium::ramalhete_queue<t_ElementType*, xenium::policy::reclaimer<xenium::reclamation::epoch_based<>>, xenium::policy::entries_per_node<8192>>,
		TicketType::NA, 0, PointerQueuePolicy::Preallocate
	>();
#endif

#ifdef HAS_VYUKOVBOUNDEDQUEUE
	RunTestsOnQueueType<t_ElementType, xenium::vyukov_bounded_queue<t_ElementType, xenium::policy::reclaimer<xenium::reclamation::epoch_based<>>, xenium::policy::entries_per_node<8192>>>();
#endif

#ifdef HAS_BEAST_UNBOUNDED
	RunTestsOnQueueType<t_ElementType, BEAST::ConcurrentQueue<t_ElementType, 8192, false>, TicketType::PERSISTENT>();
	RunTestsOnQueueType<t_ElementType, BEAST::ConcurrentQueue<t_ElementType, 8192, false>, TicketType::EPHEMERAL>();
	RunTestsOnQueueType<t_ElementType, BEAST::ConcurrentQueue<t_ElementType, 8192, false>, TicketType::NONE>();
	RunTestsOnQueueType<t_ElementType, BEAST::ConcurrentQueue<t_ElementType, 8192, true>, TicketType::BATCH, 1>();
	RunTestsOnQueueType<t_ElementType, BEAST::ConcurrentQueue<t_ElementType, 8192, true>, TicketType::BATCH, 10>();
	RunTestsOnQueueType<t_ElementType, BEAST::ConcurrentQueue<t_ElementType, 8192, true>, TicketType::BATCH, 100>();
	RunTestsOnQueueType<t_ElementType, BEAST::ConcurrentQueue<t_ElementType, 8192, true>, TicketType::BATCH, 1000>();
	RunTestsOnQueueType<t_ElementType, BEAST::ConcurrentQueue<t_ElementType, 8192, true>, TicketType::PERSISTENT>();
	RunTestsOnQueueType<t_ElementType, BEAST::ConcurrentQueue<t_ElementType, 8192, true>, TicketType::EPHEMERAL>();
	RunTestsOnQueueType<t_ElementType, BEAST::ConcurrentQueue<t_ElementType, 8192, true>, TicketType::NONE>();

	RunTestsOnQueueType<t_ElementType, BEAST::ConcurrentQueue<t_ElementType, benchmarkConfig::numElements, false>, TicketType::PERSISTENT>();
	RunTestsOnQueueType<t_ElementType, BEAST::ConcurrentQueue<t_ElementType, benchmarkConfig::numElements, false>, TicketType::EPHEMERAL>();
	RunTestsOnQueueType<t_ElementType, BEAST::ConcurrentQueue<t_ElementType, benchmarkConfig::numElements, false>, TicketType::NONE>();
	RunTestsOnQueueType<t_ElementType, BEAST::ConcurrentQueue<t_ElementType, benchmarkConfig::numElements, true>, TicketType::BATCH, 1>();
	RunTestsOnQueueType<t_ElementType, BEAST::ConcurrentQueue<t_ElementType, benchmarkConfig::numElements, true>, TicketType::BATCH, 10>();
	RunTestsOnQueueType<t_ElementType, BEAST::ConcurrentQueue<t_ElementType, benchmarkConfig::numElements, true>, TicketType::BATCH, 100>();
	RunTestsOnQueueType<t_ElementType, BEAST::ConcurrentQueue<t_ElementType, benchmarkConfig::numElements, true>, TicketType::BATCH, 1000>();
	RunTestsOnQueueType<t_ElementType, BEAST::ConcurrentQueue<t_ElementType, benchmarkConfig::numElements, true>, TicketType::PERSISTENT>();
	RunTestsOnQueueType<t_ElementType, BEAST::ConcurrentQueue<t_ElementType, benchmarkConfig::numElements, true>, TicketType::EPHEMERAL>();
	RunTestsOnQueueType<t_ElementType, BEAST::ConcurrentQueue<t_ElementType, benchmarkConfig::numElements, true>, TicketType::NONE>();


#endif

#ifdef HAS_BEAST_BOUNDED
	// Ephemeral tickets aren't benchmarked on the bounded queue as there's no initialization that needs to be done on a ticket,
	// ergo no real advantage of persistent over ephemeral.
	RunTestsOnQueueType<t_ElementType, BEAST::ConcurrentBoundedQueue<t_ElementType, 8192, false>, TicketType::PERSISTENT>(false);
	RunTestsOnQueueType<t_ElementType, BEAST::ConcurrentBoundedQueue<t_ElementType, 8192, false>, TicketType::NONE>(false);
	RunTestsOnQueueType<t_ElementType, BEAST::ConcurrentBoundedQueue<t_ElementType, 8192, true>, TicketType::BATCH, 1>(false);
	RunTestsOnQueueType<t_ElementType, BEAST::ConcurrentBoundedQueue<t_ElementType, 8192, true>, TicketType::BATCH, 10>(false);
	RunTestsOnQueueType<t_ElementType, BEAST::ConcurrentBoundedQueue<t_ElementType, 8192, true>, TicketType::BATCH, 100>(false);
	RunTestsOnQueueType<t_ElementType, BEAST::ConcurrentBoundedQueue<t_ElementType, 8192, true>, TicketType::BATCH, 1000>(false);
	RunTestsOnQueueType<t_ElementType, BEAST::ConcurrentBoundedQueue<t_ElementType, 8192, true>, TicketType::PERSISTENT>(false);
	RunTestsOnQueueType<t_ElementType, BEAST::ConcurrentBoundedQueue<t_ElementType, 8192, true>, TicketType::NONE>(false);

	RunTestsOnQueueType<t_ElementType, BEAST::ConcurrentBoundedQueue<t_ElementType, 32768, false>, TicketType::PERSISTENT>(false);
	RunTestsOnQueueType<t_ElementType, BEAST::ConcurrentBoundedQueue<t_ElementType, 32768, false>, TicketType::NONE>(false);
	RunTestsOnQueueType<t_ElementType, BEAST::ConcurrentBoundedQueue<t_ElementType, 32768, true>, TicketType::BATCH, 1>(false);
	RunTestsOnQueueType<t_ElementType, BEAST::ConcurrentBoundedQueue<t_ElementType, 32768, true>, TicketType::BATCH, 10>(false);
	RunTestsOnQueueType<t_ElementType, BEAST::ConcurrentBoundedQueue<t_ElementType, 32768, true>, TicketType::BATCH, 100>(false);
	RunTestsOnQueueType<t_ElementType, BEAST::ConcurrentBoundedQueue<t_ElementType, 32768, true>, TicketType::BATCH, 1000>(false);
	RunTestsOnQueueType<t_ElementType, BEAST::ConcurrentBoundedQueue<t_ElementType, 32768, true>, TicketType::PERSISTENT>(false);
	RunTestsOnQueueType<t_ElementType, BEAST::ConcurrentBoundedQueue<t_ElementType, 32768, true>, TicketType::NONE>(false);

	RunTestsOnQueueType<t_ElementType, BEAST::ConcurrentBoundedQueue<t_ElementType, 65536, false>, TicketType::PERSISTENT>(false);
	RunTestsOnQueueType<t_ElementType, BEAST::ConcurrentBoundedQueue<t_ElementType, 65536, false>, TicketType::NONE>(false);
	RunTestsOnQueueType<t_ElementType, BEAST::ConcurrentBoundedQueue<t_ElementType, 65536, true>, TicketType::BATCH, 1>(false);
	RunTestsOnQueueType<t_ElementType, BEAST::ConcurrentBoundedQueue<t_ElementType, 65536, true>, TicketType::BATCH, 10>(false);
	RunTestsOnQueueType<t_ElementType, BEAST::ConcurrentBoundedQueue<t_ElementType, 65536, true>, TicketType::BATCH, 100>(false);
	RunTestsOnQueueType<t_ElementType, BEAST::ConcurrentBoundedQueue<t_ElementType, 65536, true>, TicketType::BATCH, 1000>(false);
	RunTestsOnQueueType<t_ElementType, BEAST::ConcurrentBoundedQueue<t_ElementType, 65536, true>, TicketType::PERSISTENT>(false);
	RunTestsOnQueueType<t_ElementType, BEAST::ConcurrentBoundedQueue<t_ElementType, 65536, true>, TicketType::NONE>(false);

	RunTestsOnQueueType<t_ElementType, BEAST::ConcurrentBoundedQueue<t_ElementType, 131072, false>, TicketType::PERSISTENT>(false);
	RunTestsOnQueueType<t_ElementType, BEAST::ConcurrentBoundedQueue<t_ElementType, 131072, false>, TicketType::NONE>(false);
	RunTestsOnQueueType<t_ElementType, BEAST::ConcurrentBoundedQueue<t_ElementType, 131072, true>, TicketType::BATCH, 1>(false);
	RunTestsOnQueueType<t_ElementType, BEAST::ConcurrentBoundedQueue<t_ElementType, 131072, true>, TicketType::BATCH, 10>(false);
	RunTestsOnQueueType<t_ElementType, BEAST::ConcurrentBoundedQueue<t_ElementType, 131072, true>, TicketType::BATCH, 100>(false);
	RunTestsOnQueueType<t_ElementType, BEAST::ConcurrentBoundedQueue<t_ElementType, 131072, true>, TicketType::BATCH, 1000>(false);
	RunTestsOnQueueType<t_ElementType, BEAST::ConcurrentBoundedQueue<t_ElementType, 131072, true>, TicketType::PERSISTENT>(false);
	RunTestsOnQueueType<t_ElementType, BEAST::ConcurrentBoundedQueue<t_ElementType, 131072, true>, TicketType::NONE>(false);

	RunTestsOnQueueType<t_ElementType, BEAST::ConcurrentBoundedQueue<t_ElementType, benchmarkConfig::numElements, false>, TicketType::PERSISTENT>();
	RunTestsOnQueueType<t_ElementType, BEAST::ConcurrentBoundedQueue<t_ElementType, benchmarkConfig::numElements, false>, TicketType::NONE>();
	RunTestsOnQueueType<t_ElementType, BEAST::ConcurrentBoundedQueue<t_ElementType, benchmarkConfig::numElements, true>, TicketType::BATCH, 1>();
	RunTestsOnQueueType<t_ElementType, BEAST::ConcurrentBoundedQueue<t_ElementType, benchmarkConfig::numElements, true>, TicketType::BATCH, 10>();
	RunTestsOnQueueType<t_ElementType, BEAST::ConcurrentBoundedQueue<t_ElementType, benchmarkConfig::numElements, true>, TicketType::BATCH, 100>();
	RunTestsOnQueueType<t_ElementType, BEAST::ConcurrentBoundedQueue<t_ElementType, benchmarkConfig::numElements, true>, TicketType::BATCH, 1000>();
	RunTestsOnQueueType<t_ElementType, BEAST::ConcurrentBoundedQueue<t_ElementType, benchmarkConfig::numElements, true>, TicketType::PERSISTENT>();
	RunTestsOnQueueType<t_ElementType, BEAST::ConcurrentBoundedQueue<t_ElementType, benchmarkConfig::numElements, true>, TicketType::NONE>();
#endif
}

int main()
{
	std::cout << std::fixed << std::setprecision(3);

#ifdef VERIFY
	std::cout << std::endl << std::endl << std::setw(80) << std::left << "QUEUE" << std::setw(0) << "\t" << std::setw(10) << "TEST" << std::setw(0) << "\tPRODS\tCONS\tRESULT" << std::endl;
	std::cout << "---------------------------------------------------------------------------------------------------------------------------------" << std::endl;
	RunTestsOnElementType<int>();
#else
	std::cout << std::endl << std::endl << std::setw(80) << std::left << "QUEUE" << std::setw(0) << "\t" << std::setw(9) << "TEST" << std::setw(0) << "\tPRODS\tCONS\tMEDIAN\t\tQ1\t\tQ3" << std::endl;
	std::cout << "----------------------------------------------------------------------------------------------------------------------------------------------------------------------" << std::endl;

	if constexpr (benchmarkTypes::Char)
	{
		RunTestsOnElementType<char>();
	}

	if constexpr (benchmarkTypes::Int64)
	{
		RunTestsOnElementType<int64_t>();
	}

	if constexpr (benchmarkTypes::FixedString64Bytes)
	{
		RunTestsOnElementType<FixedStaticString<64>, false>();
	}
#endif
	std::cout << "Done testing, press ENTER to exit." << std::endl;
	getchar();
}

