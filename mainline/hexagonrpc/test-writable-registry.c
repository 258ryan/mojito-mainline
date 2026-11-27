#include <assert.h>
#include <stdio.h>
#include <string.h>
#include <sys/stat.h>
#include <unistd.h>
#include "hexagonfs.h"
#include "rpcd_builder.h"
#define R "/mnt/vendor/persist/sensors/registry/registry/"
int main(void)
{
	struct hexagonfs_fd *fds[HEXAGONFS_MAX_FD] = { 0 };
	char buf[64] = { 0 };
	int root, f, i;
	struct hexagonfs_dirent *d = construct_root_dir("fw", "adsp", "state");
	root = hexagonfs_open_root(fds, d); assert(root >= 0);
	for (i = 0; i < 2000; i++) {	/* many rounds: catches descriptor leaks */
		f = hexagonfs_create(fds, root, root, R "../temp.json", false); assert(f >= 0);
		assert(hexagonfs_write(fds, f, 5, "hello") == 5);
		assert(!hexagonfs_close(fds, f));
		assert(!hexagonfs_rename(fds, root, root, R "../temp.json", R "sns_x"));
		f = hexagonfs_openat(fds, root, root, R "sns_x"); assert(f >= 0);
		memset(buf, 0, sizeof(buf)); assert(hexagonfs_read(fds, f, 63, buf) == 5);
		assert(!strcmp(buf, "hello")); assert(!hexagonfs_close(fds, f));
	}
	assert(access("state/registry/sns_x", F_OK) == 0);
	assert(access("state/temp.json", F_OK) != 0);
	f = hexagonfs_create(fds, root, root, R "../sns_reg_version", false); assert(f >= 0); hexagonfs_close(fds, f);
	f = hexagonfs_openat(fds, root, root, R "../sns_reg_version"); assert(f >= 0); hexagonfs_close(fds, f);
	/* everything else stays read-only */
	assert(hexagonfs_create(fds, root, root, "/vendor/etc/sensors/config/evil", false) < 0);
	assert(hexagonfs_create(fds, root, root, "/vendor/etc/sensors/sns_reg_config", false) < 0);
	assert(hexagonfs_create(fds, root, root, "/mnt/vendor/persist/evil", false) < 0);
	assert(hexagonfs_create(fds, root, root, R "../../../evil", false) < 0);
	assert(hexagonfs_rename(fds, root, root, R "sns_x", "/vendor/etc/sensors/config/evil") < 0);
	assert(hexagonfs_create(fds, root, root, R "..", false) < 0);
	assert(symlink("../../fw/outside", "state/registry/link") == 0);
	assert(hexagonfs_create(fds, root, root, R "link", false) < 0);
	for (i = 0, f = 0; i < HEXAGONFS_MAX_FD; i++) f += fds[i] != NULL;
	printf("PASS, open descriptors left: %d\n", f);
	return 0;
}
