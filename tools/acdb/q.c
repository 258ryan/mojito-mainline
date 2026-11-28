#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
typedef int32_t (*ioctl_fn)(uint32_t, const void *, uint32_t, void *, uint32_t);
ioctl_fn acdb_start(const char *lib, const char *dir); void lib_verbose(int);
static uint8_t buf[1 << 20];
static void save(const char *name, uint32_t n) { char p[128]; snprintf(p, sizeof p, "out/%s.bin", name); FILE *f = fopen(p, "wb"); fwrite(buf, 1, n, f); fclose(f);
	printf("  %-18s %u bytes:", name, n); for (int i = 0; i < 12 && i * 4 < n; i++) { uint32_t v; memcpy(&v, buf + i * 4, 4); printf(" %x", v); } puts(""); }
int main(int argc, char **argv) {
	ioctl_fn io = acdb_start(argv[1], argv[2]);
	uint32_t tx = atoi(argv[3]), rx = atoi(argv[4]); uint64_t ptr = (uintptr_t)buf; uint32_t used; int r;
#pragma pack(push, 1)
	struct { uint32_t tx, rx, txrate, rxrate; } ss = { tx, rx, 48000, 48000 };
	struct { uint32_t tx, rx, txrate, rxrate, len; uint64_t ptr; } st = { tx, rx, 48000, 48000, sizeof buf, ptr };
	struct { uint32_t tx, rx, feature; } ds = { tx, rx, 0 };
	struct { uint32_t tx, rx, feature, len; uint64_t ptr; } dy = { tx, rx, 0, sizeof buf, ptr };
	struct { uint32_t tx, rx, len; uint64_t ptr; } dc = { tx, rx, sizeof buf, ptr };
	struct { uint32_t len; uint64_t ptr; } stm = { sizeof buf, ptr };
	struct { uint32_t tx, rx, type, len; uint64_t ptr; } col = { tx, rx, 0, 324, ptr };
#pragma pack(pop)
	printf("tx device %u, rx device %u\n", tx, rx);
	used = 0; r = io(0x13097, &ss, sizeof ss, &used, 4); printf("static size: %d -> %u\n", r, used);
	used = 0; r = io(0x13096, &st, sizeof st, &used, 4); printf("static table: %d\n", r); if (!r) save("vocproc_static", used);
	used = 0; r = io(0x13095, &ds, sizeof ds, &used, 4); printf("dynamic size: %d -> %u\n", r, used);
	used = 0; r = io(0x13094, &dy, sizeof dy, &used, 4); printf("dynamic table: %d\n", r); if (!r) save("vocproc_dynamic", used);
	used = 0; r = io(0x11397, &dc, sizeof dc, &used, 4); printf("device config: %d\n", r); if (!r) save("vocproc_devcfg", used);
	used = 0; r = io(0x13099, NULL, 0, &used, 4); printf("stream size: %d -> %u\n", r, used);
	used = 0; r = io(0x13098, &stm, sizeof stm, &used, 4); printf("stream table: %d\n", r); if (!r) save("stream_static", used);
	for (int t = 0; t < 4; t++) { col.type = t; memset(buf, 0, 324); used = 0; r = io(0x1309a, &col, sizeof col, &used, 4); printf("columns type %d: %d\n", t, r); if (!r) { char n[32]; snprintf(n, 32, "columns%d", t); save(n, used); } }
	struct { uint32_t a, b; } step = {0}; r = io(0x1112c, NULL, 0, &step, 8); printf("volume steps: %d -> %u %u\n", r, step.a, step.b);
	return 0;
}
