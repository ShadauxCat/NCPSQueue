#pragma once

#if defined(_WIN32)
#include <Windows.h>
#include <climits>
#include <assert.h>
#include <time.h>
#include <cstdint>


class Semaphore
{
public:
	Semaphore()
		: m_semaphore(CreateSemaphore(nullptr, 0, LONG_MAX, nullptr))
	{
		assert(m_semaphore != INVALID_HANDLE_VALUE);
	}

	~Semaphore()
	{
		CloseHandle(m_semaphore);
	}

	void Wait()
	{
		WaitForSingleObject(m_semaphore, INFINITE);
	}

	void Notify()
	{
		ReleaseSemaphore(m_semaphore, 1, nullptr);
	}
private:
	HANDLE m_semaphore;
};


#elif defined(__APPLE__)
#include <dispatch/dispatch.h>

class Semaphore
{
public:
	Semaphore()
		: m_semaphore(dispatch_semaphore_create(0))
	{
	}

	~Semaphore()
	{
		dispatch_release(m_semaphore);
	}

	void Wait()
	{
		dispatch_semaphore_wait(m_semaphore, DISPATCH_TIME_FOREVER);
	}

	void Notify()
	{
		dispatch_semaphore_signal(m_semaphore);
	}
private:

	dispatch_semaphore_t m_semaphore;
};

#elif defined(__linux__) || defined(__FreeBSD__) || defined(__ANDROID__)
#include <semaphore.h>
#include <atomic>
#include <time.h>
#include <assert.h>
#include <errno.h>

class Semaphore
{
public:
	Semaphore()
	{
		sem_init(&m_semaphore, 0, 0);
	}

	~Semaphore()
	{
		sem_destroy(&m_semaphore);
	}

	void Wait()
	{
		int ret = 0;
		do
		{
			ret = sem_wait(&m_semaphore);
		} while (ret != 0 && errno == EINTR);
		assert(ret == 0);
	}

	void Notify()
	{
		sem_post(&m_semaphore);
	}
private:
	sem_t m_semaphore;
};
#endif
