# Handoff: postmarketOS on the Redmi Note 10 (mojito / sunny)

State as of 2026-11-27, mainline Linux 7.4-rc4, kernel package `pkgrel=29`. Read this file first.
Older detail (how each thing was found, dead ends, reverse engineering): [`docs/HANDOFF-history.md`](docs/HANDOFF-history.md).

## Status

| Area | State |
|---|---|
| Boot, display (DPU/DSI/panel), brightness with smooth dimming, touch, GPU, Phosh | works |
| Wi-Fi (~18 s after boot), Bluetooth (~19 s) | works |
| Mobile data (LTE) | works; calls not set up |
| Accelerometer, light sensor, compass | works |
| Speakers: left = earpiece (top), right = main speaker (bottom) | works |
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
3. **CPU capped at 1.59 / 1.9 GHz.** Every boot logs `Voltage update failed` for the OPPs up to 1.71 GHz (cpu0) and
   2.21 GHz (cpu6).
4. PC-port charging (add module parameters to the SMB5 driver to try register settings live; a bad setting can suspend USBIN
   until a replug). Stock leaves `0x1366 = 0x03` on an SDP; the driver writes `0x02`.
5. Modem appears to ModemManager only ~30 s after boot.
6. One boot hung at udev "Waiting for uevents" (cause unknown).
7. Calls (q6voiced and surya's q6voice patches), mic noise (retest in a quiet room; speaker amps ruled out), second mic
   (needs `qcom,tx-channel-mapping` and probably driver work), speaker amps stay powered while idle.

## Workarounds still in place (the user wants as few as possible; fix causes, record any new shortcut)

| Workaround | Proper fix |
|---|---|
| No device package; files and packages installed by hand; initramfs borrowed from the downstream port | a mainline device package (agreed: private repo `mojito-device`, not created yet) |
| `clk_ignore_unused` on the command line | claim the running clocks (audit: display PLLs/`disp_cc`, `ipa`, LPASS ids, rf/bb clocks, UFS/USB refs) |
| Wi-Fi and Bluetooth loaded by script, modules blacklisted | proper ordering in the drivers/services |
| "No DSP request for 3 s" means the sensor PD is served | a real ready notification |
| Plain wallpaper (the default JPEG XL one locks up the phone at login) | find why glycin-jxl exhausts memory into a hard lock-up |
| `aw87xxx-seq` amplifier driver replaying vendor register tables | load the vendor profiles in a mainline Awinic driver |
| SMMU identity domain (0006), stopping the bootloader timing engine (0007) | upstreamable fixes |
| hexagonrpcd patch not upstream | send it |

Already removed: `pd_ignore_unused`, discarded sensor-registry writes, log-line readiness guessing, numeric `RX HPH Mode`.

## The phone (slot B; slot A / stock kept apart)

- Boot image: header v2 (`mainline/mk-bootimg-v2.sh`), `dtbo_b` erased. `qbootctl` marks each boot successful.
- Rootfs grown by hand to the full userdata partition (a clean install does not do this yet).
- Packages added by hand: `bootmac hexagonrpcd i2c-tools libgpiod bluez-btmgmt wlr-randr postmarketos-ui-phosh gmobile
  qbootctl qbootctl-openrc swclock-offset swclock-offset-openrc`, modem userspace (`tools/install-modem-userspace.sh`).
- Firmware: private package `firmware-xiaomi-mojito-mainline` (repo `258ryan/mojito-firmware`); EFS images are in no repo.
- `mainline/rootfs/` copied by hand: services `mojito-wifi` and `mojito-sensors` (default runlevel), `modprobe.d`
  blacklist, UCM files, gmobile panel overlay + profile script, glib wallpaper override (then `glib-compile-schemas`),
  greeter `client.conf` (`autospawn = no`, owned by greetd). The accelerometer udev rule is **not** active on the phone.
- `mainline/hexagonrpc/` build installed as `/usr/local/bin/hexagonrpcd-mojito`; state in `/var/lib/hexagonrpcd/mojito`.
- User `user` is in groups `audio video input`. PulseAudio (not PipeWire) drives the sound card.

## Workflow

The user runs the kernel build; the agent flashes and diagnoses. Ask for the SSH password each session; never store it.

1. DTS change: `python3 tools/regen-dts-patch.py`; DTS-only test without a build: `mainline/build-dtb.sh <linux-tree> out.dtb`.
2. Kernel change: add or edit patches, bump `pkgrel`, update `sha512sums`, then `rsync -a
   mainline/linux-postmarketos-qcom-sm6150/ <pmaports>/device/testing/linux-postmarketos-qcom-sm6150/`.
3. `pmbootstrap build linux-postmarketos-qcom-sm6150` (~3 min for `.c`-only changes, ~13 min after config/header changes).
4. Unpack the apk (`tar -xzf`). Keep the current boot image as rollback. Get ramdisk and cmdline from it with
   `tools/unpack-boot-v2.py`, then `mk-bootimg-v2.sh Image dtb ramdisk out.img` (`PMOS_BOOT_UUID`, `PMOS_ROOT_UUID`,
   `MKBOOTIMG` = android-tools' `mkbootimg.py`).
5. `tools/install-modules.sh <unpacked apk> <phone ip>` (`SSH_ASKPASS`, `PHONE_PW`). Install matching UCM files too.
6. `fastboot flash boot_b out.img && fastboot set_active b && fastboot reboot`; check `uname -v`.

Testing rules learned: give an audible or visible positive control before asking the user to judge a test (Phosh sound test for
audio); keep tones quiet and short; make trial settings revert themselves; ask before reboots or sleep tests.

## Hazards

- Hang/crash: TLMM pins 0-3 and 6-9; an `mdss` `resets` line; `rmmod msm`; LPASS 0x62b40000; reading the modem carve-out
  (0x8b000000) or `dd` of `modemst*`/`fsg`/`fsc`.
- Do not restart the modem while IPA is up (stalls, never recovers: reboot).
- Large transfers over USB networking can freeze the phone; use Wi-Fi. USB networking sometimes drops while the phone is fine.
- A stuck phone: Power + Volume-down for 10-15 s reaches fastboot. No log survives a reset.
- The speakers have no protection algorithm.
- Live SoundWire debugfs register writes leave the codec's register cache stale; reboot before judging anything after them.
- The clock starts in 1970 until swclock/NTP; meson and similar reject "future" timestamps (`tar -m`).
- `pkill -f pattern` kills the calling shell if its command line contains the pattern.

## Public repository

No firmware, boot images, device dumps, device identifiers, carrier or network details, or passwords. Commit as
`258ryan <20981851+258ryan@users.noreply.github.com>`. The user's standing rule: commit and push whenever something works or is
close to working. Private working files are on the build PC under `~/.claude-work/pmos-mojito/` (audio work, boot images and
rollbacks in `audio-speaker-2026-11-27/`).
