#include <dirent.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
void *lib_load(const char *, void *); void *lib_sym(const char *); void lib_verbose(int);
typedef int32_t (*ioctl_fn)(uint32_t, const void *, uint32_t, void *, uint32_t);
struct init { uint32_t n; struct { uint32_t len; char name[256]; } f[20]; };
ioctl_fn acdb_start(const char *lib, const char *dir) {
	lib_load(lib, NULL);
	ioctl_fn io = (ioctl_fn)lib_sym("acdb_ioctl"); if (!io) { fprintf(stderr, "no acdb_ioctl\n"); exit(1); }
	static struct init in; DIR *d = opendir(dir); struct dirent *e;
	while (d && (e = readdir(d))) if (strstr(e->d_name, ".acdb")) { snprintf(in.f[in.n].name, 256, "%s/%s", dir, e->d_name); in.f[in.n].len = strlen(in.f[in.n].name); in.n++; }
	int r = io(0x1138c, &in, sizeof in, NULL, 0);
	printf("initialise with %u files: %d\n", in.n, r); if (r) exit(1);
	return io;
}
#ifdef INIT_MAIN
int main(int argc, char **argv) { lib_verbose(1); acdb_start(argv[1], argv[2]); return 0; }
#endif
