#include <stdio.h>

#ifdef EXPLICIT_DEFINE
#   define EXPLICIT_DEFINE_MESSAGE "Explicit define is present"
#else
#   define EXPLICIT_DEFINE_MESSAGE "No explicit define"
#endif

#ifdef IMPLICIT_DEFINE
#   define IMPLICIT_DEFINE_MESSAGE "Implicit define is present"
#else
#   define IMPLICIT_DEFINE_MESSAGE "No implicit define"
#endif

int main()
{
	int unused;
	printf("%s", EXPLICIT_DEFINE_MESSAGE " - " IMPLICIT_DEFINE_MESSAGE);
	return 0;
}
