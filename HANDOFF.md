# Handoff: postmarketOS on the Redmi Note 10 (mojito/sunny)

For the next agent picking this up. Read this whole file before touching the phone.
State as of 2026-11-26.

## Goal

Run the user's **Finder** shell on this phone. Finder is a Qt 6.9+ QML shell on **KWin 6 (Wayland)** with
LayerShellQt and QtQuick.Effects (it lives in the user's private `finderlinux` repo). It needs GPU
acceleration with GBM + EGL, which this phone can only get from a **mainline kernel** (freedreno). That is
why there are two ports here:

- `downstream/`: Xiaomi's 4.14 kernel. **Works today** (boots, SSH, text console on screen). Stays on slot A.
- `mainline/`: Linux 7.4-rc4 + an SM6150 device tree. **Boots to SSH** (since 2026-11-26) with every GPIO
  reserved; the splash display and login work, and only a few pins can be valid. Developed on slot B.

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
and simpledrm all probe; the log has no oops; the splash display and the kmscon login work; and the **Adreno 612
renders** (freedreno, OpenGL ES 3.2, off-screen test passes). Open: a real display driver (DPU/DSI/panel), touch,
audio, Wi-Fi, modem, charging. Eight GPIOs are secure-world owned and reserved in the DTS (see TLMM).

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

### Display: the bootloader splash now stays up (simpledrm), login visible

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
2. **Display** through the real stack (the splash already works, see above): DPU, DSI host and PHY, and a DSI panel
   driver (generate it from the stock panel node with linux-mdss-dsi-panel-driver-generator).
3. **Touch: done** (r6, see above). Next, with TLMM working and any pin outside gpio0-3 / gpio6-9 usable: panel reset/TE,
   then the ADSP remoteproc on its own build (it is the audio/modem/Wi-Fi prerequisite and the likeliest to hang the boot,
   like the secure-world pins did), then charging (smb5 + bq2597x have no mainline match), Wi-Fi, audio, and finally KWin 6
   and Finder.
4. The kernel package (`7.4_rc4-r6`): patches 0001-0004, `QCOM_WDT=y`, `EFI_ZBOOT` off, raw `Image` installed as
   `/boot/Image`, `LOCALVERSION=-sm6150`, and `DRM_MSM=m` (the modules are in the package). Its DTB has board-id `0 0`; `mk-bootimg-v2.sh` patches in
   `0x22` when packing. Patch 0001 is regenerated from `mainline/sm6150-xiaomi-mojito.dts`; for DTS-only
   changes use `build-dtb.sh` instead of rebuilding the package.

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
| `tools/` | lpunpack.py (super.img), hwprobe.sh, evrec.py, vtype.py, gltest.py (off-screen OpenGL ES test on the render node), run-phosh.sh (Phosh as root, no lock-screen password works), run-phosh-user.sh (Phosh as `user` with a PAM service, takes a duration), i2cprobe.py (probe the touch I2C bus), i2c3probe.py (read-only probe of the chips on i2c3) |
