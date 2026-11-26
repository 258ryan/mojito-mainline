/* rwatch: poll registers and print every change with a CLOCK_MONOTONIC timestamp.
 *   rwatch <seconds> < list        list lines:  m <hex physaddr>   (MMIO via /dev/mem)
 *                                               0|1|2|3 <hex reg>  (regmap file N from argv)
 *   argv[2..5] = regmap "registers" files for indices 0..3
 * Freestanding arm64, so the same binary runs on Android and pmOS. */
static long sys(long n, long a, long b, long c, long d, long e, long f)
{
	register long x8 __asm__("x8") = n, x0 __asm__("x0") = a, x1 __asm__("x1") = b,
		x2 __asm__("x2") = c, x3 __asm__("x3") = d, x4 __asm__("x4") = e, x5 __asm__("x5") = f;
	__asm__ volatile("svc 0" : "+r"(x0) : "r"(x8), "r"(x1), "r"(x2), "r"(x3), "r"(x4), "r"(x5) : "memory", "cc");
	return x0;
}
#define MAXI 900
struct item { char kind; unsigned long addr; volatile unsigned int *mm; unsigned int last; int seen; } it[MAXI];
static char out[1 << 16]; static int on;
static void flush(void) { if (on) sys(64, 1, (long)out, on, 0, 0, 0); on = 0; }
static void put(char c) { out[on++] = c; if (on > (int)sizeof(out) - 64) flush(); }
static void hex(unsigned long v, int w) { for (int i = (w - 1) * 4; i >= 0; i -= 4) put("0123456789abcdef"[(v >> i) & 15]); }
static void dec(unsigned long v, int w) { char b[24]; int n = 0; do { b[n++] = '0' + v % 10; v /= 10; } while (v || n < w); while (n) put(b[--n]); }
static unsigned long now_us(void) { long t[2]; sys(113, 1, (long)t, 0, 0, 0, 0); return t[0] * 1000000UL + t[1] / 1000; }
static int hv(char c) { return c >= '0' && c <= '9' ? c - '0' : c >= 'a' && c <= 'f' ? c - 'a' + 10 : -1; }
__attribute__((used)) static void run(long *sp)
{
	long argc = sp[0]; char **argv = (char **)(sp + 1);
	unsigned long secs = 0; for (char *p = argc > 1 ? argv[1] : "20"; *p; p++) secs = secs * 10 + *p - '0';
	int rm[4] = { -1, -1, -1, -1 };
	for (int i = 0; i < 4 && i + 2 < argc; i++) rm[i] = sys(56, -100, (long)argv[i + 2], 0, 0, 0, 0);
	long mem = sys(56, -100, (long)"/dev/mem", 04010000, 0, 0, 0);
	static char in[1 << 16]; long len = 0, r;
	while ((r = sys(63, 0, (long)(in + len), sizeof(in) - 1 - len, 0, 0, 0)) > 0) len += r;
	int n = 0;
	for (long i = 0; i < len && n < MAXI; ) {
		char k = in[i]; unsigned long a = 0; i += 2;
		while (i < len && hv(in[i]) >= 0) a = a << 4 | hv(in[i++]);
		while (i < len && in[i++] != '\n') ;
		it[n].kind = k; it[n].addr = a;
		if (k == 'm') {
			long m = sys(222, 0, 4096, 1, 1, mem, a & ~0xfffUL);
			if (m < 0 && m > -4096) continue;
			it[n].mm = (volatile unsigned int *)(m + (a & 0xffc));
		} else if (k < '0' || k > '3' || rm[k - '0'] < 0) continue;
		n++;
	}
	unsigned long start = now_us(), end = start + secs * 1000000UL, polls = 0, t = start;
	while (t < end) {
		for (int i = 0; i < n; i++) {
			unsigned int v;
			if (it[i].kind == 'm') v = *it[i].mm;
			else {
				char b[9];
				if (sys(67, rm[it[i].kind - '0'], (long)b, 9, it[i].addr * 9, 0, 0) != 9 || hv(b[6]) < 0) continue;
				v = hv(b[6]) << 4 | hv(b[7]);
			}
			if (!it[i].seen || v != it[i].last) {
				t = now_us(); dec(t / 1000000, 1); put('.'); dec(t % 1000000, 6); put(' ');
				put(it[i].kind); put(' '); hex(it[i].addr, 8); put(' '); hex(v, 8); put('\n');
				it[i].last = v; it[i].seen = 1;
			}
		}
		flush(); polls++; t = now_us();
	}
	out[on++] = '#'; out[on++] = ' '; dec(n, 1); put(' '); dec(polls, 1); put('\n'); flush();
	sys(93, 0, 0, 0, 0, 0, 0);
}
__asm__(".global _start\n_start:\n mov x0, sp\n and sp, x0, #-16\n bl run\n");
