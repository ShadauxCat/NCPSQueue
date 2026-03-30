
#include <stdio.h>

extern int getnum();
extern int getextranum();

int main()
{
	printf("data = %d, %d", getnum(), getextranum());
}
