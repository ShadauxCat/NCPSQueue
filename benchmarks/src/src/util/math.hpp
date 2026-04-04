#pragma once

#include <vector>
#include <stddef.h>
#include <algorithm>

int64_t mean(std::vector<int64_t> const& data)
{
	int64_t total = 0;
	for (auto& item : data)
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
	if (size % 2 == 0)
	{
		return (newVect[size / 2 - 1] + newVect[size / 2]) / 2;
	}
	return newVect[size / 2];
}

int64_t Max(std::vector<int64_t> const& data)
{
	int64_t val = 0;
	for (auto& item : data)
	{
		val = val > item ? val : item;
	}
	return val;
}

int64_t Min(std::vector<int64_t> const& data)
{
	int64_t val = (std::numeric_limits<int64_t>::max)();
	for (auto& item : data)
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