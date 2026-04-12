#pragma once
#include <string>
#include <sstream>

template<typename t_Type>
struct TypeName
{
private:
	static constexpr size_t prefix_size = sizeof("static std::string TypeName<") - 1;
public:
	static std::string GetName(PointerQueuePolicy pointerQueuePolicy, TicketType ticketType, size_t batchCount, bool truncate = false)
	{
#ifdef _WIN32
		std::string ret = __FUNCTION__;
		ret = ret.substr(ret.find('<') + 7);
		ret = ret.substr(0, ret.find("GetName") - 4);
#else
		std::string ret = __PRETTY_FUNCTION__;
		ret = ret.substr(ret.find("t_Type = ") + 9);
		ret = ret.substr(0, ret.find("]"));
		ret = ret.substr(0, ret.find(";"));
#endif
		if (truncate)
		{
			ret = ret.substr(0, ret.find('<'));
		}
		switch (pointerQueuePolicy)
		{
		case PointerQueuePolicy::Preallocate:
			ret += " [Preallocated]";
			break;
		case PointerQueuePolicy::Dynamic:
			ret += " [Dynamic]";
			break;
		default:
			break;
		}
		switch (ticketType)
		{
		case TicketType::EPHEMERAL:
			ret += " [Ephemeral Tickets]";
			break;
		case TicketType::PERSISTENT:
			ret += " [Persistent Tickets]";
			break;
		case TicketType::NONE:
			ret += " [No Tickets]";
			break;
		case TicketType::BATCH:
		{
			std::stringstream num;
			num << batchCount;
			ret += " [Batch (" + num.str() + ")]";
			break;
		}
		default:
			break;
		}
		return ret;
	}
};