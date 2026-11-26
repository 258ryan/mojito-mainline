// SPDX-License-Identifier: GPL-2.0
/* TEST ONLY: vote an RPMh VRM clock resource (e.g. rfclka3) on/off from userspace.
 * echo rfclka3=1 > /sys/module/rpmhvote/parameters/vote */
#include <linux/module.h>
#include <linux/of.h>
#include <linux/of_platform.h>
#include <linux/platform_device.h>
#include <soc/qcom/cmd-db.h>
#include <soc/qcom/rpmh.h>
#include <soc/qcom/tcs.h>

static struct device *rdev;

static int vote_set(const char *val, const struct kernel_param *kp)
{
	char name[16];
	unsigned int on;
	struct tcs_cmd cmd = { 0 };
	u32 addr;
	int ret, st;

	if (sscanf(val, "%15[^=]=%u", name, &on) != 2)
		return -EINVAL;
	addr = cmd_db_read_addr(name);
	if (!addr)
		return -ENODEV;
	cmd.addr = addr + 4; /* CLK_RPMH_VRM_EN_OFFSET */
	cmd.data = on;
	for (st = RPMH_SLEEP_STATE; st <= RPMH_ACTIVE_ONLY_STATE; st++) {
		ret = rpmh_write(rdev, st, &cmd, 1);
		pr_info("rpmhvote: %s (0x%x) = %u state %d -> %d\n", name, addr, on, st, ret);
		if (ret)
			return ret;
	}
	return 0;
}

static const struct kernel_param_ops vote_ops = { .set = vote_set };
module_param_cb(vote, &vote_ops, NULL, 0200);

static int __init rpmhvote_init(void)
{
	struct device_node *np = of_find_compatible_node(NULL, NULL, "qcom,qcs615-rpmh-clk");
	struct platform_device *pdev;

	if (!np)
		return -ENODEV;
	pdev = of_find_device_by_node(np);
	of_node_put(np);
	if (!pdev)
		return -EPROBE_DEFER;
	rdev = &pdev->dev;
	pr_info("rpmhvote: using %s\n", dev_name(rdev));
	return 0;
}

static void __exit rpmhvote_exit(void)
{
	put_device(rdev);
}

module_init(rpmhvote_init);
module_exit(rpmhvote_exit);
MODULE_LICENSE("GPL");
