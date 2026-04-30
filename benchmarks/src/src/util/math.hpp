#pragma once

#include <math.h>
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

	if (size == 1)
	{
		return newVect[0];
	}
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

double Latency(int64_t duration, size_t numOps)
{
	return double(duration) / numOps;
}

int64_t Q1(std::vector<int64_t> const& data)
{
	std::vector<int64_t> newVect(data.begin(), data.end());
	std::sort(newVect.begin(), newVect.end());
	auto size = newVect.size();

	if (size == 1)
	{
		return newVect[0];
	}

	std::vector<int64_t> firsthalf;

	if (size % 2 == 0)
	{
		for (auto i = 0; i < size / 2; ++i)
		{
			firsthalf.push_back(newVect[i]);
		}
	}
	else
	{
		for (auto i = 0; i < size / 2; ++i)
		{
			firsthalf.push_back(newVect[i]);
		}
	}
	// Firsthalf - secondhalf instead of the usual secondhalf - firsthalf because these are durations,
	// but we're converting them to ops per second, meaning larger numbers become smaller numbers and these
	// arrays are actually in reverse order according to the final value they convert to.
	return median(firsthalf);
}

int64_t Q3(std::vector<int64_t> const& data)
{
	std::vector<int64_t> newVect(data.begin(), data.end());
	std::sort(newVect.begin(), newVect.end());
	auto size = newVect.size();

	if (size == 1)
	{
		return newVect[0];
	}

	std::vector<int64_t> secondhalf;

	if (size % 2 == 0)
	{
		for (auto i = size / 2; i < size; ++i)
		{
			secondhalf.push_back(newVect[i]);
		}
	}
	else
	{
		for (auto i = size / 2 + 1; i < size; ++i)
		{
			secondhalf.push_back(newVect[i]);
		}
	}
	// Firsthalf - secondhalf instead of the usual secondhalf - firsthalf because these are durations,
	// but we're converting them to ops per second, meaning larger numbers become smaller numbers and these
	// arrays are actually in reverse order according to the final value they convert to.
	return median(secondhalf);
}

double OpsPerSecondIqr(std::vector<int64_t> const& data, size_t numOps)
{
	std::vector<int64_t> newVect(data.begin(), data.end());
	std::sort(newVect.begin(), newVect.end());
	auto size = newVect.size();

	std::vector<int64_t> firsthalf;
	std::vector<int64_t> secondhalf;

	if (size % 2 == 0)
	{
		for (auto i = 0; i < size / 2; ++i)
		{
			firsthalf.push_back(newVect[i]);
		}
		for (auto i = size / 2; i < size; ++i)
		{
			secondhalf.push_back(newVect[i]);
		}
	}
	else
	{
		for (auto i = 0; i < size / 2; ++i)
		{
			firsthalf.push_back(newVect[i]);
		}
		for (auto i = size / 2 + 1; i < size; ++i)
		{
			secondhalf.push_back(newVect[i]);
		}
	}
	// Firsthalf - secondhalf instead of the usual secondhalf - firsthalf because these are durations,
	// but we're converting them to ops per second, meaning larger numbers become smaller numbers and these
	// arrays are actually in reverse order according to the final value they convert to.
	return OpsPerSecond(median(firsthalf), numOps) - OpsPerSecond(median(secondhalf), numOps);
}

std::string Bars(int64_t val, int64_t min, int64_t max, bool reverse = false)
{
	double pct = double(val - min) / double(max - min);
	if (reverse)
	{
		pct = 1.0 - pct;
	}
	pct = round(pct * 209.0);
	std::stringstream ss;

	for (int i = 0; i < pct; ++i)
	{
		ss << "|";
	}
	return ss.str();
}