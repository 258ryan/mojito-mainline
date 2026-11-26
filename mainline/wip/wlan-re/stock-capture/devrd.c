/* devrd: print 32-bit physical registers. Reads hex addresses from stdin, one per line.
 * Freestanding arm64 (raw syscalls) so the same binary runs on Android and pmOS. */
static long sys(long n, long a, long b, long c, long d, long e, long f)
{
	register long x8 __asm__("x8") = n, x0 __asm__("x0") = a, x1 __asm__("x1") = b,
		x2 __asm__("x2") = c, x3 __asm__("x3") = d, x4 __asm__("x4") = e, x5 __asm__("x5") = f;
	__asm__ volatile("svc 0" : "+r"(x0) : "r"(x8), "r"(x1), "r"(x2), "r"(x3), "r"(x4), "r"(x5) : "memory", "cc");
	return x0;
}
static void hex(char *p, unsigned long v) { for (int i = 7; i >= 0; i--, v >>= 4) p[i] = "0123456789abcdef"[v & 15]; }
void _start(void)
{
	long fd = sys(56, -100, (long)"/dev/mem", 04010000 /* O_RDONLY|O_SYNC */, 0, 0, 0);
	if (fd < 0) { sys(64, 2, (long)"cannot open /dev/mem\n", 21, 0, 0, 0); sys(93, 1, 0, 0, 0, 0, 0); }
	unsigned long addr = 0; int have = 0; char c;
	for (;;) {
		long r = sys(63, 0, (long)&c, 1, 0, 0, 0);
		int v = c >= '0' && c <= '9' ? c - '0' : c >= 'a' && c <= 'f' ? c - 'a' + 10 : -1;
		if (r == 1 && v >= 0) { addr = addr << 4 | v; have = 1; continue; }
		if (r == 1 && c == 'x') { addr = 0; have = 0; continue; }
		if (have) {
			char out[18]; hex(out, addr); out[8] = ' ';
			sys(64, 1, (long)out, 9, 0, 0, 0);          /* address first, so a hang names itself */
			long m = sys(222, 0, 4096, 1 /* PROT_READ */, 1 /* MAP_SHARED */, fd, addr & ~0xfffUL);
			if (m < 0 && m > -4096) { sys(64, 1, (long)"mapfail \n", 9, 0, 0, 0); }
			else {
				unsigned int val = *(volatile unsigned int *)(m + (addr & 0xffc));
				hex(out + 9, val); out[17] = '\n';
				sys(64, 1, (long)(out + 9), 9, 0, 0, 0);
				sys(215, m, 4096, 0, 0, 0, 0);
			}
		}
		addr = 0; have = 0;
		if (r != 1) break;
	}
	sys(93, 0, 0, 0, 0, 0, 0);
}
