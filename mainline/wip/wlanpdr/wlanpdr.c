// SPDX-License-Identifier: GPL-2.0
/*
 * TEST ONLY (mojito/sunny): register a PDR (service registry) listener for the
 * modem's WLAN PD, like downstream icnss does, so the modem's state indication
 * for msm/modem/wlan_pd is received and ACKed (pdr_interface ACKs automatically).
 */
#include <linux/module.h>
#include <linux/err.h>
#include <linux/soc/qcom/pdr.h>

static struct pdr_handle *pdr;

static void wlanpdr_status(int state, char *path, void *priv)
{
	pr_info("wlanpdr: %s state 0x%x\n", path, state);
}

static int __init wlanpdr_init(void)
{
	struct pdr_service *pds;

	pdr = pdr_handle_alloc(wlanpdr_status, NULL);
	if (IS_ERR(pdr))
		return PTR_ERR(pdr);
	pds = pdr_add_lookup(pdr, "wlan/fw", "msm/modem/wlan_pd");
	if (IS_ERR(pds)) {
		pdr_handle_release(pdr);
		return PTR_ERR(pds);
	}
	pr_info("wlanpdr: listening for wlan/fw on msm/modem/wlan_pd\n");
	return 0;
}

static void __exit wlanpdr_exit(void)
{
	pdr_handle_release(pdr);
}

module_init(wlanpdr_init);
module_exit(wlanpdr_exit);
MODULE_LICENSE("GPL");
