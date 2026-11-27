# Handoff: postmarketOS on the Redmi Note 10 (mojito / sunny)

State as of 2026-11-27, mainline Linux 7.4-rc4, kernel package `pkgrel=38`, device package 2-r3, installed as a package and booted through U-Boot (`boot_b`) + systemd-boot. Read this file first.
Older detail (how each thing was found, dead ends, reverse engineering): [`docs/HANDOFF-history.md`](docs/HANDOFF-history.md).

## Status

| Area | State |
|---|---|
| Boot chain: Xiaomi ABL -> U-Boot (`boot_b`) -> systemd-boot -> kernel from `/boot`; packaged (device package) | works (2026-11-27) |
| Boot, display (DPU/DSI/panel), brightness with smooth dimming, touch, GPU, Phosh | works |
| Wi-Fi (~18 s after boot), Bluetooth (~19 s) | works |
| Mobile data (LTE) | works; calls not set up |
| CPU at full speed (1.71 / 2.21 GHz) with thermal throttling at 90 / 95 C | works (DTS, pkgrel=30) |
| Accelerometer, light sensor, compass | works |
| Speakers: left = earpiece (top), right = main speaker (bottom) | works (bottom speaker fixed 2026-11-27, pkgrel=34) |
| Microphone (main, AMIC1) | works; hiss around 7 kHz, faint at the stock gain |
| Power and both volume keys, vibrator | works; very short vibration pulses are hardly felt |
| Charging from a wall charger, battery percentage | works |
| Charging from a PC USB port | broken or unreliable (old notes disagree: 500 mA / 50 mA) |
| Suspend (s2idle) | works in a 20 s test since pkgrel=29; longer sleeps, desktop-initiated sleep and power draw untested |
| Headphones, second microphone, calls, camera, GPS, NFC, fingerprint | not working or never tried |

### Added in pkgrel=29 and still to be verified by hand
Flashed to slot B (build #30) with the matching UCM. Boot checked: Wi-Fi 16 s, Bluetooth 17-19 s, modem connected, sensors,
sound card, `RX HPH Mode` names correct with value 3 = `CLS_AB`; no modem stall on this boot.
Item 1 VERIFIED: right channel heard from the bottom speaker; codec 3008=c3 3408=07, macro 0x504=18, amp registers as stock.
(It first seemed quiet in the Settings test.) UCM now uses the stock speaker levels (`RX_RX0` 84, `RX_RX2` 77,
`EAR_PA Volume` 6 = -3 dB; headphones stay at 72), confirmed good by ear while raising the volume. There is no speaker
protection processing: lower these if distortion or heating shows up.
Item 2 VERIFIED: screen off looks right (no bars).
Item 3 VERIFIED (one run): 20 s s2idle with RTC wake: screen back, ADSP and modem running, no crash lines, Wi-Fi reassociated
(gateway reachable), sensors and Bluetooth fine.

1. Patch 0019: `RX HPH Mode` item names fixed; UCM selects `CLS_AB` by name (older kernels would pick another mode).
   Check: speaker test in Phosh (both sides).
2. Patch 0005: panel blanked in `disable` (video still running). Check: screen off shows no bars.
3. Patch 0020: fastrpc invoke wait is freezable. Check: the suspend test below keeps the ADSP and Wi-Fi alive.

## Open problems, most useful first

1. **Suspend, further testing.** Fixed for a 20 s s2idle (patch 0020; before it the ADSP crashed on every resume). Still to
   check: audio after resume, long sleeps, sleep started by Phosh/gsd-power (battery, 900 s idle; goes through elogind),
   wake by power button, incoming calls/data, and idle power draw. Only `s2idle` exists. Test:
   `echo +20 > /sys/class/rtc/rtc0/wakealarm; echo freeze > /sys/power/state` (run detached; write logs to disk).
2. **Modem stalls at boot, sometimes** (`DOG detects stalled initialization` ~48 s). Seen on several boots, with stock and
   patched hexagonrpcd. `mojito-wifi` had not started hexagonrpcd yet (it waits for QMI 69, which had not appeared). It
   usually recovers; once it crashed every ~40 s until a clean reboot. Cause unknown: compare good and bad boot timelines.
3. PC-port charging (add module parameters to the SMB5 driver to try register settings live; a bad setting can suspend USBIN
   until a replug). Stock leaves `0x1366 = 0x03` on an SDP; the driver writes `0x02`.
4. Modem appears to ModemManager only ~30 s after boot (OpenRC also lists `modemmanager` as failed although it runs).
5. One boot hung at udev "Waiting for uevents" (cause unknown).
6. Pops on the speakers (2026-11-27): one at shutdown, one when the lock screen loads, one when the home screen appears; none
   from ordinary sounds or idle power cycles (tested with silent streams). Reproduced by `pulseaudio -k`: the UCM
   DisableSequence switches the amp switches off while PulseAudio's stream is still running, so DAPM powers the whole speaker
   path down mid-stream (trace: amps, EAR/AUX PGA, RDAC3/4, RX_MCLK within 20 ms). Idle power-down after the stream stops does
   not pop. PARKED (user, 2026-11-27): only at these hand-overs, never in normal use. Tried without effect: UCM disable
   sequence muting digitally + staged amp-off with msleep (the stream closes and DAPM powers down before it matters),
   20 ms amp ramp-down wait in the amp PRE_PMD (pkgrel=37, removed in 38), amp shutdown handler (kept, as vendor).
   Both paths pop on their own (only EAR or only AUX enabled), so the shared class-H/VDD_BUCK/RX clock power-down is
   the next suspect; next try: the vendor's RX mute (bolero RX_MUTE around the PA) / keeping supplies up until the PAs
   are off, in wcd937x/lpass-rx-macro.
7. Bluetooth setup flaky (any boot, with or without `clk_ignore_unused`): the second setup (bluetoothd power-on) or a
   re-probe sometimes fails during the firmware download: UART frame errors (-84), "QCA TLV response size mismatch",
   "Failed to request file: qca/cmbtfw12.tlv", retries, then hci0 is removed. Not a clock (stock leaves the 23 unclaimed
   clocks off; the UART clock chain is identical). Suspects: baud switch / flow control on the QUP UART.
8. `modprobe -r hci_uart` after such a failure oopses (NULL in `tty_lock` from `ttyport_close` <- `serdev_device_close`
   <- `hci_uart_unregister_device` <- `qca_serdev_remove`): upstream bug, closing an already closed serdev port.
9. Calls (q6voiced and surya's q6voice patches), mic noise (retest in a quiet room; speaker amps ruled out), second mic
   (needs `qcom,tx-channel-mapping` and probably driver work).

## Speakers: bottom speaker silent after boot (FIXED 2026-11-27, kernel pkgrel=34)

Symptom: the main (bottom) speaker gave no sound after every boot until its path was re-powered once during a stream
(`AUX Amp PA Switch` 0/1), then worked until the next boot. Cause, from DAPM tracing
(`/sys/kernel/tracing/events/asoc/snd_soc_dapm_widget_power`): the WCD937x RX inputs `IN1_HPHL`/`IN2_HPHR`/`IN3_AUX` are DAPM
inputs, so without routes from the RX macro outputs the codec's analog paths (RDAC3/4, EAR/AUX PGA, class-H, buck) and the
amplifiers powered up at login, with no RX clock or data, and never powered down; the AUX stage does not come up that way.
Fix: `audio-routing` `"IN1_HPHL", "HPHL_OUT"`, `"IN2_HPHR", "HPHR_OUT"`, `"IN3_AUX", "AUX_OUT"` (as upstream sm8250-mtp,
sm8450-hdk, X13s). Now the paths power with each stream after `RX_MCLK` and off when PulseAudio suspends the sink.
Also corrected (pkgrel=33): the amplifier roles were swapped. Stock DT + vendor wcd937x ("AW87xxx_SPK" after AUX PGA =
pa-channel 0): 0x5b AW87559 = main speaker on AUX ("AUX Amp"), 0x58 AW87519 = earpiece on EAR ("EAR Amp").
Ruled out on the way (for the record): amp register tables, codec/rx-macro registers (identical), SoundWire port switch,
ignored SoundWire commands (debug patch, removed in pkgrel=35). pkgrel=36 adds an amp `shutdown` handler (off table +
reset, as the vendor driver). Still open: pops (retest now that the paths follow
the stream; the vendor also mutes RX3 until the AUX PA is up and starts the SoundWire datapath in AUX PA PRE_PMU).
Vendor sources used: Neternels/android_kernel_xiaomi_sunny (techpack wcd937x, aw87xxx), LineageOS sm6150 lineage-22.2.

## CPU speed and throttling (done in pkgrel=30, DTS only)

The cpufreq hardware table offers 1017.6 / 1708.8 MHz (little) and 2016 / 2112 / 2208 MHz (big) that `talos.dtsi`
(QCS615) lacks, so `qcom-cpufreq-hw` rejected them ("Voltage update failed"). The mojito DTS adds those OPPs and gives
every CPU zone passive trips at 90 and 95 C (2 C hysteresis, 250 ms polling, step_wise); `cpuss-*` cool `cpu0`'s
policy, `cpu-1-*` `cpu6`'s (stock mapping: cpuss-2 cpu0-1, cpuss-1 cpu2-3, cpuss-0 cpu4-5, cpu-1-0/1 cpu6,
cpu-1-2/3 cpu7). Stock's kernel trips are at 110 C but Android's thermal-engine throttles earlier; we have no such daemon.

`tools/cpubench.sh`, r29 -> r30 DTB: big core 5.32 -> 4.58 s, little core 14.87 -> 13.79 s, all eight 38.73 -> 34.87 s;
86 C at the end of the run. Sustained 2.5 min all-core load: big cluster steps down 2208 -> 2112 (once 2016) MHz and holds
88-91 C; the little cluster stays at 1708.8 MHz. Not done: skin/battery temperature limits (only the SoC sensors are used).

## U-Boot (DONE 2026-11-27: flashed to `boot_b`, boots the packaged kernel)

Goal: the Xiaomi ABL chainloads generic upstream U-Boot (`qcom_defconfig` + `qcom-phone.config`, no mojito code) from
`boot_b`; U-Boot boots the kernel from `/boot` the standard way, so kernel/DTB updates stop needing hand-packed boot images.
Files: `mainline/u-boot/` (`build.sh`, config fragment `mojito.config`, `patches/`). Source: U-Boot v2026.10 (has QCS615
clock/pinctrl, the UFS/QUSB2/dwc3/SMMU drivers match talos.dtsi; USB 3 PHY has none, U-Boot forces high-speed).

Build: `mainline/u-boot/build.sh <u-boot v2026.10 git tree> <out> [debug]` (needs `gcc-aarch64-linux-gnu`; ~35 s), then
`mk-bootimg-v2.sh <out>/u-boot-nodtb.bin <mojito dtb> <empty ramdisk> u-boot.img`. Test RAM-only: `fastboot boot u-boot.img`.
`debug` starts fastboot at power-on (preboot), for `fastboot oem run:<cmd>` + `fastboot oem console`.

Verified (RAM-only, nothing flashed), 2026-11-27:
- ABL accepts the image; U-Boot runs; screen console via `cont_splash`; menu works with the keys; all 6 UFS LUNs found.
- `blkmap` exposes the pmOS partition table nested in `userdata`: partition 1 = boot (ext4, ESP type GUID), 2 = root.
  `blkmap create pmos; blkmap map pmos 0 <userdata blocks> linear scsi 0 <userdata start>` (4 KiB blocks; get both with
  `part start/size scsi 0 userdata`), then `load blkmap 0:1 ...` works.
- **Linux boots through U-Boot**: initramfs loaded from `blkmap 0:1 /initramfs`, r29 `Image` + r30 DTB sent with
  `fastboot stage`, `booti`. Display, ADSP, modem, Wi-Fi, USB networking all fine; U-Boot supplies KASLR seed and initrd.
  Linux sees 0x80000000-0x17dcfffff as RAM (3527 MB total): still to compare with a normal ABL boot.

U-Boot problems found:
1. Fixed (`patches/0001`): fastboot dequeued every completed IN request; dwc3 logs "was not queued" per reply, and with
   console recording `oem console` reads those back forever. Upstream candidate.
2. Restarting the USB gadget within one U-Boot boot fails (`dwc3 failed to enable ep0out`, `g_dnl_register -110`), e.g.
   leaving fastboot and starting the serial gadget. Only the first USB session per boot works. Cause not found yet.
3. Aborting a fastboot reply from the PC (killing `fastboot` mid-transfer) crashes U-Boot (NULL write in the
   `dwc3_gadget_ep_dequeue` path). Never put `timeout` around `fastboot oem` commands.
4. Stock 1 KiB pre-relocation console record buffer overflows; `mojito.config` enlarges it.

**EFI + systemd-boot chain works** (user's choice over extlinux), RAM-booted U-Boot `efi1`, 2026-11-27:
ABL -> U-Boot (`preboot` runs `mojito_blkmap`: finds `userdata` by name with `part start/size`, maps it as `blkmap 0`)
-> `bootefi bootmgr` finds `EFI/BOOT/BOOTAA64.EFI` on the nested boot partition (ext4 works with U-Boot's EFI file
protocol) -> systemd-boot 262.2 -> loader entry -> Linux via the EFI stub (`efi: EFI v2.11 by Das U-Boot`, efivars,
`initrd=\initramfs`). Display, Phosh, Wi-Fi, USB, ADSP, modem fine; RAM as with booti.
Test files on the phone's `/boot` (added by hand, nothing else changed): `EFI/BOOT/BOOTAA64.EFI` (from the Alpine
`systemd-boot` apk, not installed), `loader/loader.conf`, `loader/entries/mainline-test.conf`, `mainline-test/{Image,dtb}`.

Packaged (2026-11-27) in the private repo `258ryan/mojito-device` (local `~/.claude-work/mojito-device-repo`):
`device-xiaomi-mojito` pkgver 2 (mainline deviceinfo: FAT32 boot, depends on `systemd-boot`, fallback header v2
`boot.img`, `flash_kernel_on_update` off since `boot_b` holds U-Boot; services/UCM/overlays from `mainline/rootfs/`),
`hexagonrpcd-mojito`, `u-boot-xiaomi-mojito` (builds `u-boot.img`). `tools/sync-to-pmaports.sh` copies them, the
firmware package and this kernel package into pmaports. Kernel r31: DTS board-id `0x22` (ABL refuses `<0 0>`; no more
patching when packing) and `CONFIG_EFI_ZBOOT` (`/boot/linux.efi` for systemd-boot, raw `Image` as `/boot/vmlinuz` for
the fallback boot.img). Slot A (downstream 4.14 on the same rootfs) is retired by the user; its boot image is saved in
`~/.claude-work/pmos-mojito/backups/pre-mainline-device-2026-11-27/`.
Installed and flashed 2026-11-27: the packages replaced the downstream device/kernel/firmware packages, `/boot` was
reformatted to FAT32 (label `pmOS_boot`, fstab by UUID, `vfat ... umask=0077`), boot-deploy wrote `linux.efi`,
`initramfs`, the DTB, systemd-boot (`EFI/BOOT/BOOTAA64.EFI`), `loader/entries/pmos.conf` and a fallback `boot.img`;
`u-boot.img` from the package is on `boot_b`. Verified: `efi: EFI v2.11 by Das U-Boot`, r31 kernel, Phosh, Wi-Fi, sshd,
sensors service, accelerometer mount matrix, sound card, GPU firmware (from `firmware-xiaomi-mojito-mainline` through
the `/lib/firmware/postmarketos` search path). Kernel updates are now just `apk upgrade` + reboot (boot-deploy updates
`/boot`; nothing to flash). The test files, `/usr/local/bin/hexagonrpcd-mojito`, `/etc/modprobe.d/ath10k-mojito.conf`
and the hand-copied modules are gone.

Through U-Boot the kernel has SMBIOS (`/sys/class/dmi/id`: vendor `xiaomi`, product `Xiaomi Redmi Note 10`), so ASoC
names the card `xiaomi-XiaomiRedmiNote10` and UCM looks for `conf.d/sm8250/xiaomi-XiaomiRedmiNote10.conf` (device package
pkgrel 2; the old name links to it). Without it PulseAudio shows only `auto_null`.

Rescue: `build.sh <src> <out> ums` makes a U-Boot that exports `userdata` (= the pmOS disk image) to the PC as USB mass
storage at power-on; `fastboot boot` it and the PC sees `pmOS_boot` + `pmOS_root` (fsck, mount, fix, unmount). A volume
key press ends it and U-Boot boots on. `ums 0 blkmap 0` does not work (the phone resets to fastboot). Pack it with the DTB
from the packaged `u-boot.img`: ABL silently refused images packed with the r29t (r30) DTB file, and after a refused
`fastboot boot` the next one fails until fastboot is re-entered with Power + Volume-down.

## Workarounds still in place (the user wants as few as possible; fix causes, record any new shortcut)

| Workaround | Proper fix |
|---|---|
| Wi-Fi and Bluetooth loaded by a service (`mojito-wifi`), modules blacklisted from udev autoload | the order is a firmware rule (below); needs a kernel-visible "sensor PD served" signal before it can be expressed in the drivers |
| "No DSP request for 3 s" means the sensor PD is served (hexagonrpcd-mojito's `served` marker) | a real ready notification from hexagonrpcd (propose with the patch upstream) |
| Plain wallpaper (the default JPEG XL one locks up the phone at login) | find why glycin-jxl exhausts memory into a hard lock-up |
| `aw87xxx-seq` amplifier driver replaying vendor register tables | load the vendor profiles in a mainline Awinic driver |
| SMMU identity domain (0006), stopping the bootloader timing engine (0007) | upstreamable fixes |
| hexagonrpcd patch not upstream | send it |

Wi-Fi/BT ordering, findings 2026-11-27 (all tests reverted). Structure since device 2-r4 / hexagonrpcd-mojito r3:
`hexagonrpcd-mojito` (OpenRC, user fastrpc, secure node, after QMI 69) -> `/run/hexagonrpcd-mojito/served` -> `mojito-wifi`
(ath10k_snoc, then hci_uart after wlan0) and `mojito-sensors` (iio-sensor-proxy). Verified on a clean boot: no 119, Wi-Fi
connected, BT powered, sensors up. The stock hexagonrpcd-adsp-sensorspd service hard-codes `/dev/fastrpc-adsp` and the
unpatched binary; making the node configurable there is a small pmaports change worth proposing.
- Not the WCN reference clock: with `clocks = <&rpmhcc RPMH_RF_CLK2>` on the wcn3990-pmu node (sequencer "clock-enable" unit)
  and as `cxo_ref_clk_pin` on the wifi node, an early `hci_uart` (6 s) still failed and Wi-Fi then got 119. RPMh keeps the
  RF clocks on anyway.
- `hci_uart` loaded right after QMI 69 (9.5 s, before ath10k): first power-on fails, the retry works (12.3 s); then
  bluetoothd's power-cycle drops the PMU rails and BT and WLAN are both dead for the boot (119 at 14.5 s).
- With ath10k loaded first (normal order) BT power cycles are reliable (5/5): ath10k's wlan pwrseq vote keeps the shared
  PMU rails up. So the real rule is "the WCN rails must stay up once the modem has initialised the chip" (stock icnss
  votes them at boot). Proper fix direction: ath10k_snoc loadable early (retry the capability request on 119 instead of
  failing), so it holds the rails from boot; then BT can autoload.

Already removed: `clk_ignore_unused` (2026-11-27: the simple-framebuffer node now holds the 8 scan-out clocks; the
23 clocks the cleanup turns off are off in stock Android too, per its boot clock trace), hand-installed files and the borrowed downstream initramfs (device package `mojito-device`), `pd_ignore_unused`, discarded sensor-registry writes, log-line readiness guessing, numeric `RX HPH Mode`,
hand-added `audio video input` user groups (same mechanism), greeter PulseAudio `autospawn = no` (not needed: elogind's uaccess ACLs hand `/dev/snd` to the user session; verified with a
test sound 2026-11-27. The greeter's PulseAudio does NOT exit at login: its feedbackd keeps it alive, and elogind does not kill
a closed session's processes. It keeps only `controlC0` open, no PCM; stock pmOS/phrog behaviour, harmless).

## The phone (slot B; slot A retired)

- `boot_b`: U-Boot (`u-boot-xiaomi-mojito`); `dtbo_b` erased. `qbootctl` marks each boot successful. Slot A (downstream)
  is retired; its kernel package is gone.
- Packages: `device-xiaomi-mojito` (mainline, private repo `mojito-device`), `linux-postmarketos-qcom-sm6150`,
  `firmware-xiaomi-mojito-mainline` (repo `258ryan/mojito-firmware`; EFS images are in no repo), `hexagonrpcd-mojito`
  (state in `/var/lib/hexagonrpcd/mojito`), `u-boot-xiaomi-mojito`. Still added by hand: `bootmac i2c-tools libgpiod
  bluez-btmgmt wlr-randr postmarketos-ui-phosh gmobile swclock-offset`, modem userspace (`tools/install-modem-userspace.sh`).
- Rootfs grown by hand to the full userdata partition (a clean install does not do this yet).
- SSH is OpenSSH (`sshd` in the default runlevel). The downstream port used dropbear from
  `postmarketos-base-downstream-dropbear`; removing the downstream packages removed it, so `sshd` was enabled by hand.
- User `user` has the pmOS default groups only (elogind's uaccess ACLs give the active session sound, display and input).
  PulseAudio (not PipeWire) drives the card.

## Workflow

The agent may run `pmbootstrap build` with the user's sudo password (askpass from the session; never stored). Ask for the
phone SSH password each session; never store it.

1. DTS change: `python3 tools/regen-dts-patch.py`; DTS-only test without a build: `mainline/build-dtb.sh <linux-tree> out.dtb`.
2. Kernel change: add or edit patches, bump `pkgrel`, update `sha512sums`; device/firmware/U-Boot changes go in the private
   repos. `mojito-device/tools/sync-to-pmaports.sh` copies all packages into pmaports.
3. `pmbootstrap build <pkg>` (~3 min for `.c`-only kernel changes, ~13 min after config/header changes).
4. Copy the apks to the phone over Wi-Fi (`ssh ... 'cat > /var/tmp/x.apk' < x.apk`), `apk add --simulate` first and read
   **all** of its output (the purges come first), then `apk add`. boot-deploy updates `/boot`; reboot; check `uname -v`.
5. Rollback: the previous kernel apk; or boot the fallback `/boot/boot.img` with `fastboot boot`; or the UMS rescue U-Boot.

Testing rules learned: give an audible or visible positive control before asking the user to judge a test (Phosh sound test for
audio); keep tones quiet and short; make trial settings revert themselves; ask before reboots or sleep tests.

## Hazards

- Hang/crash: TLMM pins 0-3 and 6-9; an `mdss` `resets` line; `rmmod msm`; LPASS 0x62b40000; reading the modem carve-out
  (0x8b000000) or `dd` of `modemst*`/`fsg`/`fsc`.
- Do not restart the modem while IPA is up (stalls, never recovers: reboot).
- Large transfers over USB networking can freeze the phone; use Wi-Fi. USB networking sometimes drops while the phone is fine.
- A stuck phone: Power + Volume-down for 10-15 s reaches fastboot. No log survives a reset.
- The speakers have no protection algorithm.
- One-shot test boots: a systemd-boot entry `<name>+1-0.conf` (sort-key before `postmarketOS`, no loader.conf) boots once;
  systemd-boot renames it `+0-1` and the next boot falls back to `pmos.conf`. Used for the `clk_ignore_unused` tests.
- Live SoundWire debugfs register writes leave the codec's register cache stale; reboot before judging anything after them.
- The clock starts in 1970 until swclock/NTP; meson and similar reject "future" timestamps (`tar -m`).
- `pkill -f pattern` kills the calling shell if its command line contains the pattern.
- `timeout N sh -c 'a | b'` kills only the shell; the pipeline keeps running (load tests: `pkill -x sha256sum` after).
- 2026-11-27, kernel r29 (ABL boot): CPU1 stopped answering (RCU stall, no NMI response) ~2 min after reformatting
  `/boot` and writing ~50 MB to it; writeback on `loop0` hung, `sync` and reboot hung, only a hard reset helped (data
  survived). Not seen on r31 yet; watch for `rcu_preempt detected stalls`.

## Public repository

No firmware, boot images, device dumps, device identifiers, carrier or network details, or passwords. Commit as
`258ryan <20981851+258ryan@users.noreply.github.com>`. The user's standing rule: commit and push whenever something works or is
close to working. Private working files are on the build PC under `~/.claude-work/pmos-mojito/` (audio work, boot images and
rollbacks in `audio-speaker-2026-11-27/`).
