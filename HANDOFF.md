# Handoff: postmarketOS on the Redmi Note 10 (mojito/sunny)

For the next agent picking this up. Read the START HERE section, then the rest as needed, before touching the phone.
State as of 2026-11-27 (Wi-Fi work 2026-11-26/27).

## START HERE (2026-11-27, end of the long session): where things stand

### Volume-up and vibration work (2026-11-27, verified by hand; phone boot_b = r27 Image + `r27/boot_b-r27-keys.img` DTB)
- Volume-up is PM6150L (SID 4) GPIO 2; the DTS pointed at the PM6150's GPIO 2.
- Vibrator: stock "lct-pwm-vibrator" = PM6150L LPG channel at 0xbc00 (pwm index 3, 50 us) out of PM6150L GPIO 6, enable TLMM 112;
  mainline `pwm-vibrator` + `leds-qcom-lpg` (both modules). A 3 s full-strength rumble is felt; 0.15 s full and 0.4 s half-strength
  pulses were not clearly felt, so Phosh haptic feedback may need a longer/stronger theme (not tested).
- The package patch 0001 is regenerated (pkgrel 28, not built).

### Housekeeping done 2026-11-27 (evening)
- `qbootctl` + `qbootctl-openrc` installed and in runlevel default (slot B `Successful: 1`): plain reboots no longer burn retries.
- Greeter PulseAudio disabled: `mainline/rootfs/var/lib/greetd/.config/pulse/client.conf` (`autospawn = no`), install owned by greetd.

### Update, later still on 2026-11-27: MICROPHONE WORKS (main mic, AMIC1)
Cause of the exact zeros: the capture link used `<&swr_tx 0>`; the TX controller has `dout-ports = 1`, so DAI 0 is playback-only, the
capture stream never allocated a master port (all 0x11xx-0x14xx port registers zero). Fix: `<&swr_tx 1>` (master port 2 now shows
0x1224 = 0x01000103). Phone boot_b = r27 Image + new DTB (`r27/boot_b-r27-mic.img`); the package is pkgrel=28 with the regenerated
patch 0001, NOT BUILT. Voice is audible: UCM default `ADC1 Volume` 12 (stock) is faint, 20 is louder with more hiss; not decided,
UCM unchanged. Quiet-room test still needed: noise centred 4-8 kHz (peaks ~7.2 kHz), scales with ADC gain, unchanged with both
speaker amps off; the user was in a loudish room. Second mic untested: DT lacks `qcom,tx-channel-mapping` (stock: ADC2 = master port
2 channel mask 0x2), and 7.4-rc4 qcom.c takes the slave channel mask, so ADC2 may need driver work.

### Update, later on 2026-11-27: BOTH SPEAKERS WORK (kernel pkgrel=27, build #28 on slot B)
Confirmed by ear in Phosh: left = earpiece (top, amp 0x5b, EAR path), right = main speaker (bottom, amp 0x58, AUX path); music OK.
The earlier "speaker works" below was only the earpiece. What the main speaker needed:
1. Patch 0017 (wcd937x: reference-count the RX clock; the second user took no reference, the first teardown gated clock + bias:
   `clk already disabled`, 0x3408/0x3008 bit0 cleared during playback) and patch 0018 (lpass-rx-macro: AUX `DLY_Z_EN` was cleared
   instead of set; stock 0x504 = 0x18). Installed together; which one is strictly required was NOT separated.
2. UCM `cset "name='RX HPH Mode' 3"` (class AB, as stock). The enum text has an extra `CLS_H_INVALID`, so item 3 reads "CLS_H_LP"
   but is CLS_AB (writing 0 also maps to AB). On the old kernel this setting alone did not give sound.
Still open / observed: with only RX1 in use (INT1 or INT2 fed from RX1, nothing on RX0) aplay fails with I/O error (stereo is fine);
the amps stay powered with the PCM closed; a quiet high-pitched squeal occurred on the OLD kernel with RDAC3_MUX=RX3 and the RX
clock off; mainline sets AUXPA bit4 (stock does not; harmless as far as tested). Live RDAC3_MUX switching and SoundWire debugfs
register writes leave the codec regmap cache stale: do not use them to judge a test. Test with Phosh Settings > Sound as the
control. Notes, scripts, stock ROM mixer/amp files and the r26 rollback image: ~/.claude-work/pmos-mojito/audio-speaker-2026-11-27/
(`r27/boot_b-r26.rollback.img`; old modules `/lib/modules/7.4.0-rc4-sm6150.old` on the phone). Stock amp profiles
(`/vendor/firmware/aw87xxx_pid_59_music_1.bin`, `..._5a_music_0.bin` after a 64-byte header) equal the DT tables byte for byte.
`qbootctl` is still not installed: reboot via fastboot and `set_active b`.

**Working on slot B (mainline 7.4-rc4, kernel package r26, build #27):** everything from the older list below plus
**Wi-Fi** (auto at boot, ~50 s), **Bluetooth** (WCN3950, after Wi-Fi), **Phosh** (stable again), **sensors** (accelerometer + light via
the ADSP sensor PD / libssc), **sound card + speaker** (WCD9375 over SoundWire, both AW87xxx amps, UCM, PulseAudio).
**Not working yet:** microphone (records exact zeros), headphones untested (nobody had any), earpiece-only / stereo split,
calls, PC-port (SDP) charging (AICL settles at 50 mA; the wall charger is fine), volume-up, haptics, suspend.

### Exactly what is on the phone right now
- `boot_b` = r26 Image + r26 DTB (msm-id 0x163, board-id 0x22 patched in) + the ramdisk/cmdline of the running image
  (unpacked with the scratch `bootv2.py`; repack with `mkbootimg.py` from `chroot_rootfs_xiaomi-mojito/usr/share/android-tools/mkbootimg/`,
  the native chroot's copy disappears after builds). Modules r26 in `/lib/modules/7.4.0-rc4-sm6150` (`.old` = r25).
- Runlevel default adds `mojito-wifi` (from `mainline/rootfs/etc/init.d/`). `/etc/modprobe.d/ath10k-mojito.conf` blacklists
  `ath10k_snoc` and `hci_uart` (the service loads them in order). No `hexagonrpcd-adsp-sensorspd` service, no audio blacklist.
- Packages added by hand: bootmac, hexagonrpcd, i2c-tools, libgpiod, bluez-btmgmt, wlr-randr, Phosh (postmarketos-ui-phosh), Alpine gmobile r0.
  **qbootctl NOT installed** (apk hit a DNS error); until it is, forced resets mark slot B unbootable -> `fastboot set_active b`.
- Files from `mainline/rootfs/` installed: profile.d/gmobile-mojito.sh (cutout via G_RESOURCE_OVERLAYS),
  /usr/share/gmobile-mojito/..., glib schema override (plain wallpaper; then `glib-compile-schemas`), UCM
  (`/usr/share/alsa/ucm2/conf.d/sm8250/Xiaomi Redmi Note 10.conf`, `/usr/share/alsa/ucm2/Xiaomi/mojito/HiFi.conf`).
  The accelerometer mount matrix (`rootfs/usr/lib/udev/rules.d/81-libssc-xiaomi-mojito.rules`) is parked at /root/ (not active):
  without it upright reads `bottom-up`; it was NOT the freeze cause, re-enable and re-test.
- User `user` was added to `audio`, `video`, `input` by hand (the install lacked `audio`: PulseAudio could not open the card).
- Rootfs is 101 GB (grown online, see the Wi-Fi section). Wi-Fi SSH also works: `user@<wlan0 IP>` (use it for big transfers: USB networking
  drops/freezes on large copies).

### Workflow that works
1. Edit the repo. DTS-only: `mainline/build-dtb.sh <linux-tree> out.dtb` + repack + flash (no build).
2. Kernel changes: bump pkgrel, update sha512sums, regenerate patch 0001 from the DTS (python snippet in git history), then
   **rsync `mainline/linux-postmarketos-qcom-sm6150/` to `~/.local/var/pmbootstrap/cache_git/pmaports/device/testing/linux-postmarketos-qcom-sm6150/`**
   (pmbootstrap builds from there, not from the repo!) and ask the user for `pmbootstrap build linux-postmarketos-qcom-sm6150`.
   Config changes = ~13 min, .c only = ~3 min. Check `packages/edge/aarch64/` for the new pkgrel.
3. `tools/install-modules.sh <unpacked apk> <phone ip>` (SSH_ASKPASS + PHONE_PW env), build boot.img, reboot to fastboot with the
   python `reboot(..., "bootloader")` script (`/tmp` is empty after reboots: copy it again), `fastboot flash boot_b`, `set_active b`, `reboot`.
   Always verify `uname -v` afterwards (a hung SSH once left the old kernel running with new modules).

### Audio: what works and how (details in "Audio status" below)
- Kernel: patch 0015 `pinctrl-sm6150-lpass-lpi` (= SM7150 LPI block, 2 mux fixes), wcd937x cansleep reset; patch 0016 `aw87xxx-seq`
  (amps from DT register tables, DAPM, `AUX Amp PA Switch` / `EAR Amp PA Switch`).
- DT: LPI @0x62b52000 (vote LPASS_HW_MACRO; un-vote 0x100f6 "Unknown cmd" is harmless), VA/TX/RX macros, SoundWire TX (SPI 137 + PDC 108)
  / RX (SPI 138) with **7-entry port tables**, WCD9375 (reset = LPI pin 6), amps on i2c3 (0x58 AUX, 0x5b EAR with reset gpio 83), card `X10`.
- **Speaker needs both amps AND the HPH-left stage settings** (the EAR path runs RX0 -> INT0 -> DEM MUX CLSH_DSM_OUT -> HPHL_OUT -> RDAC3 -> EAR).
  Without the HPH settings (`HPHL_COMP Switch 0`, `HPHL Volume`, ...) the amps only pop. All of it is in the UCM verb/device.
- UCM caps the hardware digital gain at 72/84 (-12 dB); the user asked for no loud test tones: keep tests at <= -30 dB and short.
- PulseAudio (not PipeWire) owns the hardware here (`wireplumber.conf.d/51-pulseaudio.conf`). **The greeter (greetd user) also runs a
  PulseAudio that can hold the card** -> the user session gets nothing. Killed by hand this session; needs a permanent fix
  (e.g. `autospawn = no` for the greetd user, or the pmOS way of handing the card over). Speaker profile is `HiFi (Mic, Speaker)`;
  UCM now gives Speaker priority 200 over Headphones 100 (jack availability reads "unknown").
- Last step done: profile set to Speaker at 30 % in PulseAudio; **the user had not confirmed a Phosh system sound yet.**

### Next steps, in order
1. Confirm speaker playback from Phosh at low volume; fix the greeter PulseAudio; install qbootctl.
2. **Mic:** capture = short transient then exact zeros with both TX timing tables (perf and stock superset). Route = identical to surya's UCM.
   Next: decode the stock `tx_swr_master qcom,swr-port-mapping` triplets (port, type, ch_mask) against mainline `qcom,tx-port-mapping`,
   check SoundWire TX port enable/channel masks in `/sys/kernel/debug/soundwire/master-3-0/` during capture, compare din/dout handling.
3. Which amp drives which speaker (0x5b + EAR = bottom so far; 0x58 + AUX alone was silent), stereo, earpiece for calls; headphones by ear.
4. A **mainline device package** (deviceinfo for the v2 boot image, depends on the miatoll-style set: soc-qcom, hexagonrpcd, bootmac,
   swclock-offset, qbootctl, rmtfs/tqftpserv/qrtr/ModemManager, the private `firmware-xiaomi-mojito-mainline`, user groups) + `mainline/rootfs/`.
5. Calls (q6voiced, surya's q6voice patches), charger SDP path (stock sets `0x1366=0x03` + ICL override toggle; ours `0x02`, AICL -> 50 mA),
   accelerometer mount matrix, MAC/2.4-only scan check, volume-up, haptics, suspend.

## *** 2026-11-27 (later): Wi-Fi WORKS on mainline; Phosh back (read this first) ***

Verified on the phone (slot B, r21 kernel, cold boot, nothing by hand): `wlan0` comes up, scans (2.4 GHz seen), associates and gets
an address via NetworkManager; LTE stays connected; Phosh 0.59 (greetd/phrog) runs.

- **Recipe:** start `hexagonrpcd -f /dev/fastrpc-adsp-secure -d adsp -s -R /usr/share/qcom/sm6150/Xiaomi/mojito` (root: the node is 0600),
  wait until its file traffic stops (~37 s after start on a clean boot), **then** load `ath10k_snoc` once. Done at boot by
  `mainline/rootfs/etc/init.d/mojito-wifi` (in runlevel default; `ath10k_snoc` stays blacklisted for udev autoload).
- **Timing matters:** QMI service 400 (sensor core) registers immediately, so it is NOT a readiness signal. Loading ath10k early gives 119
  again (three times in the first test), and the first success after those firmware restarts then failed with `failed to connect htt (-110)`
  (CE interrupts never fired, "polling.."). A fresh `rmmod`/`modprobe` then worked, and a clean boot with the wait works first time.
- The hexagonrpcd messages `Could not open .../sns_reg_version` and ~1600 `Tried to open .../temp.json for writing` are **normal**:
  hexagonrpcd 0.4.0 rejects every write (`AEE_EUNSUPPORTED`, `hexagonrpcd/apps_std.c`) and only maps `registry/registry`.
- MAC address is random each boot (`invalid MAC address; choosing random`): still to fix (stock reads it from persist/NV).
- **Rootfs was only 917 MB** (the first-boot resize did not run on the loop-in-userdata layout); grown online on the phone with
  `sfdisk --relocate gpt-bak-std /dev/loop0; echo ", +" | sfdisk -N 2 --no-reread --no-tell-kernel /dev/loop0; partx -u -n 2 /dev/loop0;
  resize2fs /dev/loop0p2` (now 101 GB). A clean install will need this fixed in the initramfs hook.
- **Not yet reproducible from a clean build:** there is no mainline device package; slot B is still assembled by hand (kernel package +
  `mk-bootimg-v2.sh` + packages/blobs/config copied over SSH, see "REINSTALLED" below).

**Wi-Fi + Bluetooth bring-up, final (2026-11-27, verified on a cold boot: wlan0 connected ~50 s, BT powered ~51 s, no 119):**
`mainline/rootfs/etc/init.d/mojito-wifi` + `modprobe.d/ath10k-mojito.conf` (blacklists `ath10k_snoc` AND `hci_uart`). Order matters:
1. hexagonrpcd as **root on `/dev/fastrpc-adsp-secure`**, started after the modem's WLFW service (QMI 69) is registered.
2. `ath10k_snoc` once the sensor PD's file traffic has started and settled; if 119 anyway, unload it (no endless crash loop).
3. `hci_uart` only after `wlan0` is up.
Lessons (each cost a freeze/boot):
- **An early `hci_uart` probe kills the chip for the whole boot.** At ~5 s the modem has not brought the WCN3950 up yet, BT times out
  (`command 0xfc00 tx timeout`), retries with power cycles, and afterwards Wi-Fi gets 119 and BT times out for the rest of the boot. This
  was also the old "chip is silent" BT A/B result. Wi-Fi and BT fail or work together: check BT when Wi-Fi gets 119.
- **`/dev/fastrpc-adsp` (`qcom,non-secure-domain`) does not work for this:** same sensor-PD file traffic, but 119 every time. The stock
  `hexagonrpcd-adsp-sensorspd` service (user fastrpc) cannot open the 0600 secure node, so it is not used. The DT change was reverted.
- A `modprobe ath10k_snoc` that never returns holds the module lock: `lsmod`, udev and reads of `/proc/<pid>` hang, the phone slowly locks up.
- The freezes on the Phosh boots happened even with Wi-Fi not loaded yet (last line: session start at ~31 s, USB link drops); without
  greetd the same bring-up never froze. Suspects: gmobile r1 (local cutout build, installed just before the freezes started) and
  plymouth staying attached. **Resolved: it was gmobile 0.7.5-r1** (the local build with the mojito panel compiled in): with Alpine's
  stock r0 the same Phosh boot (plymouth still running) is stable, Wi-Fi/BT/LTE up. The cutout data now comes from
  `rootfs/usr/share/gmobile-mojito/display-panels/xiaomi,mojito.json` via `G_RESOURCE_OVERLAYS` (`rootfs/etc/profile.d/gmobile-mojito.sh`);
  do not install the r1 build. greetd is enabled again.
- **The real cause of the Phosh freezes: the default GNOME wallpaper** (`/usr/share/backgrounds/gnome/curvaturingster-{l,d}.jxl`).
  At every login `glycin-jxl` (JPEG XL decoder) grows to ~2.1 GB within 3 s, MemAvailable falls to ~400 MB, then one CPU hard-locks
  (RCU stall, no NMI response) and the phone freezes. Captured with a per-second /proc/*/status VmRSS logger. The gmobile r1 and
  mount-matrix "causes" were coincidence. Fix: `rootfs/usr/share/glib-2.0/schemas/99-mojito-wallpaper.gschema.override` (plain color;
  run `glib-compile-schemas`). A phone-sized JPEG would also work; do not use the JXL. gmobile r1 is therefore probably fine too.
- Rotation: upright reported `bottom-up` without a mount matrix; `rootfs/usr/lib/udev/rules.d/81-libssc-xiaomi-mojito.rules`
  (Y,Z inverted) was written and tested once, then parked as `/root/81-libssc-xiaomi-mojito.rules.off` on the phone during the freeze
  hunt. It was not the cause: re-test and re-enable.
- **Audio bring-up written, NOT tested yet (2026-11-27), in r25:** patch 0015 adds `pinctrl-sm6150-lpass-lpi` (the SM7150 LPI block:
  0x62b52000 = stock gpio18-31; table with the gpio19 swr_tx_data=func3 and gpio23 swr_rx_data=func2 fixes from the surya/Mi 9T ports,
  confirmed by the stock DT) and the wcd937x `gpiod_set_value_cansleep` reset fix. DTS: `vreg_bob`, `lpass_tlmm` (vote LPASS_HW_MACRO),
  VA/TX/RX macros (no dcodec vote), SoundWire TX (SPI 137 + wake PDC 108) / RX (SPI 138), v1.5.1, surya port tables, TX map <2 2 3 4>,
  WCD9375 (reset = LPI pin 6 as gpio, L15a/L10a/BOB, micbias 2.7 V per stock), sm8250 card: headphones + mics. Violet's failures
  (UNATTACHED, MASTER_CLASH_DET) match the missing LPI mux, the wrong reset pin (it used TLMM 24) and the LPI mux bugs.
  Speaker/earpiece still need the AW87xxx amps (i2c3 0x58 / 0x5b, no mainline driver; stock init sequences are in the private dump).
  First boot: blacklist `pinctrl_sm6150_lpass_lpi` and load it by hand (the LPI/LPASS block can hang the SoC without its vote).
- **Audio status 2026-11-27 (r25 + DT fixes on the phone):** LPI loads (vote 0x100f4 OK; un-vote 0x100f6 "Unknown cmd", harmless),
  both SoundWire buses enumerate the WCD9375, card `X10` registers once the port tables have **7 entries** (controllers: TX 6 in + 1 out,
  RX 1 in + 6 out; 5-entry tables -> RX "SWR bus clsh" + TX "Initialization not complete" -110). Headphone stream runs (no jack test yet).
  **Speaker plays** with BOTH amps on, as Android does: EAR (RX0 -> INT0 -> RDAC3 -> EAR) + amp 0x5b (reset = TLMM gpio 83,
  `gpioset -c gpiochip2 83=1`) and AUX (RX1 -> INT2 -> AUX) + amp 0x58; 0x58 alone was silent. Sound came from the bottom.
  r26: patch 0016 `aw87xxx-seq` (DT register tables, DAPM on/off, "<prefix> PA Switch"), amps as card `aux-devs`.
  Mic: capture gave a transient then exact zeros with the SM7150 "perf" TX timing; r26 DT uses stock `tx_frame_params_superset`
  (si 3, lane 0; `techpack/audio/soc/swrm_port_config.h` in the downstream tree). RX timing already equals stock `rx_frame_params`.
- **"battery over-voltage" dmesg flood** (charger, patch 0008): not an interrupt (bat-ov IRQ count 0) but the health getter printing
  each time UPower polls, while BATTERY_CHARGER_STATUS_2 has BAT_OV set. That happens when the battery sits above our 4.45 V float,
  e.g. after Android charged it to its 4.47 V (`qcom,fv-max-uv`). The cell rating is 4.45 V (`qcom,max-voltage-uv`, both cell
  vendors), so the float stays 4.45 V; the getter now reports POWER_SUPPLY_HEALTH_OVERVOLTAGE silently (in r25, unbuilt).
- Repeated forced resets mark slot B unbootable (`fastboot getvar slot-unbootable:b` = yes, retry 0): `fastboot set_active b`.
  Permanent fix: install `qbootctl` + `qbootctl-openrc` (marks the boot successful; the install hit DNS errors, not done yet).
- **Sensors now work as a side effect:** with the sensor PD served, iio-sensor-proxy (libssc) reports an accelerometer and ambient
  light; Phosh auto-rotates. Orientation test (upright/upside-down/left/right) matched without a mount matrix.
- busybox `grep` has no `--line-buffered`; a `dmesg -w | grep ...` capture silently records nothing. Stream raw `dmesg -w` instead.

**Bluetooth WORKS too (2026-11-27):** the chip is a **WCN3950**, so the node must be `qcom,wcn3950-bt` (7.4 has it; loads
`qca/cmbtfw12.tlv` + `qca/cmnv12.bin`), on UART7 with the PMU supplies and `swctrl-gpios = <&tlmm 102>`. Log: `QCA SOC Version 0x40070120`,
`QCA setup on UART is completed`. It then stays an *unconfigured controller* (no BD address) until **`bootmac`** is installed (sets
BT and Wi-Fi addresses, also fixes the random Wi-Fi MAC). Scan finds devices. Now in the repo DTS together with Wi-Fi `okay` and
**L10a no longer always-on** (the working test DTB) - kernel package **pkgrel=25, NOT BUILT YET** (patch 0001 regenerated).
- `mojito-wifi` bug fixed: the hexagonrpcd log is empty for the first seconds, which the first version took as "quiet" and loaded
  ath10k at 12 s (119 x5, then HTT -110). It now waits for >= 100 lines first. `rmmod ath10k_snoc; modprobe ath10k_snoc` recovers.
- **USB networking freezes** the phone on large transfers (~140 MB tar earlier; the user knows it as a recurring bug). Keep
  transfers small/one at a time; recovery: Power + Vol-down to fastboot.
- The `qcom-pm8150b-charger ... battery over-voltage` message floods dmesg (several per second) and pushes other messages out of
  the ring buffer: check logs right after an event, or fix the message.
- Firmware for a clean build: private repo `258ryan/mojito-firmware` (package `firmware-xiaomi-mojito-mainline`, provides/replaces
  `firmware-xiaomi-mojito`; vendor files, ath10k board, BT tlv/nv, hexagonrpcd sensor tree). EFS images are NOT in it (IMEI).

## 2026-11-27: Wi-Fi cause found on stock (the analysis that led to the fix above)

Controlled tests on stock MIUI (same phone, recorder kernel, one change per boot) showed the WLAN capability request depends on the **ADSP sensor PD file server**:

| ADSP | `adsprpcd` instances | capability reply |
|---|---|---|
| not running | - | **error 119** after ~200 ms (twice) |
| running | all three | success, ~44 ms |
| running | none | **119** (twice) |
| running | `audiopd` only | **119** |
| running | **`sensorspd` only** | **success** |
| running | default (no argument) only | **119** |

- Not required: `cnss-daemon` and 20 other modem-facing Android programs (all blocked together: still success). Not the cause: the ADSP firmware
  build (the pmOS package's `ADSP.VT.5.3-00316` also succeeds on stock; the phone ships `-00323`). The kernel version was already ruled out.
- **Plan on pmOS:** run `hexagonrpcd -f /dev/fastrpc-adsp -d adsp -s -R <dir>` (Alpine `community`, 0.4.0), like postmarketOS's miatoll port
  (`hexagonrpcd-adsp-sensorspd`), with this phone's sensor files, then load `ath10k_snoc`.
  Layout of `<dir>` (here `/usr/share/qcom/sm6150/Xiaomi/mojito`): `sensors/config` = `/vendor/etc/sensors/config`,
  `sensors/registry` = `/mnt/vendor/persist/sensors/registry/registry`, `sensors/sns_reg.conf` = `/vendor/etc/sensors/sns_reg_config`,
  `dsp/adsp` = `/vendor/dsp/adsp` + `/vendor/lib/rfsa/adsp`, `socinfo/` files: soc_id 355, revision 1.1, hw_platform IDP,
  platform_subtype Unknown, platform_subtype_id 0, platform_version 65536. These are vendor/device files: **not in this repo**.
- 7.4 creates only `/dev/fastrpc-adsp-secure` here (the DT node lacks `qcom,non-secure-domain`): pass that device to `-f`, or add the
  property as sm7125-mainline does for sc7180.
- Recording method, tools and the recorder kernel recipe: `mainline/wip/wlan-re/stock-capture/`.

**Phone state:** stock was recorded, then pmOS was restored from the PC backup (slot A downstream, slot B = 7.4 with the Wi-Fi-enabled test DTB
without L10a always-on). The backup restore needs `depmod 7.4.0-rc4-sm6150` and `rc-update -u`; after the first boot modules loaded only after
`udevadm trigger --action=add` (recheck). `hexagonrpcd` and the sensor files are installed; **the Wi-Fi test has not run yet**.

## START HERE (2026-11-26, end of session): where things stand

> **2026-11-27, read first:** a second Wi-Fi session ("Wi-Fi: second session" below) exhausted the mainline ideas. The user then chose to restore
> stock Android. Before that wipe the pmOS files and boot partitions were backed up on the PC (not in this repo).

**Working on slot B (mainline 7.4-rc4):** boot, UFS, USB networking/SSH, display + DCS brightness, touch, Adreno 612, Phosh on boot with
the correct corner/cutout layout (gmobile panel data, `mainline/gmobile/`), **battery gauge** (`qcom_qg_lite`, patch 0010), **charging**
(SMB5, patch 0008; wall ~1 A, PC port 500 mA, correct Charging/Full status), **ADSP**, **modem**: LTE data (~22 Mbit/s, IPv4+IPv6), SMS
send, data on/off toggle, **APR audio services** (q6core/afe/asm/adm bound; no sound card yet).
**Not working:** **Wi-Fi** (see next paragraph), speaker/mic/earpiece (needs the LPASS LPI pin driver, see "Audio"), calls (need audio),
Bluetooth, volume-up key, haptics, sensors, suspend, Vulkan. **Slot A** (downstream 4.14) is untouched; keep it working.

**Wi-Fi in one paragraph (details: section "Wi-Fi", it holds every test and result):** the modem's WLAN service (WLFW, QMI service 69) answers
every request ind_register, host cap, msa info, msa ready, BDF download and cal report. Only the capability request fails: after a repeatable
~200 ms the firmware returns the constant error 119 (the handler sets `r2 = #0x77` whenever its platform init `FUN_b01c15b0` returns non-zero),
and `wlan_process` is killed ~9.4 s later. That init is the first power-up of the WCSS "Helium" block; from the firmware's own strings it enables
the RF crystal over the WSI bus and waits for the RF chip, i.e. a hardware/clock condition we cannot see. **Everything on the Linux side that we
can vary was tested on hardware and still gives 119:** rails and their order, GPIO 98 `cnss-wlan-en` (stock pin state, pull-up 16 mA, now in the
DTS bound to remoteproc_mpss), the upstream WCN3990 PMU/pwrseq node, always-on rails at violet's voltages, MSA size and permissions (with and without
`qcom,msa-fixed-perm`; the DTS now has none, like stock icnss and violet), host-capability message contents (live tunable `mainline/wip/0018`),
`VBATT_REQ`, waiting for `MSA_READY_IND`, board data before the capability retry, an older firmware build (`HL.3.2.2-00715`), writable file-based
rmtfs like violet. The violet port (Redmi Note 7 Pro, same SoC, Wi-Fi works) has the same device tree and services as far as read. **Open question:
what the ~200 ms wait inside the modem's first power-up is** (newest lead, unproven: the RF crystal enable over WSI fails; see "CORRECTION and new
lead" in the Wi-Fi section). The modem's memory and log are NOT readable (below), so the remaining ideas are:
(1) compare against a phone state where Wi-Fi works: boot stock Android with root and dump GPIO/regulator/clock/pinctrl state, diff against ours
(**back up `userdata` first: our rootfs is a loop file inside it**); (2) a full violet-parity image (direct supplies, no ch1, always-on LPM rails, no
PMU) - parts of it were tested separately; (3) keep reading the firmware (recipe in the Wi-Fi section) for the wait.

**Exactly what is on the phone right now:**
- `boot_b` = the r21 kernel + the DTB built from this repo's DTS at the end of the session (Wi-Fi node disabled, PMU node, GPIO 98 pinctrl,
  L10a always on, APR audio). `ath10k_snoc` stays blacklisted (`/etc/modprobe.d/ath10k.conf`); load it by hand to test Wi-Fi.
- Changed by hand on the rootfs: `/etc/conf.d/rmtfs` is violet-style (`rmtfs_files_path=/var/lib/rmtfs`, `rmtfs_avoid_writing=false`; the original is
  `rmtfs.pmos-default`); `/var/lib/rmtfs/modem_fs1|fs2|fsg|fsc` are copies of the EFS backup images in `~/.claude-work/pmos-mojito/efs-backup-2026-11-26/` (the
  modem writes to these files, the partitions are untouched). `/usr/lib/firmware/postmarketos/wlanmdsp.mbn.orig` is a copy of the original firmware (same as `wlanmdsp.mbn`).
- Modules: r21. Packages added by hand: rmtfs, tqftpserv, qrtr, ModemManager (enabled at boot), qmi-utils, gmobile/gmobile-udev 0.7.5-r1
  (local build). NetworkManager connection `mobile` (carrier APN) autoconnects. `/lib/firmware/ath10k/WCN3990/hw1.0/{firmware-5.bin,
  board.bin}` (firmware-5 from linux-firmware-ath10k, board.bin = stock bdwlan.bin).
- The clock is only right after NTP over LTE (`ntpd -q -n -p pool.ntp.org`); no time sync at boot yet.

**REINSTALLED 2026-11-27 (after the stock-MIUI reference session):** fresh `pmbootstrap install` (console UI, password unchanged). Slot A = downstream from that install
(boot/vendor_boot/dtbo via `pmbootstrap flasher`), slot B = r21 kernel + repo DTS DTB + the new install's vendor_ramdisk (`mk-bootimg-v2.sh`, new UUIDs
boot 03430a6c-..., root e11d21b7-...), `dtbo_b` erased, vbmeta_a/_b = stock vbmeta flashed with `--disable-verity --disable-verification` (the device package has no
vbmeta partition for `flasher flash_vbmeta`). On the rootfs: r21 modules, modem userspace (offline from cached apks; ModemManager shows "failed" at boot but is
started by D-Bus activation and LTE autoconnects), the 53 stock firmware files the package lacks in /lib/firmware/postmarketos (incl. **ipa_fws**: without it IPA
fails with -2 and there is no rmnet_ipa0), restored rmtfs config/EFS files, NM `mobile`, msm.conf, blacklists for ath10k_snoc and hci_uart, and the Android files
`/lib/firmware/ath10k/WCN3990/hw1.0/android/{bdf_gl.bin,regdb.bin}` + `/lib/firmware/qca/cmbtfw12.tlv, cmnv12.bin`. Phosh/gmobile are NOT reinstalled.
**Lesson:** never `tar -C / -x` an archive made with `tar -C dir .` - its `./`, `./etc` ... entries re-own `/` and `/etc` to the PC uid and sudo then refuses
(`/etc must be owned by root`); there is no doas/root password, so only a rootfs reflash fixes it. Pack file lists only (`find . -type f`) and extract with `-o`.

**Package state:** `mainline/linux-postmarketos-qcom-sm6150` is at **pkgrel=24, NOT BUILT YET** (patch 0001 was regenerated from the DTS and its checksum
updated; includes patch 0014, the SMMU fix audio streams need). Build it: `pmbootstrap build linux-postmarketos-qcom-sm6150` (~3 min with ccache; config/header
changes ~13 min), then `tools/install-modules.sh`, `mk-bootimg-v2.sh`, flash `boot_b` (and `fastboot set_active b` afterwards). gmobile: `pmbootstrap build --arch aarch64 gmobile`.
DTS-only changes: `mainline/build-dtb.sh` (no package build).

**Next steps, in order:**
1. **Audio:** port `sm7150-mainline/linux` (tag v7.1_rc3) `drivers/pinctrl/qcom/pinctrl-sm7150-lpass-lpi.c` to SM6150 (LPI block at
   **0x62b52000**; 0x62b40000 is the SSC block that hangs the SoC), then macros + SoundWire + WCD937x + sound card from their
   `sm7150.dtsi` / `sm7150-xiaomi-*.dts`. Speaker = WCD937x AUX_OUT -> aw87xxx analog PA (i2c3 0x58/0x5b, chip id 0x59, not aw87390).
2. **Wi-Fi:** the 2026-11-27 Bluetooth A/B test (section "Wi-Fi") shows the WCN3990 chip itself does not respond (BT on UART7 also fails, rails/clocks verified in the PMIC).
   Next: run the BT power-on on slot A (downstream) and diff the hardware state; see the bullet "BLUETOOTH A/B TEST".
3. Volume-up key (pm6150l GPIO 2 in the sm7125 Xiaomi tree), PMIC haptics, Bluetooth (WCN3990 on UART; sm7125/sm7150 trees have the
   node), sensors (ADSP sensor core, QMI 400; no mainline driver), time sync at boot, suspend, KWin/Finder.

**Rules and hazards learned the hard way** (details below):
- The user runs `pmbootstrap build`; the agent flashes and diagnoses. Ask for the SSH password each session; never store it. Commit with the
  GitHub no-reply identity (see `git log`; the repo has no user.email set, use `git -c user.name=... -c user.email=...`); keep device identifiers,
  carrier/APN and phone numbers out of the repo.
- **Stage risky drivers:** blacklist the module in `/etc/modprobe.d/` before flashing, load by hand over SSH, un-blacklist once it works.
- **Do not restart the modem** (`rc-service rmtfs restart`, or `echo stop/start > remoteproc1/state`) **while IPA is set up**: the modem dies 40 s later
  (`DOG detects stalled initialization`), recovery never completes, IPA times out; reboot.
- **Never read the modem carve-out (0x8b000000, 0x8400000 bytes) via /dev/mem**: the read hangs the CPU (RCU stall); violet reports SoC resets. A memory capture
  before the secure-world shutdown is therefore not possible; the coredump after shutdown (`coredump=enabled`, debugfs `crash`) is all zeros.
- **Never `dd` the `modemst*`/`fsg`/`fsc` partitions on the phone**: the read hangs in the kernel (D state, unkillable) and then `sync` hangs too. Use the EFS backup
  images on the PC. Recover a stuck phone with `echo 1 > /proc/sys/kernel/sysrq; echo b > /proc/sysrq-trigger` over ssh.
- **Boot slot counter:** repeated forced resets without a clean boot make ABL mark slot B unbootable (phone stops in fastboot). `fastboot set_active b` resets it; do it after every flash.
- `pkill -f <pattern>` kills your own shell when the pattern is in its command line; use `[p]attern` or kill by pid.
- Test loop that is fast: poll ssh and a QRTR lookup of service 69 instead of fixed sleeps (reboot to Wi-Fi result ~40 s), and use writable module parameters between
  WLAN-process restarts (every ~10 s while ath10k_snoc is loaded and failing). The modem reads `wlanmdsp.mbn` only at modem boot.
- PMIC state survives a warm reboot (a latched charger suspend needs a replug). Regmap debugfs reads only the requested window:
  `dd if=/sys/kernel/debug/regmap/0-00/registers bs=9 skip=$((0xADDR)) count=N`.
- Hangs/crashes: TLMM pins 0-3/6-9; an `mdss` `resets` line; `rmmod msm`; LPASS 0x62b40000 (SSC) without power; the modem carve-out. No log survives a reset.
- Builds: ccache makes `.c`-only changes ~3 min. Object-only test compiles miss modpost errors (`MODULE_IMPORT_NS("IIO_CONSUMER")`).
- `/tmp` on the phone is empty after reboot; run `rc-update -u` after adding services (1970 clock). apk caches repo indexes by URL: serve a
  new local repo on a new port. Reboot to fastboot from SSH: copy a small python script with the `reboot(..., "bootloader")` syscall.

## Goal

Run the user's **Finder** shell on this phone. Finder is a Qt 6.9+ QML shell on **KWin 6 (Wayland)** with
LayerShellQt and QtQuick.Effects (it lives in the user's private `finderlinux` repo). It needs GPU
acceleration with GBM + EGL, which this phone can only get from a **mainline kernel** (freedreno). That is
why there are two ports here:

- `downstream/`: Xiaomi's 4.14 kernel. **Works today** (boots, SSH, text console on screen). Stays on slot A.
- `mainline/`: Linux 7.4-rc4 + an SM6150 device tree. Boots to SSH and, as of 2026-11-27, runs **Phosh on the real
  display (DPU/DSI/panel, brightness), touch, the Adreno GPU and a Phosh autostart**. Developed on slot B.

## The device

- Retail name Redmi Note 10, codename on this unit **`sunny`** (M2101K7AG, no NFC); same board as `mojito`.
- SoC SM6150 (mainline calls it **Talos**, also QCS615), Adreno 612, 4 GB RAM, 128 GB UFS (4096-byte sectors).
- Bootloader unlocked. A/B slots. Boot header **v3** (kernel in `boot`, initramfs + DTB in `vendor_boot`).
- Panel `k7 38 0c 0a` 1080x2400 video mode; FocalTech touch (`fts_ts`); PMICs PM6150 + PM6150L.
- Stock firmware: MIUI 14 global `V14.0.9.0.SKGMIXM` (Android 12). The user keeps the verified fastboot ROM
  locally for recovery; it is not in this repo (vendor blobs are not redistributable).

## Working with the phone

- SSH: `ssh user@172.16.42.1` over the USB cable (NCM). The login password is the one set at
  `pmbootstrap install --password ...`; **ask the user**, it is deliberately not written here.
  `user` has sudo (sudo-rs reads the password with `-S`).
- Boot takes ~4-5 minutes on downstream before SSH answers (slow services). Ping answers much earlier.
- **Reboot into fastboot without buttons** (busybox `reboot` takes no argument):
  `python3 -c "import ctypes; l=ctypes.CDLL(None); l.sync(); l.syscall(142,0xfee1dead,672274793,0xA1B2C3D4,b'bootloader')"`
- Slot switching: `fastboot set_active a|b` then `fastboot reboot`. **Slot A = working downstream. Keep it working.**
- No `scp`/`sftp` server on the phone. Copy files by serving them from the PC over USB
  (`python3 -m http.server --bind 172.16.42.2`) and `wget` on the phone. Never pass large data on the
  SSH command line (argument too long, and `pkill -f <name>` will kill your own SSH command if it contains `<name>`).
- **Do NOT route internet through the PC to the phone (NAT over USB).** Large forwarded downloads crash and
  reboot the downstream kernel within seconds, reproducibly. Local USB traffic is fine (200 MB at 37 MB/s),
  disk I/O is fine. Download packages on the PC and serve them over USB.
- Text input on the phone's own screen: `tools/vtype.py` creates a temporary uinput keyboard and types.
  `tools/evrec.py` records touch/button events. `tools/hwprobe.sh` is a read-only hardware survey.

## Working on the PC

- pmbootstrap 3.12.1 from git (`pipx install git+https://gitlab.postmarketos.org/postmarketOS/pmbootstrap.git`;
  PyPI has none). Work dir `~/.local/var/pmbootstrap`, config: device `xiaomi-mojito`, UI console,
  **service manager openrc** (systemd does not run on the 4.14 kernel).
- pmbootstrap needs sudo. The user's `sudo -v` does not carry into the agent's shell. Ask the user how they
  want to provide it; do not store their password anywhere persistent, delete any temp helper afterwards.
- Packages are copied into `$(pmbootstrap config aports)/device/testing/` to build.

## Downstream port: what was needed (all in `downstream/`)

1. Kernel built with clang; `gcc6` in makedepends only to pull in aarch64 binutils; `REPLACE_GCCH=0`.
2. Header v3: pmOS builds `vendor_boot` (initramfs + DTB). DTB = all kernel-built `qcom/*.dtb` concatenated;
   `dtbo.img` built from the kernel's overlays (Xiaomi's board changes live in `sm6150-idp*.dts`).
3. `deviceinfo_initfs_compression="gzip"` (4.14 cannot unpack zstd initramfs).
4. Initramfs hook `10-loop-4k-partscan.sh`: kernels < 5.8 lack `LOOP_CONFIGURE`, so with 4K UFS sectors the
   pmOS subpartitions inside `userdata` never appear; the hook rescans after setting the block size.
5. OpenRC `cgroups` service hangs on this kernel: removed from the default runlevel
   (`rc-update del cgroups default`, redo after any fresh `pmbootstrap install`).
6. Kernel cmdline `service_locator.enable=0` (no Android PD mapper; lets the audio notifier use SSR).
7. Root fs is a loop inside the 112 GB `userdata`; it was grown live with `sfdisk --relocate gpt-bak-std`,
   `sfdisk -N 2`, `partx -u`, `resize2fs` (the pmOS auto-resize is skipped because the hook bypasses it).
8. Screen: no `/dev/fb0` (msm_drm fbdev init fails: "failed to get buffer obj iova: -22") and the SDE driver
   rejects atomic commits. Fix: **kmscon** with `LD_PRELOAD=libnoatomic.so` (`downstream/shim/noatomic.c`) so it
   uses legacy KMS. OpenRC service `kmscon-console` on tty1; tty1 getty is commented out in `/etc/inittab`.
9. Firmware: extracted from the stock ROM (`NON-HLOS.bin`, `BTFM.bin`, `dspso.bin`, `vendor_a/firmware` from
   `super.img` via `tools/lpunpack.py`) into `/lib/firmware/postmarketos/` **on the phone only**.
   OpenRC service `msm-dsp-boot` boots the ADSP at startup (`/sys/kernel/boot_adsp/boot`).

### Downstream hardware status

Works: display + backlight, touch, power/volume keys, vibrator (needs pulses > ~0.5 s), flashlight, battery
and charging readouts, thermal, USB gadget, ADSP boots. No notification LED on this model.
Not working: audio (sound card not registering; `q6core_audio` bound on one boot at ~300 s and not on the
next; Bluetooth DAI links removed via DT property `qcom,wcn-btfm`), modem, CDSP (untested), Wi-Fi, Bluetooth,
GPS, sensors, GPU (KGSL only; no Mesa path), cameras (Android HAL only). `haveged` crashes (harmless).

The phone also has these changes made directly on its rootfs (not in the packages): `kmscon-console` and
`msm-dsp-boot` services, `/usr/local/lib/libnoatomic.so`, the firmware, `cgroups` removed, the inittab edit,
`vendor_boot` repacked with the cmdline/DTB changes above. Fold them into packages before reinstalling.

## Mainline port: where it stands (`mainline/`)

Mainline 7.4-rc4 already has the SoC (`talos.dtsi`), PMIC dtsi files, the **Adreno 612 + RGMU** in
`a6xx_catalog.c`, and the SM6150 DPU catalog. `mainline/sm6150-xiaomi-mojito.dts` adds the board:
regulators (PM6150 = pmic-id `a`, PM6150L = `c`, ranges from the stock DT), UFS/USB supplies, buttons,
simple-framebuffer on the bootloader splash at `0x9c000000`, Xiaomi carveouts (including XBL/AOP
`0x85e00000`, ADSP 34 MB, IPA at `0x97b00000`, GPU zap at `0x97b15000`) and ramoops at `0x9d800000` with the
same layout as the stock kernel. The kernel package is `mainline/linux-postmarketos-qcom-sm6150`
(config started from pmaports' sm7150 config, plus the SM6150 symbols `PINCTRL_QCS615`, `QCS_GCC_615`, ...).

### Status (2026-11-26): mainline boots to SSH; pin controller (115 GPIOs), splash login and the Adreno GPU work

Linux `7.4.0-rc4-sm6150` boots from a header v2 `boot.img` (see "Packaging the v2 boot image"; `dtbo_b` erased) to
the pmOS rootfs on slot B and answers on SSH over USB. UFS, the USB gadget, the watchdog, the TLMM pin controller
all probe; the **real display stack works** (DPU + 14 nm DSI + our panel driver, with DCS brightness), the
**Adreno 612 renders** (freedreno, OpenGL ES 3.2), **touch works** and Phosh runs. Open: Phosh/KWin on the msm KMS
device (not yet tried on it), audio, Wi-Fi, modem, charging. Eight GPIOs are secure-world owned and reserved in the
DTS (see TLMM).

Results of the v2 boots, in the order they were tried (details in the sections below):

| Image | Result |
|---|---|
| r0 kernel (no patches), default DTB | freezes at ~3 s in the `qcs615-tlmm` probe, RCU stalls name CPU 6 |
| r1 kernel (patches 0002/0003 added), `gpio-reserved-ranges = <0 4>` (violet's value) | same freeze |
| r1, `<0 2>, <123 1>` (the only pins that wedge, plus UFS_RESET) | same freeze, also with `maxcpus=1` (then it resets) |
| r1, same plus `interconnects` on the TLMM node (probe waits for the config NoC) | prints the boot text, goes black, SoC resets in seconds |
| r1, `<0 124>` (all GPIOs reserved), with or without the NoC links | boots to SSH, but no pin is usable |
| r2/r3 with TLMM as a module (`=m`), `<0 2>, <123 1>`, loaded at 11 s and at 180 s | the same abort at `gpio2`, so it is not timing; the load takes the system down |
| r3, **`<0 4>, <6 4>, <123 1>`**, module loaded from SSH | **registers `gpiochip2` (124 GPIOs), 115 pins read back, no abort, system stable** (this is the DTS in the repo) |

### TLMM: eight secure-world GPIOs, found and fixed

**Root cause.** Eight GPIOs belong to the secure world and cannot be read by Linux: **gpio0-3** (WEST tile) and
**gpio6-9** (EAST tile), probably the first two QUP serial engines (a fingerprint sensor or secure element). Reading
gpio0 or gpio1 **hangs** the CPU; reading gpio2, 3 or 6-9 raises a **synchronous external abort** (`ESR 0x96000010`,
EC 0x25, DFSC 0x10). When the pin controller registers its gpio chip, gpiolib reads the control register of every
valid line (`msm_gpio_get_direction` from `gpiochip_add_data_with_key`), so one valid protected pin kills the probe.
The fix is `gpio-reserved-ranges = <0 4>, <6 4>, <123 1>` in the DTS (123 is `UFS_RESET`, not scanned, kept reserved).
After it the kernel registers `gpiochip2` (124 GPIOs) and `/sys/kernel/debug/gpio` dumps all 115 valid pins with real
states, with no abort. The Note 7 Pro port reserves only `<0 4>`; here gpio6 then aborts.

**Why every earlier run failed the same way.** The kernel reads valid pins in order and dies at the first protected
one: `<0 4>` -> gpio6, `<0 2>, <123 1>` -> gpio2, a single valid pin gpio2 -> gpio2, all reserved -> nothing is read.
The dying kworker holds the deferred-probe lock, so the visible symptom was a frozen boot with RCU stalls naming
one CPU (the one running the probe), never the oops, which scrolled off or was not drawn.

**How it was found** (the exact tooling matters, see the mistake below):
- A boot-time kprobe trace printed the call sequence to the console: `kprobe_event="p:a,msm_pinctrl_probe;..."` plus
  `tp_printk` (events are created at `fs_initcall` and enabled automatically, before the TLMM probe). The last line,
  `g: msm_gpio_get_direction o=2`, followed by `Internal error: synchronous external abort`, named the pin. The whole
  command line must fit in 512 bytes (Android boot header v2) or it is cut.
- A diagnostic module parameter (`diag=1`, in a debug-only patch, since removed) read gpio2 four ways (non-posted
  mapping, 8/16/32-bit, and the whole-tile mapping). The very first one aborted, so neither mapping type nor access
  width nor privilege is the issue (a userspace read through `/dev/mem` aborts too: `SIGBUS`).
- The per-pin `/dev/mem` scan: one child process per pin, pinned to a spare CPU; the child writes `OK pin ctl io
  intr_cfg intr_status` after the read. **A pin with a `TRY` line and no `OK` line is a pin that did not complete.**
  Result: 122 tried, 115 OK, gpio0/1 hung, gpio2/3/6/7/8/9 aborted.

**A mistake to avoid.** The first version of the scan counted a pin as fine when the child *finished*, but a child
killed by `SIGBUS` also finishes, so it reported "only gpio0 and gpio1 are protected" and "everything reads fine
later". That produced a long, wrong detour (idle states, probe timing, NoC and cpufreq dependencies, a TLMM module
loaded at 11 s and 180 s) before the log's `OK` lines gave the real list. Always check the child's wait status.

**Practical rules.**
- Reserved pins cannot be muxed (`msm_pinmux_request` refuses them), and these eight are secure-world owned anyway.
  Do not add pinctrl states or gpio consumers for gpio0-3 / gpio6-9 (e.g. a fingerprint reset line on those pins).
- Register addresses: pin `n` is at tile base + `0x1000 * n` with EAST `0x3100000`, WEST `0x3500000`, SOUTH
  `0x3d00000` (same as the downstream driver's `0x3000000 + {0x100000, 0x500000, 0xd00000}`).
- A kernel oops in a probe running in `deferred_probe_work_func` leaves the system stuck rather than rebooting.

### GPU: the Adreno 612 renders (freedreno, render node)

`tools/gltest.py` (copy it to the phone and run it as a normal user) opens `/dev/dri/renderD128` through GBM, makes a
surfaceless OpenGL ES context and draws a shader triangle into an FBO, then reads pixels back. Result: `GL_RENDERER
FD612`, `OpenGL ES 3.2 Mesa 26.3.1`, clear and triangle tests PASS, no kernel error. What it took:

1. **DTS:** `&gpu { status = "okay"; }` and `&gpu_zap_shader { firmware-name = "postmarketos/a612_zap.mdt"; }`. The
   `gmu` node needs nothing: for the 612 the GMU is the "GMU wrapper" (`a6xx_gmuwrapper_funcs`), handled inside the
   GPU driver, so `506d000.gmu` staying unbound is normal. `mdss`/`dsi` stay disabled (the display is simpledrm).
2. **Firmware** (all already on the phone from the downstream install, in `/lib/firmware/postmarketos/`): `a612_zap.mdt`
   plus `.b00-.b02` (signed for this phone by the vendor, cannot come from linux-firmware), `a612_rgmu.bin`,
   `a630_sqe.fw`. The driver looks in `qcom/`, so: `mkdir /lib/firmware/qcom` and symlink the last two into it
   (`ln -s ../postmarketos/a630_sqe.fw /lib/firmware/qcom/`). The zap path is the full DT `firmware-name` above.
3. **Modules:** `DRM_MSM=m`, so the r4 package's module tree must be on the rootfs: unpack
   `usr/lib/modules/7.4.0-rc4-sm6150` from the apk into `/lib/modules/` and run `depmod -a 7.4.0-rc4-sm6150` (17 MB,
   852 modules; the phone's kmod reads the `.ko.zst` files).
4. **`/etc/modprobe.d/msm.conf`: `options msm separate_gpu_kms=1`.** With one GPU and no display subsystem the driver's
   default (`-1`, auto) picks "single card" and the GPU waits forever for a display master, with no log line at all.
   You get a bound `adreno` driver, no `renderD128`, nothing deferred.

**Traps hit while bringing it up.**
- udev **auto-loads `msm` at boot** as soon as the modules are installed (the GPU node's modalias), before any
  `modprobe msm separate_gpu_kms=1` you type; `modprobe` of an already-loaded module is a silent no-op that returns 0.
  Always read `/sys/module/msm/parameters/separate_gpu_kms`.
- **`rmmod msm` oopses** in `adreno_remove` when the GPU bound through the plain component path (NULL drvdata). Do not
  try to reload it; set the option file and reboot.
- `evdev` is `=m` as well: without it there is no `/dev/input/event*` (`modprobe evdev`, or build it in).
- The firmware loads lazily, at the first open of the DRM device (about 8 s after boot); it then initialises the
  hardware, which includes the zap shader, so `gpu hw init failed` in `dmesg` is the line to look for.

### Phosh runs (phoc renders on the Adreno, scanout on simpledrm)

> **Historical** (2026-11-26): this was Phosh on simpledrm before the real display driver worked. It is superseded: Phosh now runs on the msm KMS
> device and starts on boot (see "Display: the real DPU/DSI/panel stack works" and "Phosh starts on boot" below). The traps (seatd, D-Bus) still apply.

`tools/run-phosh.sh` (run as root on the phone, from SSH) starts Phosh 0.59 for 45 s: `phoc` renders on
`/dev/dri/renderD128` (GLES2, `GL renderer: FD612`) and presents on the simpledrm card `/dev/dri/card0` (XR24 linear
buffers, atomic modeset 1080x2400 @ 60 Hz, wlroots multi-GPU copy). The shell, `gnome-session`, squeekboard, polkitd and
at-spi all come up and stay up. The only input is the volume key (`gpio-keys`) until touch works.

- **Packages, with no internet on the phone.** On the PC: build a scratch apk root from the phone's
  `/lib/apk/db/installed` and `/etc/apk/world`, then `apk.static --root R --arch aarch64 --repositories-file repos
  --allow-untrusted add --simulate phosh phoc` lists what is missing (350 packages, 210 MiB, no upgrades; repos are the
  three on the phone: postmarketos main, alpine edge main and community). `apk fetch -o repo/aarch64 <names>`, then
  `apk mkndx --allow-untrusted -o Packages.adb *.apk` (an apk 3 index must be called `Packages.adb`),
  `python3 -m http.server 8000 --bind 172.16.42.2 --directory repo`, and on the phone
  `apk --repositories-file F --allow-untrusted add phoc phosh seatd seatd-openrc` with `F` containing
  `http://172.16.42.2:8000/aarch64/Packages.adb`. Nothing is added to any OpenRC runlevel (diff `rc-update show -v`
  before and after). The rootfs is shared with slot A.
- **Traps.** `libseat` in Alpine has no `builtin` backend, so install `seatd` and use `LIBSEAT_BACKEND=seatd`. `phoc`
  stalls silently before it looks at the display unless there is a D-Bus session bus (`phosh-session` uses
  `dbus-run-session`). `kmscon-console` must be stopped first (it holds DRM master on card0). Set
  `WLR_LIBINPUT_NO_DEVICES=1` while there is no touchscreen.

### Touch: FocalTech FT5452 works (package r6)

The stock tree lists a FocalTech node and a Himax node on `i2c@884000` (our `i2c1`, `gpio4`/`gpio5`). Reading the bus
from userspace (`tools/i2cprobe.py`) showed **0x38 ACKs with chip id `0xa3=0x54, 0x9f=0x52` = FT5452**, and 0x48
(Himax) does not answer. Reset is gpio88 (active low), interrupt gpio89 (falling edge), the analog supply is gpio96 (a
fixed regulator here) and the I/O rail is `vreg_l13a`. The DTS node is `focaltech,ft5452`, 1080x2400.

**r5 had the device but the data was wrong.** `edt-ft5x06` bound as `generic ft5x06 (48)` and the interrupt fired, but the
chip kept reporting one stale contact: about 100 interrupts/s at idle, coordinates at about 3 Hz, and **no lift ever**
(one `BTN_TOUCH` in several minutes), so Phosh never saw a tap. The raw packet (read with `SLAVE_FORCE` over
`/dev/i2c-N`, register 0 onwards: count at 0x02, then 6 bytes per point, flag in bits 7:6 of byte 3: 0 down, 1 up, 2
contact) stayed `count=1 flag=2` after the finger left. Tried and ruled out: the interrupt trigger (`0xa4=01`, edge is
right), monitor mode (`0xa5` goes to 0 while touched and back to 1 about 2 s after release), the register map (identical
on slot A), a host firmware upload (the vendor driver also fails to load `focaltech_ts_fw_samsung.bin` and touch still
works downstream).

**Cause and fix.** The downstream driver (`drivers/input/touchscreen/ft3418_i2c`, repo `xiaomi-sdm678/android_kernel_xiaomi_mojito`
at the commit pinned in `downstream/linux-xiaomi-mojito/APKBUILD`) reads the whole frame, 10 points x 6 + 3 = **63 bytes**,
on every interrupt. Mainline's `edt_ft5452_data` has `max_support_points = 5` and reads 33 bytes, and the chip never
advances its table. Slot A's interrupt count stays flat at idle; r5's did not. Patch `0004-Input-edt-ft5x06-read-all-10-points-on-the-FT5452.patch`
sets it to 10. On r6 the idle interrupt count is 0, `TRACKING_ID`/`BTN_TOUCH` go down and up properly, and about 90
position events/s arrive while touching. Phosh reacts to taps and swipes.

### Phosh as a normal user (the lock screen needs a real password)

`tools/run-phosh.sh` runs Phosh as root. Root is locked (`!` in `/etc/shadow`) and there is no `phosh` PAM service, so PAM
falls through to `other` (deny all): **nothing can unlock the lock screen**. `tools/run-phosh-user.sh [seconds]` adds
`/etc/pam.d/phosh` (includes `base-auth`, `base-account`, `base-password`, the same check as `login`), starts
`seatd -g wheel` (the user is in `wheel`, so no group change is needed), makes `/dev/dri/renderD128` world readable
(until reboot) and runs `phosh-session` as `user` under `timeout`. Unlock with the account's password. The old script has
no timeout: kill `phoc` to end its session.

### Phosh starts on boot and controls the brightness (`mainline/autostart/`, `tools/install-phosh-autostart.sh`)

`PHONE_PW=... tools/install-phosh-autostart.sh` installs an OpenRC service `phosh-mojito` that auto-logs `user` in on `tty1`
(`getty -n -l phosh-autologin` -> `login -f user`); `~/.profile.phosh` then starts `phosh-mojito-session`, which waits for the msm
KMS card (the one with a DSI connector, found by name, not by number) and runs `phosh-session` on it with `renderD128` for
rendering. It also enables `elogind`, removes `kmscon-console` from the default runlevel (the text console holds DRM
master; restore it with `rc-service phosh-mojito stop; rc-service kmscon-console start`) and adds `user` to `seat`. Unlock with
the account password (PAM service `/etc/pam.d/phosh`). Phosh's brightness slider writes the DCS backlight and works.

Every one of these cost a boot cycle, so they are recorded:

1. **Brightness needs a logind session on a seat.** Phosh sets the backlight through `login1.Session.SetBrightness`; without it
   the log says `NotYourDevice: Your session has no seat`. A session started with `su`/`su -l` or OpenRC's `command_user` has
   no seat. A real login on a terminal of `seat0` (here `tty1`) does. elogind must be running.
2. **OpenRC's `command_user` drops supplementary groups**, so phoc could not open `/run/seatd.sock` (group `seat`): launch through
   `su`/`login`, which set them. OpenRC's `command_user` also opens the log file only after dropping to the user.
3. **OpenRC ignored the new service because the phone's clock is stuck in 1970.** The cached dependency tree
   (`/var/cache/rc/deptree`) looked newer than the new init script, so the service was never in the runlevel graph (0 matches in
   the cache; `openrc default` printed nothing). Run `rc-update -u` after installing any service (the installer does).
4. `checkpath -d` does not create parent directories and `/run/user` does not exist on this image (it says `could not open user`).
5. `supervise-daemon` silently failed to start the child here; use the plain background launcher.

### Other hardware found while here (all in the downstream device tree and live dump)

- `i2c3` (`0x88c000`, the vendor kernel's "i2c2") is enabled in r6 and ACKs for `wl2866d` (0x28, camera LDO), `aw87xxx`
  PA #1 (0x58, reg0 `0x59`) and `bq2597x` charge pump (0x65). **0x5b** (second PA) has `reset-gpio` tlmm 83 in the stock tree,
  so it stays silent until a driver releases it, and **0x43** (`fsa4480` USB-C audio switch) is silent until its side is
  powered. Probe with `tools/i2c3probe.py`. Mainline label mapping: vendor i2c0 `a84000` = `i2c5` (NFC `st21nfc` 0x08),
  vendor i2c1 `884000` = `i2c1` (touch), vendor i2c2 `88c000` = `i2c3`.
- Also enabled in r6: the PM6150L flash LED (`white:flash`, torch 300 mA / flash 1 A / 1.28 s) and the PMIC RTC (read
  only like the vendor tree, which sets `qcom,qpnp-rtc-write = 0`; it reads 1970).
- Audio, Wi-Fi and the modem need the remoteprocs first. The vendor ADSP boots from the `adsp.mdt` set already in
  `/lib/firmware`; the codec is `wcd937x`, the amps `aw87xxx`, Wi-Fi/BT `wcn3990` (`bdwlan.*`, `*btfw*.tlv`), NFC `st21nfc`.
  The downstream kernel has no working audio itself and no debugfs, so there is no live codec or clock state to copy.
- Charging: the stock tree uses `smb5` plus `bq2597x`; mainline has nothing matching, so battery readouts need a new
  driver or a fuel-gauge shim. Battery is a 5000 mAh Li-poly.
- The downstream live device tree can be dumped from slot A (`/sys/firmware/devicetree/base`, decompile with `dtc -I fs`).
  Keep such dumps out of the repo: they carry device identifiers.

### Display: the real DPU/DSI/panel stack works, brightness included (package r12)

The panel is a 1080x2400 Samsung-style AMOLED in DSI video mode (stock node `k7 38 0c 0a`, vendor commands behind
`F0 5A 5A`); brightness is the DCS command `0x51` (11 bit, 0..0x7ff, big endian), exposed as the backlight device
`/sys/class/backlight/ae94000.dsi.0` (max 2047). It took five separate fixes, each hiding the next:

1. **`CONFIG_DRM_MSM_DSI_14NM_PHY=y`**: it was off, so the PHY driver for this SoC was not even built.
2. **Patch 0006**, `qcom,sm6150-mdss` in the SMMU's `qcom_smmu_client_of_match` (identity default domain): without it the
   bootloader's scanout hit an empty translation context, hundreds of thousands of `Unhandled context fault` per second
   from 0.47 s, and a black screen.
3. **Patch 0007**, stop the bootloader's INTF timing engines in `dpu_kms_hw_init`: otherwise the DSI video engine
   stays busy and every panel command times out with -110.
4. **Patch 0005**, the panel driver `panel-xiaomi-mojito-k7` (init/off sequences, timings, reset, backlight) plus the
   `&mdss`, `&mdss_mdp`, `&mdss_dsi0`, `&mdss_dsi0_phy` nodes and the panel node in the DTS.
5. **The last one was a power-cycle, not a register.** With the framebuffer holding `MDSS_CORE_GDSC` and the display clocks
   the display core never power-cycles, the bootloader's leftover state survives, the CTL sits in a hardware reset
   (`hw recovery is not complete for ctl:1`, flush `0x80020041` never latches, `DANGER_STATUS=0x33`, MDP irq never
   fires) and the panel shows solid **blue** (the DPU underflow colour: DSI, panel and INTF timing are all fine). **Remove
   `power-domains` and `clocks` from the `framebuffer@9c000000` node** (done in the DTS, with a comment): genpd then collapses
   the domain once nothing uses it and msm powers it up fresh. Cost: a few seconds of green/black between the splash
   and the first real frame. A manual `echo 4 > /sys/class/graphics/fb0/blank; echo 0 > ...` (with kmscon stopped) did
   the same by hand and found the cause.

What did NOT help (each tested, do not repeat): MDP core clock (forced 307 MHz), lut/rot clocks, `INTF_CONFIG2`/DATA_HCTL,
UBWC static register, SMMU prefetch (ACTLR), VIG instead of DMA pipe, interconnect votes, VBIF, DSI host registers,
`VIDEO_BURST` (the stock traffic mode is non-burst; our DSI registers matched the bootloader's). An `mdss` `resets =
<&dispcc DISP_CC_MDSS_CORE_BCR>` line (as sm6125/sm6350 have) needs a reset map in `dispcc-qcs615.c` (`{0x2000}`, absent
upstream) and then **hangs the phone at probe** (the reset hits a live scanout), so it is not used.

Debugging aids that found it: the DPU register dump `/dev/mem` (blocks listed in the scratch scripts; `ctl:N` in the log is a
1-based enum, so `ctl:1` is `ctl_0` at `0x1000`), `msm_disp_snapshot` devcoredump, the bootloader's working state read on the
r6 image (no msm), and the downstream kernel rebuilt with `CONFIG_DEVMEM`/`CONFIG_DEBUG_FS` (stock 4.14 has neither; do not read the whole
GCC space or all PMIC regmaps on it, both crashed the phone). Repro of the old failure: `rc-service kmscon-console restart`, then
count `vblank timeout` in `dmesg`. Boot with `separate_gpu_kms=1` in `/etc/modprobe.d/msm.conf` still works; `dpu_prefer_vig` is not needed.
Patch 0007 may be unnecessary now that the domain collapses; it is harmless.

### Display: the bootloader splash now stays up (simpledrm), login visible

> **Historical:** these framebuffer power-domain/clock holds were REMOVED once the real display driver worked, because holding the domain
> keeps the DPU stuck in the bootloader's state (see "Display: the real DPU/DSI/panel stack works").

The panel (an OLED, no backlight device) shows the bootloader's splash through simpledrm, and kmscon's login
appears. Two properties on the `framebuffer@9c000000` node in the DTS did it; each fixed a different failure:

1. **`power-domains = <&dispcc MDSS_CORE_GDSC>`**: without it, genpd `sync_state` powers `mdss_core_gdsc` off
   about 6 s after boot (`pd_ignore_unused` only stops the late-init sweep, not this path) and the panel goes
   noisy green. `pm_genpd_summary` shows the domain staying on.
2. **`clocks = <&dispcc …>`**: AHB, MDP, VSYNC, ESC0, BYTE0 and PCLK0. Their gates were open (the bootloader
   left them so) but the kernel's enable/prepare counts were 0, and with only the power domain the panel went
   **black**. simpledrm calls `clk_prepare_enable()` on each entry, so the counts are 1 now. BYTE0 and PCLK0 read
   0 Hz (their DSI PLL parent is registered by `msm.ko`); they are only gated on, which is already their hardware
   state, so the bootloader's pixel timing is untouched.

Ruled out on the way (none of these is needed, none is in the repo): `regulator_ignore_unused` (no regulator was
being disabled: no `: disabling` lines in `dmesg`), a driverless DT consumer holding the NoC providers pending
with `fw_devlink.sync_state=strict` (it works, `sync_state() pending due to display-keepalive`, but the panel was
black until the clocks were added), the backlight (there is no backlight device), and `msm.ko` (not loaded).

Diagnosis tools that found it: `/sys/kernel/debug/pm_genpd/pm_genpd_summary` (domain state and its consumers),
`/sys/kernel/debug/clk/clk_summary` (the enable/prepare counts, not just the hardware-enabled column),
`/sys/kernel/debug/dri/0/state` (which client owns the plane), and `dd if=/dev/fb0` converted to a PNG to see what
is in the framebuffer.

This is still the **splash**, not a real display driver. When `msm.ko` loads (GPU work, later), it takes over from
simpledrm and the DPU, DSI host, DSI PHY and a panel driver are needed; those will replace these two properties.

### Debugging workflow that worked

- **Console on the panel** is the only log until SSH is up. This cmdline names the device that hangs:
  `loglevel=8 printk.time=1 panic=0 dyndbg="file drivers/base/dd.c +p"` (the last "probing driver X with device Y"
  line before a freeze). `fbcon=font:VGA8x8` garbles the console; do not use it.
- **No log survives a reset.** ramoops is attached on both kernels (`0x9d800000`, same layout), but `/sys/fs/pstore`
  was empty after a normal reboot, `sysrq-b` and a downstream kernel panic. The PMIC reports "Hard Reset and 'cold'
  boot, previous power-off from PS_HOLD", i.e. RAM loses power. A secure-world or watchdog reset might behave
  differently but is untested. Downstream has no `/dev/mem` or `/proc/kcore`; mainline has `/dev/mem` (MMIO works).
- **DTS-only changes** need no pmbootstrap build: `mainline/build-dtb.sh <linux-tree> out.dtb`, then
  `mk-bootimg-v2.sh`, then flash `boot_b` (one minute per iteration).
- **Slots:** after 7 failed boots ABL falls back to slot A once, and to fastboot when slot A's retries are also used up
  (the downstream OS never marks itself successful). `fastboot set_active b` resets the counter. Run
  `fastboot devices` and check the phone is listed *before* chaining commands, or they wait silently.
- **No buttons needed:** over SSH, the `reboot(…, "bootloader")` syscall from the top of this file works on both
  kernels.
- **SSH from scripts:** `sshpass` is not installed. Use a throwaway `SSH_ASKPASS` helper and delete it afterwards.
  `python3 -I` breaks mkbootimg (it drops the script directory from the import path). Do not `pkill -f <name>`
  from a command line that contains `<name>`: it kills your own shell.

### Boot attempts with header v3 (earlier; all fell back to fastboot with only the Mi logo on screen)

| Packaging | Result |
|---|---|
| v3, DTB board-id `0 0`, `dtbo_b` erased | fastboot after ~4 s (ABL refused) |
| v3, empty overlay (no fragments) in `dtbo_b` | fastboot after ~12 s |
| v3, wider load addresses (kernel 0x10008000, dtb 0x13f00000, ramdisk 0x14000000) | ~12 s |
| v3, overlay with a fragment (`dummy-overlay.dts`) | ~12 s |
| v3, stock `dtbo` | ~12 s |
| **Control:** downstream kernel + DTB with the same v3 packaging and stock `dtbo` | **boots fine** |
| Control with the dummy dtbo instead | ~12 s |
| v2 `boot.img` (raw Image + initramfs + DTB with board-id `0x22`, `__symbols__`), `dtbo_b` erased | **boots the kernel**: this is the recipe that works (see Status above) |

On pstore: see "Debugging workflow that worked": the empty pstore after resets is explained by the PMIC power
cycling RAM on the reset types tested.

### The best lead: the Redmi Note 7 Pro port

`github.com/VipinVIP/violet-sm6150-mainline` boots Linux 7.2.10 natively from ABL on another Xiaomi SM6150
phone (display, touch, Wi-Fi, modem, audio out work; GPU renders but hangs under load). Their recipe:

- **`dtbo` erased** (with a valid dtbo, ABL applies the stock overlay to the mainline DTB, fails and refuses).
- **Header v2 `boot.img`** with the DTB inside: raw `Image`, `--base 0 --kernel_offset 0x8000
  --ramdisk_offset 0x1000000 --tags_offset 0x100 --dtb_offset 0x1f00000 --pagesize 4096`.
- DTB patched with `qcom,msm-id = 0x163 0x0` and **`qcom,board-id = 0x22 0x0`**, compiled with `-@`.
- Their `docs/RULED-OUT.md`: silent resets were Linux being handed a firmware-protected page, so reserved
  memory must be complete (done here).
- Patches 0002 (tzmem: no SHM bridge on sm6150) and 0003 (qcs615 interconnect ACV enable mask) are copied
  into this kernel package; 0017 (SMMU hyp-owned context banks) and the pd-mapper/glink patches matter for audio
  and modem later. Credit: VipinVIP.

### Next steps

1. **GPU: done for off-screen rendering** (see above). Remaining: a KMS output for a compositor (item 2), and Vulkan
   (turnip) if wanted. `kmscube`, `eglinfo`, `phoc` and `phosh` are not installed and the phone has no internet; fetch the
   apks on the PC (`pmbootstrap` or the edge mirror) and serve them over the USB link.
2. **Display: done** (see above). Next: run Phosh on the msm KMS device (`WLR_DRM_DEVICES` = the msm card, `renderD128` for rendering,
   no simpledrm) and then KWin/Finder; `tools/run-phosh*.sh` still point at simpledrm's `card0`; the autostart above is the supported way to start Phosh now.
3. **Touch: done** (r6, see above). Next, with TLMM working and any pin outside gpio0-3 / gpio6-9 usable: panel reset/TE,
   then the ADSP remoteproc on its own build (it is the audio/modem/Wi-Fi prerequisite and the likeliest to hang the boot,
   like the secure-world pins did), then charging (smb5 + bq2597x have no mainline match), Wi-Fi, audio, and finally KWin 6
   and Finder. (Panel reset/TE: the reset pin is already used by the panel driver.)
4. The kernel package (`7.4_rc4-r12`): patches 0001-0007, `QCOM_WDT=y`, `EFI_ZBOOT` off, raw `Image` installed as
   `/boot/Image`, `LOCALVERSION=-sm6150`, and `DRM_MSM=m` (the modules are in the package). Its DTB has board-id `0 0`; `mk-bootimg-v2.sh` patches in
   `0x22` when packing. Patch 0001 is regenerated from `mainline/sm6150-xiaomi-mojito.dts`; for DTS-only
   changes use `build-dtb.sh` instead of rebuilding the package.

### Battery, charging, ADSP, modem (2026-11-26, packages r13-r21)

**Battery: `qcom_qg_lite` (patch 0010).** A new, small driver for the PM6150 **QGauge** block (`qgauge@4800`, SDAM `0xb600`),
which the bootloader leaves running. It reads `LAST_ADC_V` (0xc0, 194.637 uV/LSB) and `LAST_BURST_AVG_I` (0xc6; subtype 0x04 on
this phone = 10 A range, 305.176 uA/LSB; positive = discharging, reported negated per the power_supply ABI). SOC starts from SDAM
`0x47` (if within 10 points of the OCV estimate), then coulomb counting, pulled toward the OCV table (voltage + I x 120 mOhm) mostly
when |I| < 100 mA; it writes the reported SOC back to SDAM `0x47` (the only write). Learned capacity from SDAM `0x68` (4539 mAh here).
The OCV tables are the stock profile `m305-nvt-5000mah` (`pc-temp-v1-lut`, 0/10/25/40/50 C) in the DTS `simple-battery` node.
Battery temperature needs patch 0009 (adc5 `BAT_THERM_100K_PU`): without it an unknown channel fails the whole ADC probe. While the
`power-supplies` charger is online its status is reported, because on a weak input the battery current changes sign every few
seconds (the load is right around the 500 mA SDP limit) and a current-based status flaps. Another SM6150-family gauge exists in the
sm7125 kernel (`qcom_qg.c`, same compatible): it hard-codes the 5 A scale (2x off here) and reports STATUS_UNKNOWN.

**Charging: SMB5 (patch 0008).** Ported from the pipa SMB5 patches. Changes that mattered, each found on hardware:
- No Type-C/OTG writes at probe (rewriting them could drop the USB link, the only connection).
- Watchdog pet address is `base + 0x643`, not absolute `0x643`.
- Input current: wall chargers (DCP 2 A) and CDP (1.5 A) use high-current mode with "ICL override after APSD" (vendor
  `SW_OVERRIDE_HC_MODE`); in hardware-automatic mode the limit register is ignored and an SDP gets 100 mA.
- SDP (and FLOAT, which an SDP often reads as right after a replug) use **USB51 500 mA mode without the ICL override**: with the
  override set (what the vendor code does) this PMIC **suspends USBIN** (POWER_PATH_STATUS 0x110b bit 6) and the phone runs on battery;
  the suspend latches until a replug. Afterwards: clear USBIN suspend, re-run AICL (0x1644).
- Status from the charge state (0x1006 bits 2:0) first; the VBATT >= inhibit flag (0x1007 bit 5) is set during a near-full taper.
- Recharge is VBAT based (bootloader sets CHGR_CFG2 0x1051 = 0x2c), threshold 4.20 V (raw 0x544a at 0x107e).
- Verified: wall charger ~1 A in (AICL-limited), +0.4 A into a 98 % battery; PC port 500 mA; boot with the cable in. Not verified:
  charging from a low battery (2 A FCC), a long discharge for gauge accuracy.

**ADSP.** Upstream `remoteproc_adsp` + `firmware-name = "postmarketos/adsp.mdt"` (stock, signed for this phone), carve-out at the
stock 0x95900000 (the Note 7 Pro needs 0x95300000). `QRTR_SMD`, `RPMSG_QCOM_GLINK_SMEM`, `QCOM_FASTRPC`, `QCOM_PD_MAPPER` are built
in (as modules they load too late). Patches 0011-0013 from the Note 7 Pro port (pd-mapper one entry per domain + `qcom,sm6150`
match, glink early intents, rpmhpd MSS). Boots in 0.6 s at ~5 s uptime; channels `IPCRTR`, `apr_audio_svc`, `apr_apps2`, fastrpc.

**Modem.** DTS nodes added (talos.dtsi/QCS615 has none): `smp2p-mpss` (SMEM 435/428, SPI 451, `apss_shared 14`, entries
master/slave-kernel, wlan, ipa), `remoteproc_mpss` (`qcom,sm8150-mpss-pas`, pas-id 4, wdog SPI 266, glink edge SPI 449 /
`apss_shared 12`, `firmware-name = "postmarketos/modem.mdt"`), `rmtfs@a1dff000` (0x282000 with guard pages, client-id 1,
`MSS_MSA` VMID; the stock tree allocates it dynamically), IPA v4.2 (`qcom,sc7180-ipa`, SPI 311/432, SIDs 0x1520/0x1522).
- `rmtfs -s` starts the modem itself (`auto_boot = false` otherwise). Firmware: `MPSS.AT.4.4.c6 ... RENNELL_GEN_PACK`.
- **IPA firmware: this phone ships `ipa_fws` (stock `qcom,ipa_fws`, PAS 15), so the AP must load it: `qcom,gsi-loader = "self"`,
  `memory-region = <&ipa_fw_mem>`, `firmware-name = "postmarketos/ipa_fws.mdt"`.** With the Note 7 Pro's `modem-init` the modem never
  raised `ipa-clock-query`/`ipa-setup-ready`, there was no `rmnet_ipa0`, and ModemManager found no modem; a modem started after IPA
  was loaded stalled ("DOG detects stalled initialization") after 40 s.
- ModemManager 1.25.95 uses the `qcom-soc` plugin (`qrtr0` + `rmnet_ipa0`); data goes over `qmapmux0.0`.
- Data off once failed: ModemManager sent WDS Stop Network with handle `FF:FF:FF:FF` (it had lost the real one), the modem said
  `InvalidHandle`, MM stayed "connected" and NetworkManager left the WWAN radio off, so the toggle never came back. Seen after
  restarting the modem/IPA by hand under a running MM; not reproducible after a clean boot (off/on and autoconnect work). Recover with
  `nmcli radio wwan on`; if it recurs, capture `mmcli -G DEBUG` logs of the Start Network.
- `qmi-utils` (qmicli) is installed for debugging; this firmware rejects the WDS autoconnect query (`InvalidOperation`).

### Wi-Fi (WCN3990 / ath10k): node added, handshake fails (disabled in the DTS)

`wifi@18800000` from the stock `qcom,icnss@18800000` (SID 0x1640 mask 1, CE SPI 414-425 with four cells, rails pm6150 L9 /
pm6150l L1, L2, L10). The stock `wlan_msa_region` is 2 MB but the firmware gets 1 MB (`qcom,wlan-msa-memory`), so the DTS splits it.
Files on the phone (`/lib/firmware/ath10k/WCN3990/hw1.0/`): `firmware-5.bin` from linux-firmware-ath10k (a 60-byte feature
descriptor; the code is `wlanmdsp.mbn` on the modem) and the stock `bdwlan.bin` as `board.bin`. `ath10k_snoc` is blacklisted
on the phone (`/etc/modprobe.d/ath10k.conf`).

ath10k reaches the modem's WLFW service (QMI 69), then:
- no quirk: `host capability request rejected: 90`; `qcom,snoc-host-cap-8bit-quirk`: rejected with 1 (malformed);
- `qcom,snoc-host-cap-skip-quirk`: MSA info / permissions / MSA ready pass, then `capability req rejected: 119`;
- every time the modem's `wlan_process` crashes ~10 s later (`EF:wlan_process:0x1:qmi_platform:...:cmnos_thread.c`), PDR restarts
  it, and the loop repeats; cleanup prints `failed to unmap msa permissions: -22` (a consequence, not the cause);
- `qcom,msa-fixed-perm` **hangs the boot** in udev ("waiting for uevents") even with ath10k blacklisted: do not use it;
- 1 MB vs 2 MB MSA: no difference. ath10k's QMI code is identical between 7.2 (Note 7 Pro, Wi-Fi works) and 7.4.
Later tests (2026-11-26 evening):
- **L10a (1.8 V, the WCN I/O rail, always on in the stock tree) was unpowered**: nothing in Linux votes for it. With
  `regulator-always-on` the host capability request passes without any quirk (error 90 = "incompatible state" is gone). Kept in the DTS.
- Still `capability req rejected: 119` afterwards, unchanged by: `RPMH_RF_CLK2` as `cxo_ref_clk_pin`; all WCN rails at the stock
  voltages (L9a cx-mx 640 mV as `qcom,vdd-cx-mx-config`, L1c 1.8, L2c 1.304, L10c 3.304) and always on before the modem boots. The board
  has no ch1 rail (stock BT and icnss use L1c/L2c/L10c only); SID 0x1640 is the stock value (SM7150 uses 0x240).
- `tqftpserv -d` (run under `script` so the output is flushed): the modem requests only `/readwrite/server_check.txt` and
  `ota_firewall/ruleset` at boot and nothing when WLAN starts, so the WLAN image is inside the modem firmware here.
- **Do not restart the modem (`rc-service rmtfs restart`) while IPA is set up**: the modem asserts in `ipa_hal.c` (GSI) and IPA then
  times out (-110); `rmmod ath10k_snoc` hangs afterwards. Reboot instead.
- Reference with working WCN3990 on the same family: sm7150-mainline/linux (Xiaomi sweet/davinci) uses a `qcom,wcn3998-pmu` node
  (swctrl GPIO, vddio) and no quirks. Stock icnss comparison (Xiaomi kernel `drivers/soc/qcom/icnss.c`, `icnss_qmi.c`): sequence ind_register -> msa_info -> assign MSA
  (MSS_MSA + WLAN [+ WLAN_CE], same as ath10k) -> msa_ready -> cap; **no host cap** (ath10k's skip quirk matches); same client id
  0x4b4e454c; the empty cap request matches. **The one difference: icnss sets `pin_connect_result_enable` in ind_register, ath10k does
  not** -> candidate fix `mainline/wip/0015`, untested (modules were built, the session ended before loading them).
- **`mainline/wip/0015` TESTED (2026-11-26): does NOT fix it.** Patched ath10k_core/snoc (out-of-tree build, loaded from `updates/` on the test DTB:
  L10a always on, msa-fixed-perm, ch1): still `capability req rejected: 119`, then `PDM: service 'wlan_process' crash: EF:wlan_process:0x1:qmi_platform:0x509c:cmnos_thread.c:4`
  ~10 s later, firmware crashed, repeat. So `pin_connect_result` is not the missing piece. The patched modules are still in
  `/lib/modules/7.4.0-rc4-sm6150/updates/` on the phone (snoc stays blacklisted; remove `updates/` to return to stock). Next ideas: capture the stock icnss QMI 69
  traffic under downstream, the `qcom,wcn3998-pmu` node, or park Wi-Fi and do audio (step 2).
- **Stock `wlanmdsp.mbn` reverse-engineered with REA/Ghidra 12.2 (Hexagon; file `stock/extract/fwall/wlanmdsp.mbn` in the work dir, sha256 4b1510cc...).** The firmware is
  the on-SoC WCSS "Helium" WLAN block (`platform_helium*.c`, RF part over WSI, "Adrastea Clock"), not an external chip. `wlfw_process_req_cb` is FUN_b02166d8 (dispatcher; ids match ath10k:
  0x20 ind_register, 0x23 wlan_cfg, 0x24 cap, 0x2d msa_info, 0x2e msa_ready, 0x34 host_cap). **The cap request (0x24, handler FUN_b01c0628) is where the firmware powers the WLAN block up for the
  first time**: it calls FUN_b01c15b0 (= platform_helium_init: PLATFORM_CLIENT registration, `ccpm_ccvs_plat_req` voltage/clock votes, a write + poll on WCSS reg 0xa6750000, chip-id read at base+0x80000
  matched against a table, `platform_ccpm_init`). Non-zero return -> error response (our 119, the error code is not a named constant at the call site); the asserts in this path are `platform_helium_init.c`
  `plat_init_num_macs` / `platform_ccpm_init`. So the 119 is a failed modem-side power-up, not a host-protocol problem; the open question is WHICH step (precondition FUN_b01c1568, ccpm vote FUN_b0147d50 ->
  "CCPM not initialized" = 0xd, the 0xa6750000 poll, or the chip-id table). Firmware also reads WLAN_SW_CTRL_GPIO / WCSS_PWR_REQ_GPIO itself. Stock DT `cnss_wlan_en` (gpio98) is defined but referenced by nothing.
  Next: get the modem's own F3/diag log of that sequence (msg_v2_send strings), or read the failing step's return values; then match against rails/clocks/interconnect votes done by Linux.
- **Static trace of FUN_b01c15b0 (REA/Ghidra), result so far:** NOT failing: precondition FUN_b01c1568 (calls ccpm_mgr_init FUN_b0147c50, always 0, and a static PLATFORM_CLIENT table lookup FUN_b01478b4, never
  null), and the poll FUN_b01c2b30 on 0xa6750000 (return value ignored). Asserts (crash, not error reply): `platform_ccpm_init` via FUN_b014a3c8/FUN_b01c14c0 and `plat_init_num_macs` (chip-id table miss at base+0x80000).
  Can return 1 (=> our error reply): `ccpm_ccvs_plat_req` FUN_b0147d50 (0xd "CCPM not initialized" if flag DAT_b03200a0 bit0 clear, 0xc if client/manager NULL) and `ccpm_request_wlan_pwr` FUN_b01478e8
  (state 6 and 7): returns 0xc if the client's manager pointer (+0xc of the static PLATFORM_CLIENT struct at 0xb0300300, 0 in the image, filled at runtime) is NULL, and for a type-1 client returns 0 (success) ONLY when the
  global DAT_b0300ac0 == 1 (written at 0xb014b028, code Ghidra did not define as a function; not yet decoded). Hypothesis (unproven): DAT_b0300ac0 / the manager pointer depend on state set by an earlier host request or
  SMP2P bit that ath10k does not provide. Static tracing is slow here; a runtime log of the modem (msg_v2_send / ULog) would name the step directly.
- **Modem coredump via remoteproc: tried 2026-11-26, USELESS as is.** `echo enabled > /sys/class/remoteproc/remoteproc1/coredump`, load ath10k_snoc, `echo 2 > /sys/kernel/debug/remoteproc/remoteproc1/crash`:
  the modem restarts cleanly (IPA/data came back, no reboot needed) and a 135.9 MB ELF core appears in /sys/class/devcoredump/devcd1/data, but EVERY byte of every segment is zero.
  Cause: `rproc_boot_recovery()` runs `rproc_stop()` (-> `qcom_pas_shutdown()`, TZ reclaims/scrubs the modem memory) BEFORE `rproc->ops->coredump()`. The mpss descriptor also has `minidump_id = 3`.
  No `DIAG*` glink channel is exposed (modem channels: DATA1-4, DATA11, DS, IPCRTR, apr_*, glink_ssr...) and no diag-router tool is packaged. Getting modem memory would need a kernel patch that copies the
  region before the shutdown (untested; reading modem-owned memory from HLOS can hit the XPU and reset the AP, like the secure-world GPIOs did). Do not repeat the stock dump.
- **DAT_b0300ac0 decoded (2026-11-26).** Ghidra missed the setter (Hexagon packets/immext confuse its function discovery); `llvm-objdump-18` decodes it. The flag is written `= 1` at 0xb014b028, the tail
  of the CCPM client-init routine at **0xb014ada0** (loops 8 entries of a table at 0xb0300840, also sets byte `gp+0xf0 = 1`, which the QMI dispatcher tests). It has no direct callers: it is tail-called (0xb0148bfc)
  from `0xb0148bdc(obj, state)` when `state == 1`, and that function is installed at `ops+0x38` of a per-client-type ops table (switch at ~0xb01488a0-0xb0148a00). The ops slots are called from CCPM
  state-machine walkers (e.g. 0xb01476d8 walks a client list, 0xb0149138 loops clients by bitmask), i.e. driven by the modem's own power-resource votes, not by a host input we can see.
  Conclusion: the `ccpm_request_wlan_pwr` failure (needs DAT_b0300ac0 == 1) means the CCPM client-init never ran before the first WLAN power request; WHO triggers state 1 is not found. Static tracing = many
  hand-read Hexagon hops; not worth continuing unless a runtime trace becomes possible.
  Disassembly recipe (no Ghidra needed): carve the LOAD segment (vaddr 0xb0000000, size 0x2e8370) with a few lines of python, `llvm-objcopy-18 -I binary -O elf32-hexagon --rename-section
  .data=.text,alloc,load,readonly,code seg.bin seg.o`, `llvm-objdump-18 -d --triple=hexagon --mcpu=hexagonv66 --adjust-vma=0xb0000000 seg.o`. Printed call/jump targets are section-relative:
  real target = 0xb0000000 + printed. A packet starts after the previous line containing `}`; a function entry is a packet start (allocframe is mid-packet).
- **CORRECTION (2026-11-26): the modem does NOT have the WLAN image built in; it fetches `wlanmdsp.mbn` from the AP through tqftpserv.** The modem blobs (modem.b17) hold the `wlan_pd` /
  `wlan_process` PD definition with the candidate paths `/readonly/firmware/image/wlanmdsp.mbn`, `/readonly/vendor/firmware_mnt/image/wlanmdsp.mbn`, `/readonly/vendor/firmware/wlanmdsp.mbn`;
  tqftpserv maps them into the directory the modem itself was loaded from (`/usr/lib/firmware/postmarketos/`), where the phone has `wlanmdsp.mbn` (sha256 4b1510cc..., byte-identical to the stock ROM's
  modem/image/wlanmdsp.mbn, WLAN.HL.3.2.2-00993; `wlanmdsp.otaupdate` is a dangling symlink to /data/vendor/firmware/). Its atime is 1 s after modem.mdt's, i.e. it is served at modem boot, minutes before
  ath10k is loaded by hand. So the 119 is NOT a race and NOT a missing/mismatched wlanmdsp: the WLFW service only exists once that image runs, ind_register/msa_info/msa_ready are answered by it, and the cap
  rejection is produced by the image's own power-up routine (see the decompilation notes above). (The pmbootstrap rootfs chroot has a DIFFERENT wlanmdsp.mbn, sha256 5b426fc0...; not what the phone runs.)
- **Community PMU/pwrseq test (2026-11-26): no change.** The 7.4-rc4 kernel already has `pwrseq-qcom-wcn` (WCN3990/3998, VDD_IO first, XO/RF/CH0/CH1, 50 ms) and ath10k_snoc pwrseq support, as used by the
  SDM845/SM8150 boards. The DTS now has a `qcom,wcn3990-pmu` node (vddio L10a, xo L1c, rf L2c, ch0 L10c, ch1 L11c) and the wifi node takes its supplies from it. On hardware (stock ath10k modules, no patch):
  still `capability req rejected: 119`. The sw-ctrl GPIO of this SoC family was not found (sm7125 tree 403, sm7150 tags too old), the driver does not read swctrl-gpios. The test DTB (wifi node `okay`) is
  what boot_b holds; the repo DTS keeps the PMU node with the wifi node disabled.
- **WI-FI, SESSION 2026-11-26 (all tested on hardware; every one still ends in `capability req rejected: 119`):**
  GPIO 98 `cnss-wlan-en` hogged high from boot (it reads LOW otherwise; stock DT and the violet port drive it high; hog in the repo DTS now); WCN rails always-on at violet's voltages (LPM) - reverted, no effect;
  community PMU/pwrseq node (`qcom,wcn3990-pmu`, kept in the DTS); `VBATT_REQ` (QMI 0x32, one TLV 0x01 u64 uV) sent from a QRTR client BEFORE ath10k connects at 4.46 V and 3.9 V: the firmware answers success,
  cap still 119 (so the handler's stored level is not what rejects it); ath10k waiting for `MSA_READY_IND` before the cap request (`mainline/wip/0016`, like cnss-daemon): the indication is already there 15 us after
  the msa_ready response, still 119. The cap request is answered after a repeatable ~200 ms (first WLAN-process instance after boot) / ~420 ms (later instances), i.e. the firmware times out waiting for something
  in its power-up and rejects the request. CORRECTION: the WLFW thread is NOT wedged afterwards (BDF download and cal report are answered ~6 ms after the rejection); my earlier 'wedge' reading came from a test
  client stalling in the kernel's QRTR TX flow control. wlan_process is killed ~9.4 s later ('EF:wlan_process:0x1:qmi_platform:0x9b:cmnos_thread.c:400'); a plausible (UNVERIFIED) reason is a firmware watchdog waiting for the host's
  WLAN_MODE/config requests, which ath10k never sends once the capability request failed, so the crash is probably a consequence, not the cause.
  After the failed cap the firmware DOES accept BDF download and cal report (debug_mask=0x300000 shows `qmi bdf download request completed`, `qmi cal report request completed`).
  Debug recipe: `modprobe ath10k_core debug_mask=0x00300000` before `modprobe ath10k_snoc`.
- **Cap request internals + last experiments (2026-11-26):** disassembly (llvm-objdump-18 on the carved wlanmdsp LOAD segment) shows the cap handler sets `r2 = #0x77` whenever the platform init FUN_b01c15b0 returns non-zero:
  119 is a CONSTANT meaning 'WLAN platform init failed', not a deeper status. ath10k `wip/0017` (wait for MSA_READY_IND, keep MSA permissions on cap failure, resend the cap request 3x after BDF+cal): the retried cap request
  gets NO reply at all (ath10k blocks in qmi_txn_wait) until wlan_process is killed ~9.4 s after the first rejection, i.e. the init cannot be re-run after it failed once, and BDF-before-cap is NOT the missing prerequisite.
  Only the first rejection (~200 ms after the request) carries information. Next, if continued: find the ~200 ms wait inside FUN_b01c15b0 (suspects: ccvs/pwr requests FUN_b0147d50 / FUN_b01478e8 states 6 and 7, RFA/WSI reset,
  WCSS clock measure) with the REA/llvm-objdump recipe above.
- **Host capability sweep (2026-11-26, `mainline/wip/0018`, live-tunable `/sys/module/ath10k_snoc/parameters/hostcap_mode`: 1 skip the request as stock icnss does, 2 daemon_support=1, 4 bdf_support, 8 cal_filesys_support,
  16 cal_done=0, 28/30 combinations as the ginkgo port): EVERY setting, and the default, still ends in `capability req rejected: 119` (0.2-0.45 s after the request). What the host says in the host-cap message is NOT the cause.
  Also negative: exact stock GPIO98 pinctrl state (out high, pull-up, 16 mA, now in the DTS bound to remoteproc_mpss). Stock icnss source (xiaomi-sdm678/android_kernel_xiaomi_mojito @4f60b376): no GPIO/pinctrl at all, powers the
  rails only AFTER the WLFW server arrives (before ind_register), cx-mx 640 mV via qcom,vdd-cx-mx-config, ch0/ch1 3.312 V, no host cap, no cold-boot-cal handling (that is the separate cnss-daemon).
- **Firmware-build swap (2026-11-26):** the modem reads `/usr/lib/firmware/postmarketos/wlanmdsp.mbn` at MODEM BOOT only (swapping the file while the WLAN process restarts changes nothing; a reboot is needed). A corrupted file
  (first 4 KB zeroed) gives no WLFW service and the modem crashes ~50 s after boot, so the file really is what the modem runs. The older same-line build `WLAN.HL.3.2.2-00715` (the copy in the pmbootstrap rootfs chroot,
  sha256 5b426fc0...) fails IDENTICALLY (`capability req rejected: 119`, ~0.2 s), so the rejection is not specific to the -00993 build. Original restored on the phone (`wlanmdsp.mbn.orig` kept next to it).
  Fast test loop that worked: swap/load, reboot, poll ssh + a QRTR WLFW lookup (service 69) instead of fixed sleeps: reboot to result takes ~40 s; module parameters can be changed live between WLAN-process restarts.
- **violet startup-script comparison (2026-11-26; phone/violet-modem.initd, phone/rmtfs.initd in VipinVIP/violet-sm6150-mainline):** violet runs `rmtfs -o /var/lib/rmtfs` (file storage that accepts writes, seeded with dd from modemst1/modemst2/fsg),
  starts tqftpserv + rmtfs first and the modem (`echo start > remoteproc/state`) afterwards, retries stop/start up to 4x. OUR phone ran `rmtfs -s -P -r` (partitions, READ-ONLY, modem writes dropped; from /etc/conf.d/rmtfs
  `rmtfs_avoid_writing="true"`). Tested: `rmtfs -s -o /var/lib/rmtfs` writable, files seeded from ~/.claude-work/pmos-mojito/efs-backup-2026-11-26/*.img (the modem DID write modem_fs1/fs2) -> still `capability req rejected: 119`.
  Config now violet-style (`/etc/conf.d/rmtfs`: rmtfs_files_path=/var/lib/rmtfs, avoid_writing=false; original saved as rmtfs.pmos-default). Modem stop/start with IPA loaded: the modem dies 40 s later
  (`DOG detects stalled initialization`) and recovery never completes (IPA does not re-handshake): do not restart the modem without rebooting. Boot order on our phone is already tqftpserv -> rmtfs (-s starts the modem at ~8.2 s).
  Hazards learned: `dd`/`head` reads of /dev/disk/by-partlabel/modemst* hang in the kernel (D state, unkillable, `sync` then hangs; recover with `echo b > /proc/sysrq-trigger`); reading the modem carve-out
  (0x8b000000, 132 MB) via /dev/mem hangs the reading CPU (RCU stall) - violet's RULED-OUT says the same ('reads of the modem carve-out reset the SoC'): a pre-shutdown memory capture is NOT possible.
- **Android reference (stock vendor.img, `debugfs -R "rdump /etc/init ." vendor_a.img`, no root needed):** starts qrtr-ns, pd-mapper, pm-service/pm-proxy (peripheral manager, only AP-side voting), tftp_server, rmt_storage (modemst1/modemst2/fsg/fsc,
  same as rmtfs), cnss-daemon (a second WLFW client: waits for MSA ready, cold-boot cal, BDF update by ro.boot.hwversion), `insmod qca_cld3_wlan.ko`; the hardware is called HELIUM (`cnss_diag -t HELIUM`). The kernel pd-mapper table matches the stock
  modemr.jsn/modemuw.jsn (wlan_pd: elf_loader, servreg, wlan/fw, instance 180). Nothing there feeds the modem's cap handler.
- **Slot A (vendor 4.14) as an A/B:** the modem boots via `/dev/subsys_modem` (PAS path, no mba needed; `rc-service rmtfs start` first), then dies after ~40 s with `DOG detects stalled initialization` because `ipa_fws` is not up;
  opening `/dev/subsys_ipa_fws` made the phone reset twice with NO kernel message (hard reset; /var/log is persistent there, `dmesg` snapshots every second showed nothing). No Wi-Fi data from slot A; do not repeat without a new idea.
- **violet-sm6150-mainline (github.com/VipinVIP/violet-sm6150-mainline) check:** its Wi-Fi node/modem node/smp2p/IPA match ours; `violet-vbat.c` is a battery-gauge driver (NOT a WLFW tool); its patches 0010/0015 act after the handshake. Qualcomm's qcom-deb-images issue #667
  (RB1, WCN3950, kernel 7.2) shows the same `capability req rejected: 119` intermittently (1 in 100), open, no cause.
- **BLUETOOTH A/B TEST (2026-11-27): the WCN3990 does not answer on its own UART either, so the 119 is a chip-level problem, not a WLFW/modem protocol one.**
  BT shares the chip but talks to the AP directly (no modem). Test DTB = repo DTS + `mainline/wip/bt-uart7-test.dtsi`: `qcom,wcn3990-bt` on UART7 (QUP SE7 0xa8c000,
  gpio10-13 func1 = stock `qcom,qup_uart@0xa8c000` / qup13; safe pins), supplies from the PMU node, `qupv3_id_1` enabled. `hci_uart` is blacklisted (`/etc/modprobe.d/bt-test.conf`);
  stock `crbtfw*.tlv`/`crnv*.bin` copied to `/lib/firmware/qca/`. Result every time: `setting up wcn399x` -> `command 0xfc00 tx timeout` -> `Reading QCA version information failed (-110)`,
  3 retries. UART TX works (tx counter rises), rx stays 0 apart from ONE garbage byte right after some power-ons (`Frame reassembly failed (-84)`, typical of the chip's TX line rising).
  Verified IN THE PMIC (regmap 0-01/0-05 LDO STATUS1 0x08 VREG_READY + EN_CTL 0x46 + VSET 0x42) while hci_uart powers the chip: L10a 1800 mV, L1c 1800, L2c 1304, L10c 3312, L9a (cx-mx) 728, all ready.
  Clocks (PMIC 0-00: 0x5400 RF1, 0x5500 RF2, 0x5600 RF3, 0x5300 LN_BB3; EN_CTL 0x46, STATUS1 0x08): RF2 runs even unvoted (status 0xc0 = pin/other-master), RF3/LN_BB3 are off.
  Tried with no change: RF_CLK2 as the PMU `clocks`; RF_CLK3, LN_BB_CLK2/3 voted on (mainline qcs615 clk-rpmh lacks RF_CLK3, so via the test module `mainline/wip/rpmhvote/`,
  `echo rfclka3=1 > /sys/module/rpmhvote/parameters/vote`; VRM clock enable is at cmd-db addr **+4**); L9a always-on 640 mV; L10c 3.312 V; stock UART biases. cmd-db has lnbclka1-3, rfclka1-3.
  So: rails on, clocks on, UART path right, chip silent. Remaining suspects are board-level things not in our DTS (an enable/strap line or load switch, e.g. a PMIC GPIO) or chip state.
  **Best next step: the same BT power-on on slot A (downstream 4.14, its own bt_power driver: power via /dev/btpower ioctl, raw HCI 0xfc00 on /dev/ttyHS1 at 115200).** If it answers there,
  dump TLMM + PMIC GPIO + PMIC LDO/clock registers there with BT on and diff against mainline: whatever differs is what both BT and Wi-Fi are missing.
  **SW_CTRL found: TLMM gpio102** (`qca,bt-sw-ctrl-gpio = <&tlmm 102 0>` in the NetErnels sunny DTB; input from the chip). With L10a NOT always-on (test DTB `bt-t10`):
  gpio102 reads low with the chip off and goes high within 100 ms of the pwrseq power-up, i.e. the chip's PMU/IO really come up; still no UART answer after that clean
  full power cycle, so a latched chip state is ruled out. (With L10a always-on, gpio102 stays high all the time.) Could go into the PMU node as `swctrl-gpios` (driver ignores it for wcn3990).
  Checked and identical to ours / nothing new: stock + NetErnels + fiqri19102002/android_kernel_xiaomi_mojito Bluetooth node (only L1c/L2c/L10c, current level 1, no GPIO, no clock),
  downstream `bluetooth-power.c` (rails only), AlphaDroid device tree (standard rfkill/btpower/cnss-daemon), PMIC GPIOs (stock pinctrl only vol-up/PWM/camera; none output-high live;
  PM6150 gpio9/10 are in func1 live, unexplained), stock fixed regulators (cameras + dummy), PMIC clkdivs (audio MCLK only). GENI UART clock 7.3728 MHz, no baud errors.
  **Manual UART bring-up (2026-11-27), no Bluetooth driver:** DTB = repo DTS minus PMU/wifi nodes + `mainline/wip/wcn-manual-test.dtsi` (each WCN rail as a `regulator-output`,
  UART7 as plain /dev/ttyHS1); `userspace-consumer.c` built as a module with the RPMh "unknown state" check removed (RPMh regulators return -EINVAL before the first vote).
  `mainline/wip/wcnuart.py` powers L10a/L1c/L2c/L10c(/L9a) by hand and tries 12 start-ups: mainline (0xC0@2400, 0xFC@115200), 0xFC@2400, no off pulse, no pulses, +cx-mx,
  RTS/CTS, 500 ms after the pulse, command at 3 Mbaud, HCI reset, slow rail ramp. **All: no reply, CTS never asserted.** Turning the rails off from Linux turns L1c/L2c/L10c off
  in the PMIC, but L10a and L9a stay on (another RPMh master, probably the modem, votes them once used), so SW_CTRL stays high after the first trial; that matches stock (L10a always on).
  **Cold-start repeat (one variant per reboot, `COLD=1` refuses a trial unless gpio102 reads low first):** A, B (0xFC@2400), D, F (+cx-mx), G (RTS/CTS), H, L all started from a true
  cold chip (sw_ctrl L->H) and all got no reply, CTS never asserted. (I, C not repeated cold.) ~7 quick reboots in a row tripped the ABL boot counter (phone stopped in fastboot;
  `fastboot set_active b` fixed it), so space reboots or re-arm the slot. Stock msm_geni_serial.c has no WCN-specific wake byte/baud (only PM-vote ioctls, a host wake-up byte, loopback).
  Conclusion: rails, clocks (RF1/RF2/RF3/LN_BB2/3), UART pins and every reasonable pulse/baud sequence are ruled out; the chip's PMU comes up but its BT/WLAN core never boots.
  Phone state after the tests: boot_b = r21 kernel + the `wcn-manual-test` DTB (no wifi/PMU node, L10a not always-on), harmless (hci_uart and ath10k_snoc blacklisted). Flash `bt-t3`/repo DTB to restore L10a always-on.
- **STOCK MIUI REFERENCE (2026-11-27, rooted with Magisk; raw dumps are private in ~/.claude-work/pmos-mojito/android-dump-2026-11-27/, NOT in the repo):**
  - **The chip is a WCN3950, not a WCN3990.** BT ROM answer under Android: SoC version 0x40070120, product ID 0x0f, ROM build 0x0102, patch 0x0001; the HAL loads
    `cmbtfw12.tlv` + `cmnv12.bin` ("cm" = WCN3950). The stock DT says `qca,wcn3990` only because the downstream drivers treat the family alike. Mainline BT must be
    `qcom,wcn3950-bt` with `qca/cmbtfw12.tlv` / `qca/cmnv12.bin` (we had copied the `cr*` WCN3990 files). Fits the `wcn3950_rfa_*` strings in wlanmdsp and the RB1 (WCN3950) 119 report.
  - The Android BT HAL start-up is byte-for-byte what mainline hci_qca does (0xC0 @2400, reopen @115200, 0xFC, reopen with RTS/CTS, EDL version cmd 01 00 fc 01 19 ~125 ms later);
    there the chip answers in 5 ms. So the mainline BT silence is NOT the UART sequence.
  - **On Android the WCN rails never switch off:** with BT and Wi-Fi both off, L1c/L2c/L10c/L10a/L9a stay enabled (2 users each: icnss + bt_power) and `wlan` stays loaded.
    icnss + the modem WLAN firmware bring the chip up at boot and keep it up; BT talks to an already-running chip. Working hypothesis: the WLAN platform init (the cap request,
    which enables the RF chip's XO over WSI) is what starts the WCN3950 core, so the 119 failure also explains BT. UNPROVEN, but consistent with every mainline test.
  - Android WLAN boot: wlan_pd up 14.89 s -> icnss QMI connected 14.897 -> cnss-daemon (2nd WLFW client) reads cal files and downloads **`regdb.bin` then `bdf_gl.bin`** at
    14.951/14.955 -> `WLAN FW is ready` 17.28 s. **`bdf_gl.bin` differs from `bdwlan.bin`** (our board.bin); wlanmdsp.mbn is identical to ours. Files are in
    `/vendor/firmware_mnt/image` (copies in the private dump, files/wlanfw/).
  - Rail modes on Android: L1c, L2c, L10c, L9a = LPM (`idle`), L10a/L11a = HPM (`fast`); mainline uses HPM/auto. L10a also feeds the WCD937x codec.
  - **Live trace of the Android WLAN bring-up** (Magisk post-fs-data script re-arms tracefs after init; trace in the private dump, trace/wlanboot-trace.txt):
    QMI server up 12.1895 s -> icnss enables pm6150_l9 640 mV, pm6150l_l1 1.8 V, pm6150l_l2 1.304 V, pm6150l_l10 3.312 V in that order (12.1895-12.1944, ~1 ms each); per rail
    RPMh writes voltage (addr+0), **mode = 4 (addr+8; PMIC5 LDO mode 4 = LPM)**, enable (addr+4). RPMh addrs: ldoa9 0x41b00, ldoc1 0x42200, ldoc2 0x40700, ldoc10 0x41800.
    Then two SCM 0x42000c16 (hyp assign, MSA) at 12.1976/12.1998. cnss-daemon BDF regdb.bin 12.2529, bdf_gl.bin 12.2580. Nothing else WLAN-related from the AP
    (no GPIO, no clock, no RF-clock vote) until `WLAN FW is ready` at 14.8188, when icnss drops and re-votes the rails. NOTE the rails come on only AFTER the WLFW server
    appears (the modem's wlan_pd is already running); on mainline the rails were on before the modem booted.
  - **Next mainline Wi-Fi tests, in order:** (1) ath10k downloads `regdb.bin` + `bdf_gl.bin` BEFORE the first cap request (never tested: wip/0017 only retried cap after
    a failed one, which the firmware never answers); (2) WCN rails in LPM (`regulator-initial-mode = <RPMH_REGULATOR_MODE_LPM>`); (3) then BT as `qcom,wcn3950-bt` with cm* firmware.
  - No debugfs in the MIUI kernel; tracefs works (regulator/clk/gpio/rpmh/spmi/scm/msm_bus events), but Android init stops a boot-time trace at ~3.5 s, before icnss.
    The dumps also cover the live DTB (`fdt.dtb`), kernel config, sensors/registry, audio/mixer/tinymix, fingerprint, overlays (auto-brightness), battery/charger,
    CPU/cpufreq/idle/thermal, touch/tap-to-wake, display, USB (gadget configfs, DWC3/PHY) and persist.
- **ANDROID-PARITY TESTS ON MAINLINE (2026-11-27, after the MIUI reference), all still `capability req rejected: 119` ~200 ms after the request:**
  (A) Wi-Fi node on direct rails like stock icnss (`mainline/wip/wifi-lpm-test.dtsi`: no PMU node, no ch1, L9a 640 mV, L10c 3.312 V, L1c/L2c/L10c/L9a
  `regulator-initial-mode` LPM; PMIC confirms mode 0x04 = LPM and all enabled), rails switched on by ath10k only after the WLFW service exists (like Android);
  (B) `mainline/wip/0019` (`pre_bdf=1`): the firmware REFUSES regdb.bin and board data before the capability request (QMI error 90, incompatible state), so
  (B2) `pre_bdf=3` (only the calibration report before cap, like cnss-daemon's cal table at +7 ms): also refused (-22); the cap request is the gate, no WLFW step is accepted before it.
  on Android the cap request must already succeed within ~60 ms of QMI connect (cnss-daemon's BDF at +63 ms); (C) every PMIC RF/LN clock voted on via rpmhvote
  (RF1, RF2, RF3, LN_BB2, LN_BB3 all EN=0x80 / OK) during the WLAN restarts. The Android trace shows nothing else from the AP in that window (only the 4 rail
  votes, 2x SCM hyp-assign, IRQs from smp2p/glink). RB1 (WCN3950, qrb2210-rb1.dts, works upstream) uses plain PMU rails and no clock either.
  (D) **firmware-package mismatch found and ruled out:** the pmOS `firmware-xiaomi-mojito` package (AbdulkareemQasem blobs) ships a DIFFERENT modem
  build than this phone's ROM (V14.0.9.0: nearly all modem.b* segments, modem.mdt, wlanmdsp.mbn, adsp.mdt, cdsp.mdt differ). Replaced modem.* + wlanmdsp.mbn
  with the ROM's own (stock/extract/fwall; package copies kept in /lib/firmware/postmarketos-pkg-backup/): the modem and LTE (rmnet_ipa0) work, still 119.
  The phone now runs the ROM's modem + wlanmdsp (an `apk upgrade` of the firmware package would put the package ones back).
  (E) **modem file requests (tqftpserv -d, rmtfs -v at boot; logs in the private dir modem-requests-pmos/):** the modem asks for
  /readwrite/server_check.txt (write), /readwrite/{mcfg,lctoem}.tmp (r/w), /readwrite/ota_firewall/ruleset (missing, rejected),
  /readonly/vendor/firmware_mnt/image/wlanmdsp.mbn (3x) and **/readonly/firmware/image/modem_pr/mcfg/configs/mcfg_{hw,sw}/mbn_{hw,sw}.dig, which pmOS
  REJECTED (no modem_pr tree)**; rmtfs serves modem_fs1/fs2/fsg. Installed the ROM's modem_pr tree (242 files, from NON-HLOS.bin image/modem_pr via mcopy)
  into /lib/firmware/postmarketos/modem_pr: both digests are now served, the modem reads no MBN after them (the EFS from Android already holds the
  matching MCFG), and Wi-Fi is still 119. So MCFG is not the cause; modem_pr stays installed for parity.
  (F) **TrustZone MSA assign compared: identical.** Android trace: 2x SCM 0x42000c16 (SIP svc 0x0c MP, cmd 0x16 = MP_ASSIGN, arginfo 0x1117 = 7 args
  RO/VAL/RO/VAL/RO/VAL/VAL, same as mainline qcom_scm_assign_mem), one per MSA region. Stock icnss (fiqri tree icnss.c msa_perm_list/secure_list) and
  ath10k qmi.c map the same way: HLOS(0x3) -> MSS_MSA(0xF) RW + WLAN(0x18) RW, plus WLAN_CE(0x19) RW for non-secure regions; same VMID/PERM values
  (secure_buffer.h vs dt-bindings/firmware/qcom,scm.h); same point in the sequence (after msa_info, before msa_ready). Our assigns succeed.
  (G) **Service-registry (PDR) listener for wlan_pd, like icnss: no change.** Android's kernel receives and ACKs "Indication received from
  msm/modem/wlan_pd, state 0x1fffffff, trans-id 1" 4 ms before icnss's QMI connect; mainline ath10k has no PDR client at all. Test module
  `mainline/wip/wlanpdr/` (pdr_add_lookup("wlan/fw", "msm/modem/wlan_pd"), loaded at boot via /etc/modules before the modem starts): UNINIT at modem
  boot, UP indication trans-id 1 received and ACKed, DOWN/UP on every crash also ACKed - and the cap request still gets 119. The module stays installed
  (/lib/modules/7.4.0-rc4-sm6150/updates/wlanpdr.ko, listed in /etc/modules); a real ath10k fix will want PDR anyway.
  **Not yet compared against MIUI (only the pmOS side exists):** the QRTR/QMI service list (pmOS: `qrtr-lookup`) and the modem's tftp/rmtfs file
  requests (pmOS logs in modem-requests-pmos/; MIUI's early-boot logcat had rotated out of the dumps). Both need a MIUI boot with logcat captured from
  the first second (plus a static aarch64 qrtr-lookup or equivalent). Until then "AP-side parity" covers only what is listed in (A)-(G).
  => The difference is probably on the MODEM side, not in anything the AP drives that was compared above: same wlanmdsp.mbn, but the modem image/config, EFS, or the services the modem talks
  to differ between MIUI and pmOS. Next: compare the QMI/QRTR service list and the modem's tftp/rmtfs file requests under MIUI vs pmOS, and the modem firmware
  files actually loaded (MIUI loads them from /vendor/firmware_mnt, pmOS from /lib/firmware/postmarketos: compare checksums of modem.* and the mcfg/mbn set).
- **Firmware RE of the capability path (2026-11-27, wlanmdsp.mbn 4b1510cc, llvm-objdump-18 recipe above; addresses are absolute):**
  The cap handler's platform init `b01c15b0` returns 1 (-> QMI error 119) at exactly four points: the precondition `b01c1568`; **(A)** CCPM
  `ccpm_ccvs_plat_req` `b0147d50(client, 1, 0)`; **(B)** CCPM WLAN power request `b01478e8(client, 6, 0, 0)`; **(C)** the same with state 7. Between B and C it
  waits 10000 (`b003b4d8(0x2710)`), sets bit 0 of WCSS reg **0xa6750000** and polls it (`b01c2b30(0xa6750000, 1, 1, delay 10, count 10)`, result ignored),
  waits 3000, and optionally runs `b01c2d00` (only if 0xa6750000 bit 0 was already set: polls `[gp+0x13c]+0x22070` for bit 20 with delay 200 x10).
  After C: HW version/chip-id table match at `[gp+0x13c]+0x80000` (miss = assert "Invalid HW variant", not an error reply), then `b014bc38`, `b01c14c0`.
  - `b01c2b30` = generic poll(addr, mask, value, delay, count): 0 on match, -1 after count tries, `b003b4d8(delay)` between tries.
  - `b003b4d8` = busy/timer delay; the delays in this path add up to ~15-20 ms if the unit is us, so the observed ~200 ms has to be spent INSIDE a CCPM call.
  - `b01478e8`: returns 0xc if the client or its manager (`client+0xc`) is NULL; for a type-1 client (`client+4 == 1`) calls `b014a820` and returns success
    only if the global **0xb0300ac0 == 1**. `b0147d50`: returns 0xd ("CCPM not initialized", plain string at 0xb02a4381) if byte **0xb03200a0** is 0, otherwise
    builds a request from the state table at 0xb031a740 and calls `b01479a4` under a lock (`b02122e8`/`b02122f0`).
  - **`b014ada0` is the CCPM client-init routine** (its tail writes 0xb0300ac0 = 1 at 0xb014b028): loops 7 table entries (`b0147370`), clears bit 0 of
    **0xa67c0000**, waits 200, then `b0145e40`, `b0145db0`, `b0147550`, `b0146400` (returns 5 = early exit) ... (The earlier claim that this init
    "never completes" on mainline was wrong; see the correction below.)
  - F3 log text is QShrink-hashed (descriptors {line|ssid, mask, hash}), but assert strings and many CCPM log strings are plain
    (e.g. "platform_helium_init.c:Invalid HW variant", "ccpm_rf_xo_enable: ...").
- **CORRECTION and new lead (2026-11-27, static reading only, nothing run on the phone): the RF crystal enable probably fails.**
  - The flag **0xb0300ac0 is 1 in the firmware image** (data segment). One direct read (0xb0147964) and one direct write (0xb014b028) were found;
    pointer-based writes are not excluded. That write stores 1 when client-init completes and **0 on the early exit** at 0xb014ae38, taken when
    `b0146400` returns 5. So B/C do not need the init to have run; they fail if it ran and took that exit.
  - `b0146400` is **`ccpm_rf_xo_enable`** (its log strings). It returns 5 when "step 12: Wait WSI_CMD.RF_CMD_IP bit 31 to be 0"
    (register 0xfc0800e0 in the firmware's address space) is still busy after 5 retries; the success path returns the xo_type. It also logs
    WLAN_SW_CTRL_GPIO before and after the XO command.
  - A (`b0147d50` -> `b01479a4` -> `b014a8c0`) returns 0 on every path read once CCPM is initialised. It applies resource mask 0x802 (ids 1, 11).
  - **Inference (not proven):** the 119 is exit B or C after `ccpm_rf_xo_enable` failed. This would fit the silent Bluetooth core (radio chip not answering).
  - CCPM resources (table 0xb03010c8, 0x18 each; id = byte at +4, subtype = next byte): 1 /icb/arbiter (sub 1), 2 wcn_ant_switch, 3 cpu latency,
    4 wcn_core, 6 wcn_pa, 7 wcn_pa_2, 8 wcss, 11 ccpm_mca (sub 3), 12 **adrastea_clk** (sub 6), 13 /icb/alc (sub 7), 14, 15, 17.
    Callbacks are installed by subtype (jump table 0xb02a4698). Only sub 6 gets node+0x38 = `b0148bdc` (value == 1 -> `b014ada0`).
  - `b01478e8` -> `b014a820` -> walker `b0147670` (holds 0xb01476d8). The walker filters by resource-id bit (state 6: mask 5; state 7: mask 2) and skips
    nodes without a callback at +0x34 (only subs 1, 3, 7 have one). So B appears to do nothing (id 0 is not in that table, id 2 has no such callback);
    C reaches /icb/arbiter, which makes C the likelier failing exit. Resources are then applied by mask: `b014787c` -> `b0149070` / `b0149110`.
  - **Open (weak link):** what puts bit 12 (adrastea_clk) into an apply mask with value 1 on this path. If client-init never runs, B and C should
    succeed. Also open: whether the delays explain ~200 ms (step 12 alone is 5 x 6 x `b003b4d8(1000)`, ~30 ms if the unit is us).
  - **Next:** (1) on the phone, sample TLMM gpio102 (SW_CTRL) rapidly across the capability request; a change or none is a clue, not proof;
    (2) trace the adrastea_clk apply path and the WSI test routine ("ccpm_rfactrl_wsi_test").
- **Still unknown:** what the modem's WLAN power-up waits ~200 ms for. Needs the modem's own log or a different angle (e.g. memory capture before `qcom_pas_shutdown`, risky).
### Wi-Fi: second session (2026-11-27) - every test below still ends in `capability req rejected: 119`

Tools and device-tree fragments: `mainline/wip/wlan-re/`.

**New facts (measured on hardware):**
- During the capability request the **modem itself** enables L1c, L2c, L10c (+5 ms after MSA ready) and L9a (+16 ms); SW_CTRL (gpio102) rises
  +17..27 ms; L1c/L2c/L9a go off again at the rejection (+200 ms on the first attempt after boot, ~400-425 ms later). The chip's PMU side reacts.
- No file request reaches `tqftpserv`/`rmtfs` between driver load and the first rejection (both stayed asleep): not a missing board file there.
- mainline ath10k powers regulators only in `hif_power_up` (after FW ready), so the earlier "Android power order" test (A) never did that.
  L10a being on does not by itself hold SW_CTRL high (it read low with L10a on).

**Tested, no change:** L10a not always-on with the PMU node; radio powered before the first WLFW request, plus 100/500 ms waits (`early-power.patch`);
**kernel 7.2.10** with our patches (same version as the violet port); violet-style direct supplies and always-on/LPM rails (mojito stock voltage
ranges); modem stop/start loop like violet (4 restarts, mobile data driver blocked; the modem survives restarts without IPA); **clean-room** run:
Wi-Fi node like sm7125-mainline `miatoll`, `msa-fixed-perm`, no gpio98 pinctrl, no PMU node, stock driver, `rmtfs` pmOS default, no `wlanpdr`.
Slot A (downstream) Bluetooth power-on through `bt_power`: no reply, CTS never asserted (inconclusive: stock starts the chip through Wi-Fi first).
Do not read `/sys/kernel/debug/gpio` on slot A from that probe: the phone reset (gone after removing the read).

**Public reports of the same error, no published software fix found:** qualcomm-linux/qcom-deb-images#667 (RB1, WCN3950, intermittent),
arduino/arduino-deb-images#23 (UNO Q, every boot, BT silent too). On an Arduino forum thread a board replacement fixed it. This phone's radios work
under stock MIUI, so the hardware is fine.

**Captured later the same day (see the top section); at the time of this session still missing:** QMI message contents including the successful capability exchange, the QRTR service
list from boot, the modem's file requests from boot, logcat from the first second. Stock kernel 4.14.190 has no kprobes, syscall tracing or IPC logging
and forces module signatures, so the plan is a rebuilt kernel (Xiaomi `mojito-r-oss`, stock config) with `qrtrcap/` added. Not yet built or proven.

- sm7125-mainline (Redmi Note 9 Pro, same PMICs, same `wlan_mem` 0x93900000, Wi-Fi works, unpatched ath10k): 2 MB MSA +
  `qcom,msa-fixed-perm` + ch1 = L11c. With that config here: boots fine, MSA permission errors gone, still 119. The repo DTS now uses it.
- Stock node also has `qcom,smmu-s1-bypass` and iova ranges (matters for data path later, not for the handshake).

### Phosh: display corners and the camera cutout (`mainline/gmobile/`)

Phosh (`shell-layout 'device'`) takes corners and cutouts from gmobile's built-in panel data, matched by the DT compatible, not from
GSettings. gmobile 0.7.5 had no `xiaomi,mojito`, so the clock sat under the punch hole and icons ran into the corners.
`mainline/gmobile/` is Alpine's gmobile 0.7.5 + `xiaomi,mojito.json`: 1080x2400, 67x149 mm, corner radius 119 px, camera circle
centre (540,52) radius 37, from the stock overlay (`config_mainBuiltInDisplayCutout` "M 0,0 H -37 V 93 H 37 V 0 H 0 Z",
`rounded_corner_radius` 119px, via the LineageOS mojito tree). Build with `pmbootstrap build --arch aarch64 gmobile` (without
`--arch` it builds x86_64), install `gmobile` + `gmobile-udev` r1, restart Phosh. Upstream candidate for gmobile.

### Camera (reference from stock MIUI, 2026-11-27; traces in the private dump, camera/)

Sensors on this unit (`persist.vendor.camera.mi.module.info*`): wide **Sony IMX582**, ultra-wide **Sony IMX355**, macro **GalaxyCore GC02M1**, depth **OmniVision OV02B1B**,
front **OmniVision OV13B10** (rear vendor id 07, front 01; the vendor also ships OFilm/Sunny/Semco module variants). Sensor detection is in userspace CamX; CCI at 0xac4a000.
Power-up traced with tracefs while opening the camera app:
- rear wide (camera 0): TLMM gpio47 (reset) low -> `camera_vana0_ldo` (PM6150L GPIO 9 switched) -> pm6150_l13 1.8 V -> titan_top_gdsc -> **MCLK0** -> gpio47 high -> CCI clocks
  -> pm6150_l19 2.8 V (actuator) -> CSID/IFE/IPE.
- front (camera 1): gpio38 (reset) low, gpio94 and gpio121 low -> pm6150_l13 1.8 V -> gpio94 high, gpio121 low, gpio38 high -> **MCLK2**.
Mainline needs camss for SM6150/QCS615 plus sensor drivers (imx355, ov13b10 exist upstream; imx582 / gc02m1 / ov02b1b do not).

### Audio, haptics, flash, charger, proximity (reference from stock MIUI, 2026-11-27; private dump, audio/ haptics/ flash/ charger/)

- Sound card `sm6150-idp-snd-card`, mixer file **`mixer_paths_idp.xml`** (copy + ftm_test_config* in the private dump, audio/cfg/). Media playback trace (ASoC DAPM + I2C):
  speaker = RX_MACRO RX1 -> RX INT2 -> WCD937x **AUX_OUT** -> AUX PGA -> **AW87xxx "SPK" at i2c-2 (QUP i2c3) 0x58**; earpiece ("handset" path) = RX0 -> RX INT0 -> HPHL/RDAC3
  -> **EAR** -> **AW87xxx "Rcv" at 0x5b**; Android powers BOTH amps for media. Full amp init register sequences captured (22 writes to 0x58, 39 to 0x5b) in audio/trace-audio-clean.txt;
  tinymix during playback in audio/tinymix-playing.txt.
- Mics: `amic1` = ADC1 (SWR_MIC, TX DEC0); `amic2`/`amic3` = ADC2 with ADC2 MUX INP2/INP3; `handset-mic` / `dmic-endfire` = ADC1 + ADC2.
- **Proximity is ultrasonic** (Elliptic Labs virtual sensor): `ultrasound-proximity*` mixer paths drive the earpiece and a mic. There is no proximity chip to look for.
- Haptics: PM6150L haptics at SPMI sid 5 **0xbc00** (writes 0xbc41=07, 0xbc45=01, 0xbc44=b3, 0xbc47=01, 0xbc46=84 for an 800 ms buzz); TLMM gpio112 goes high too.
- Torch: PM6150L flash at SPMI sid 5 **0xd300** (0xd343=07, 0xd340=13, 0xd346=80, 0xd34c=01). (0x31xx/0x35xx writes in both traces are ADC/thermal noise.)
- Charger (unplug/replug trace, charger/): JEITA FCC 6 A, **float voltage 4.47 V**, termination -350 mA, QG full capacity 4539 mAh; vbus ~5.0 V on the PC port.
## Packaging the v2 boot image

`mainline/mk-bootimg-v2.sh <Image> <dtb> <ramdisk> [out.img]` with `PMOS_BOOT_UUID`/`PMOS_ROOT_UUID` set
(read them from the phone's `/proc/cmdline`; they change with every `pmbootstrap install`). Inputs:

- `Image`, `dtb`: from the kernel package (`/boot/Image`, `/boot/dtbs/qcom/sm6150-xiaomi-mojito.dtb`).
- `ramdisk`: for now the **downstream** pmOS initramfs, unpacked from the downstream `vendor_boot.img`
  (`unpack_bootimg --boot_img vendor_boot.img --out vb` gives `vb/vendor_ramdisk`). It is kernel-agnostic
  (gzip, contains the 4K loop hook); the mainline drivers it needs are built in. No mainline device package yet.
- `MKBOOTIMG`: android-tools' `mkbootimg` (a Python script; the copy inside pmbootstrap's rootfs chroot works
  with `python3`).

`vendor_boot_b` still holds an older v3 mainline image; with a v2 `boot` image ABL is expected to ignore it
(not verified).

## Layout

| Path | What |
|---|---|
| `downstream/device-xiaomi-mojito` | device package (deviceinfo, cmdline, initramfs hook) |
| `downstream/linux-xiaomi-mojito` | 4.14.253 kernel package (xiaomi-sdm678/android_kernel_xiaomi_mojito, branch 11) |
| `downstream/firmware-xiaomi-mojito` | firmware package (blobs from AbdulkareemQasem/Redmi-Note-10) |
| `downstream/shim/noatomic.c` | LD_PRELOAD shim forcing legacy KMS for kmscon |
| `downstream/README.md` | step-by-step notes for the downstream port |
| `mainline/sm6150-xiaomi-mojito.dts` | board device tree (authoritative copy) |
| `mainline/linux-postmarketos-qcom-sm6150` | mainline kernel package + patches |
| `mainline/mk-bootimg-v2.sh` | packs the header v2 boot.img (see above) |
| `mainline/build-dtb.sh` | compiles the DTS to a DTB without rebuilding the kernel package (fast loop) |
| `mainline/dummy-overlay.dts` | the dtbo experiment (ABL rejected it) |
| `mainline/NOTES.md` | facts pulled from the stock device tree |
| `mainline/gmobile/` | gmobile 0.7.5 + the Redmi Note 10 display panel (corners, camera cutout) for Phosh |
| `tools/install-modem-userspace.sh` | installs rmtfs/tqftpserv/qrtr/ModemManager on the phone from the PC, enables them, optional APN |
| `tools/` | lpunpack.py (super.img), hwprobe.sh, evrec.py, vtype.py, gltest.py (off-screen OpenGL ES test on the render node), run-phosh.sh (Phosh as root, no lock-screen password works), run-phosh-user.sh (Phosh as `user` with a PAM service, takes a duration), i2cprobe.py (probe the touch I2C bus), i2c3probe.py (read-only probe of the chips on i2c3) |
