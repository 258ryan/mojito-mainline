# Work in progress (not in the verified package)

## SMB5 charger (battery/charging)

`0008-power-supply-add-the-Qualcomm-SMB5-charger-driver.patch` + `charger-dts.txt`.

Status: **compiles (clang, 7.4-rc4), untested on hardware.** Not listed in `APKBUILD` on purpose: the package at `pkgrel=12` is the
verified baseline. To try it: add the patch to `source` and `sha512sums`, set `CONFIG_CHARGER_QCOM_SMB5=m` in the config, paste the
fragment from `charger-dts.txt` into the DTS (it is two small blocks plus a battery node), bump `pkgrel`, build, install the modules
with `tools/install-modules.sh`, flash the image.

What was verified from sources: the charger is in PM6150 (SID 0), not PM6150L; the register bases (CHGR 0x1000, DCDC 0x1100, BATIF
0x1200, USBIN 0x1300, TYPEC 0x1500, MISC 0x1600), `CHARGING_ENABLE_CMD` (0x42), the float-voltage register (0x70, 3.6 V + n x 10 mV, up
to 4.79 V) and the fast-charge step (50 mA) all match Xiaomi's vendor driver (`drivers/power/supply/qcom/smb5-reg.h`, `qpnp-smb5.c`
in the pinned downstream commit). Battery (vendor profile): 5000 mAh, max 4.45 V.

Do NOT use the original pipa patch 0018 as is: it disables charging at probe (right for a tablet driven by a userspace service, wrong
here). The port here keeps charging enabled and only takes its float-voltage fix.

Safe bring-up order: (1) boot with the driver and read `power_supply` values only, no cable; (2) plug in and watch `usb_in_v` and the
battery voltage rise; (3) keep `constant-charge-current-max-microamp` at 2 A until temperatures are known; watch the battery
temperature. The bq2597x charge pump (i2c3, 0x65) is not needed for basic charging; leave it alone.

There is no fuel-gauge driver for this phone's QG block (`qgauge@4800`): the pipa package's `qcom_fg.c` supports the FG gen3/gen4 blocks,
which are different. For a battery percentage either write a small voltage-to-percentage `power_supply` from the PMIC ADC (battery
voltage and temperature channels need adding to `pm6150_adc`; `ADC5_VBAT_SNS`=0x84, `ADC5_BAT_THERM`=0x0a) or port QG.
`generic-adc-battery` does NOT provide a percentage.

Sources: the Linaro series "pmi8998 charger improvements and smb5 support" (June 2025, 11 patches; only the rename to `qcom_smbx` is in
7.4-rc4; its patch 9/11 adds SMB5 support but was not confirmed merged), and the postmarketOS pmaports package
`device/testing/linux-xiaomi-pipa` (patches 0002 and 0018) which this port comes from.
