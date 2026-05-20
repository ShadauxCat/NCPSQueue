#pragma once

#include <memory.h>

template<size_t t_Size>
class FixedStaticString
{
public:
	FixedStaticString() {}
	FixedStaticString(int _unused) {}
private:
	char m_str[t_Size];
};