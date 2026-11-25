/* Hide DRM atomic/universal-plane support so kmscon uses legacy KMS.
 * Xiaomi downstream SDE driver advertises atomic but rejects the commits. */
#define _GNU_SOURCE
#include <dlfcn.h>
#include <errno.h>
#include <stdint.h>
int drmSetClientCap(int fd, uint64_t cap, uint64_t val)
{
	static int (*real)(int, uint64_t, uint64_t);
	if (cap == 2 /* UNIVERSAL_PLANES */ || cap == 3 /* ATOMIC */)
		return -EOPNOTSUPP;
	if (!real)
		real = dlsym(RTLD_NEXT, "drmSetClientCap");
	return real(fd, cap, val);
}
