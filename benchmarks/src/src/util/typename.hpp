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
		ret = ret.substr(ret.find('<')+1);
		if (ret.find("class") != std::string::npos)
		{
			ret = ret.substr(6, ret.length() - 6);
			ret = ret.substr(0, ret.find("GetName") - 4);
		}
		else
		{
			ret = ret.substr(0, ret.find("GetName") - 3);
		}
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
		case TicketType::SEMAPHORE:
			ret += " [Semaphore]";
			break;
		case TicketType::BATCH:
		{
			std::stringstream num;
			num << batchCount;
			ret += " [Batch (" + num.str() + ")]";
			break;
		}
		case TicketType::WAIT:
			ret += " [Blocking]";
			break;
		case TicketType::BATCHWAIT:
		{
			std::stringstream num;
			num << batchCount;
			ret += " [Blocking Batch (" + num.str() + ")]";
			break;
		}
		default:
			break;
		}
		return ret;
	}
};

#ifdef HAS_MOODYCAMEL
template<typename t_ElementType, size_t t_Size>
struct TypeName<MoodyCamelWithSize<t_ElementType, t_Size>>
{
	static std::string GetName(PointerQueuePolicy pointerQueuePolicy, TicketType ticketType, size_t batchCount, bool truncate = false)
	{
		std::string ret = TypeName<moodycamel::ConcurrentQueue<t_ElementType>>::GetName(PointerQueuePolicy::None, TicketType::NA, 0, truncate);

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
		case TicketType::PERSISTENT:
			ret += " [With Tokens]";
			break;
		case TicketType::NONE:
			ret += " [No Tokens]";
			break;
		case TicketType::SEMAPHORE:
			ret += " [Semaphore]";
			break;
		case TicketType::BATCH:
		{
			std::stringstream num;
			num << batchCount;
			ret += " [Batch (" + num.str() + ")]";
			break;
		}
		case TicketType::BATCHWITHTOKEN:
		{
			std::stringstream num;
			num << batchCount;
			ret += " [Batch With Tokens (" + num.str() + ")]";
			break;
		}
		default:
			break;
		}
		return ret;
	}
};

template<typename t_ElementType, size_t t_Size>
struct TypeName<BlockingMoodyCamelWithSize<t_ElementType, t_Size>>
{
	static std::string GetName(PointerQueuePolicy pointerQueuePolicy, TicketType ticketType, size_t batchCount, bool truncate = false)
	{
		std::string ret = TypeName<moodycamel::BlockingConcurrentQueue<t_ElementType>>::GetName(PointerQueuePolicy::None, TicketType::NA, 0, truncate);

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
		case TicketType::PERSISTENT:
			ret += " [With Tokens]";
			break;
		case TicketType::NONE:
			ret += " [No Tokens]";
			break;
		case TicketType::SEMAPHORE:
			ret += " [Semaphore]";
			break;
		case TicketType::BATCH:
		{
			std::stringstream num;
			num << batchCount;
			ret += " [Batch (" + num.str() + ")]";
			break;
		}
		case TicketType::BATCHWITHTOKEN:
		{
			std::stringstream num;
			num << batchCount;
			ret += " [Batch With Tokens (" + num.str() + ")]";
			break;
		}
		default:
			break;
		}
		return ret;
	}
};
#endif