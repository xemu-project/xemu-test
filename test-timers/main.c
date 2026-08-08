#include <xboxkrnl/xboxkrnl.h>
#include <pbkit/pbkit.h>
#include <hal/debug.h>
#include <hal/video.h>
#include <hal/xbox.h>
#include <windows.h>
#include "stdio.h"

#define printf debugPrint

unsigned const SAMPLE_STEP =   1000; /* ms */
unsigned const SAMPLE_END  = 315000; /* ms */

unsigned divl(unsigned long long dividend, unsigned divisor, unsigned *remainder);
unsigned long long rdtsc(void);
unsigned tsc_to_ms(unsigned long long tsc);

void main(void)
{
	unsigned long long perf_start,  perf_cur;
	unsigned long long ticks_start, ticks_cur;
	unsigned long long tsc_start,   tsc_cur;
	unsigned perf_freq, perf_delta, ticks_delta, tsc_delta, elapsed;

	XVideoSetMode(640, 480, 32, REFRESH_DEFAULT);

	/* Init graphics */
	if (pb_init()) {
		Sleep(2000);
		XReboot();
	}
	pb_show_debug_screen();

	/* Get initial reading of counters */
	perf_start  = KeQueryPerformanceCounter();
	perf_freq   = (unsigned) KeQueryPerformanceFrequency() / 1000;
	ticks_start = KeTickCount;
	tsc_start   = rdtsc();

	for (elapsed = 0; elapsed < SAMPLE_END; elapsed += SAMPLE_STEP) {
		/* Update counter readings */
		perf_cur  = KeQueryPerformanceCounter();
		ticks_cur = KeTickCount;
		tsc_cur   = rdtsc();

		/* Calculate time delta */
		perf_delta  = (ULONG)(perf_cur-perf_start) / perf_freq;
		ticks_delta = ticks_cur - ticks_start;
		tsc_delta   = tsc_to_ms(tsc_cur - tsc_start);

		/* Display counters */
		debugClearScreen();
		printf("Performance Counter: %d ms elapsed\n", perf_delta);
		printf("       Tick Counter: %d ms elapsed\n", ticks_delta);
		printf(" Time Stamp Counter: %d ms elapsed\n", tsc_delta);
		printf("\n");

		/* Wait a while for counters to advance... */
		Sleep(SAMPLE_STEP);
	}

	/* Shutdown graphics and reboot */
	pb_kill();
	XReboot();
}

/* Read the time stamp counter */
unsigned long long rdtsc(void)
{
	unsigned hi, lo;
	asm volatile ("rdtsc" : "=d" (hi), "=a" (lo));
	return ((long long) hi << 32) | lo;
}

/* Convert timestamp counter readings to milliseconds */
unsigned tsc_to_ms(unsigned long long tsc)
{
	unsigned ms, freq = 733333;
	return divl(tsc, freq, NULL);
}

/* Unsigned divide 64-bit by 32-bit */
unsigned divl(unsigned long long dividend, unsigned divisor, unsigned *remainder)
{
	unsigned hi = dividend >> 32, lo = dividend, _remainder, quotient;
	asm __volatile__ ("divl %1"
		: "=a" (quotient)
		: "r" (divisor), "d" (hi), "a" (lo));
	if (remainder) *remainder = _remainder;
	return quotient;
}
