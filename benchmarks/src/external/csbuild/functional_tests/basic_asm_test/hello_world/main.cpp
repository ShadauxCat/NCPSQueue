
#include <stdio.h>

extern "C"
{
	extern int getnum();
}

int main()
{
	printf("getnum() = %d", getnum());
	return 0;
}
