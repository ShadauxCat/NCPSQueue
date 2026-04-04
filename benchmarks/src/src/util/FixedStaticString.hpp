#pragma once

#include <memory.h>

template<size_t t_Size>
class FixedStaticString
{
public:
	FixedStaticString() {}
	FixedStaticString(int _unused) {}

	FixedStaticString(FixedStaticString const& other)
	{
		memcpy(m_str, other.m_str, t_Size);
	}

	FixedStaticString& operator=(FixedStaticString const& other)
	{
		memcpy(m_str, other.m_str, t_Size);
		return *this;
	}
private:
	char m_str[t_Size];
};