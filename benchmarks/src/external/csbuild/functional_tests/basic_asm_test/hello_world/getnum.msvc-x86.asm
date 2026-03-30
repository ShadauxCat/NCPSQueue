
; x86-specific assembly directives
.486
.model flat, c

; Begin the code section
.code

public getnum

getnum proc

	; Move the integer value "4" into the output register.
	mov eax, 4
	ret

; Function export
getnum endp
end
