#pragma once

#include <pthread.h>
#include <mach/thread_act.h>
#include <sys/sysctl.h>

#define SYSCTL_CORE_COUNT "machdep.cpu.core_count"
#define CPU_SET_FORCE_INLINE __attribute__((always_inline))

typedef struct cpu_set
{
	uint32_t count;
} cpu_set_t;

static CPU_SET_FORCE_INLINE void CPU_ZERO(cpu_set_t* const cs)
{
	cs->count = 0;
}

static CPU_SET_FORCE_INLINE void CPU_SET(const int32_t coreIndex, cpu_set_t* const cs)
{
	cs->count |= 1 << static_cast<uint32_t>(coreIndex);
}

static CPU_SET_FORCE_INLINE int CPU_ISSET(const int32_t coreIndex, cpu_set_t* const cs)
{
	return cs->count & (1 << static_cast<uint32_t>(coreIndex));
}

static int32_t sched_getaffinity(const pid_t pid, const size_t cpuSize, cpu_set_t* cs)
{
	int32_t coreCount = 0;
	size_t countLength = sizeof(coreCount);

	const int32_t ret = sysctlbyname(SYSCTL_CORE_COUNT, &coreCount, &countLength, 0, 0);
	if (ret)
	{
		errno = ret;
		return -1;
	}

	CPU_ZERO(cs);
	for (int32_t i = 0; i < coreCount; ++i)
	{
		CPU_SET(i, cs);
	}

	return 0;
}

static int32_t pthread_setaffinity_np(pthread_t thread, const size_t cpuSetSizeInBytes, cpu_set_t* cs)
{
	const int32_t totalPossibleCoreCount = 8 * static_cast<int32_t>(cpuSetSizeInBytes);

	int32_t coreIndex = 0;
	for(; coreIndex < totalPossibleCoreCount; ++coreIndex)
	{
		if(CPU_ISSET(coreIndex, cs))
		{
			break;
		}
	}

	thread_affinity_policy_data_t policy = { coreIndex };
	thread_port_t machThread =  pthread_mach_thread_np(thread);

	thread_policy_set(machThread, THREAD_AFFINITY_POLICY, reinterpret_cast<thread_policy_t>(&policy), 1);

	return 0;
}

#undef SYSCTL_CORE_COUNT
#undef CPU_SET_FORCE_INLINE
