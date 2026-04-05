#pragma once

#if defined(_WIN32)
#	define NOMINMAX
#	include <Windows.h>
	using ssize_t = SSIZE_T;
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
#	include <mach/mach_time.h>
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
#	include <time.h>

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

std::atomic<int64_t> timer(-1);
std::atomic<int64_t> started(0);

void timeFn(std::function<void()> fn)
{
	++started;
	while (timer.load() == -1) {}
	fn();
	timer.store(SteadyNow());
}


template<typename t_QueueWrapper>
void latencyTestPing(t_QueueWrapper* wrapper1, t_QueueWrapper* wrapper2)
{
	++started;
	while (timer.load() == -1) {}
	for (size_t i = 0; i < NUM_ELEMENTS; ++i)
	{
		wrapper1->enqueue(1, 0);
		wrapper2->dequeue(1);
	}
	timer.store(SteadyNow());
}

template<typename t_QueueWrapper>
void latencyTestPong(t_QueueWrapper* wrapper1, t_QueueWrapper* wrapper2)
{
	++started;
	for (size_t i = 0; i < NUM_ELEMENTS; ++i)
	{
		wrapper1->dequeue(1);
		wrapper2->enqueue(1, 0);
	}
}
