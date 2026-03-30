
.text

#ifdef IS_PLATFORM_MACOS

/* MacOS function name */
.global _getnum
_getnum:

#else

/* Linux function name */
.global getnum
getnum:

#endif

	/* Move the integer value "4" into the output register. */
#if defined(IS_ARCH_X86)
	mov $4, %eax
	ret
#elif defined(IS_ARCH_X64)
	mov $4, %rax
	ret
#elif defined(IS_ARCH_ARM_32)
	mov r0, #4
	bx lr
#elif defined(IS_ARCH_ARM_64)
	mov w0, #4
	ret
#else
	/* Cause an intentional error here for architectures that still need to be implemented. */
	Platform not implemented
#endif
