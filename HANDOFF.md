# Handoff: postmarketOS on the Redmi Note 10 (mojito/sunny)

For the next agent picking this up. Read this whole file before touching the phone.
State as of 2026-11-26.

## Goal

Run the user's **Finder** shell on this phone. Finder is a Qt 6.9+ QML shell on **KWin 6 (Wayland)** with
LayerShellQt and QtQuick.Effects (it lives in the user's private `finderlinux` repo). It needs GPU
acceleration with GBM + EGL, which this phone can only get from a **mainline kernel** (freedreno). That is
why there are two ports here:

- `downstream/`: Xiaomi's 4.14 kernel. **Works today** (boots, SSH, text console on screen). Stays on slot A.
- `mainline/`: Linux 7.4-rc4 + an SM6150 device tree. **Does not boot yet.** Being tested on slot B.

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

### Boot attempts so far (all on slot B, all fell back to fastboot with only the Mi logo on screen)

| Packaging | Result |
|---|---|
| v3, DTB board-id `0 0`, `dtbo_b` erased | fastboot after ~4 s (ABL refused) |
| v3, empty overlay (no fragments) in `dtbo_b` | fastboot after ~12 s |
| v3, wider load addresses (kernel 0x10008000, dtb 0x13f00000, ramdisk 0x14000000) | ~12 s |
| v3, overlay with a fragment (`dummy-overlay.dts`) | ~12 s |
| v3, stock `dtbo` | ~12 s |
| **Control:** downstream kernel + DTB with the same v3 packaging and stock `dtbo` | **boots fine** |
| Control with the dummy dtbo instead | ~12 s |
| v2 `boot.img` (raw Image + initramfs + DTB with board-id `0x22`, `__symbols__`), `dtbo_b` erased | **result not recorded** (the session ended while watching) |

pstore came back empty after every failure, but it was also empty after downstream crashes, so this phone
may clear that RAM on reset. That proves nothing either way.

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

1. Check the outcome of the v2 + erased-dtbo test (re-run it: flash `boot_b`, `fastboot erase dtbo_b`,
   `fastboot set_active b`, reboot, watch `lsusb` for `18d1:d001` = pmOS initramfs USB gadget).
2. Rebuild the kernel package (pkgrel 1 adds patches 0002/0003, `QCOM_WDT=y`, `EFI_ZBOOT` off so a raw
   `Image` is produced and installed as `/boot/Image`, `LOCALVERSION=-sm6150`). That build was interrupted.
   The earlier build used `EFI_ZBOOT`; ABL needs the raw `Image` (unwrap a zboot image by reading the payload
   offset/size at bytes 8-15 and decompressing the zstd payload).
3. If it still resets early, diff our DTS against violet's `dt/violet-sm6150.dts` (same SoC: compare
   reserved-memory, `protected-clocks`, disabled nodes) and their kernel config.
4. Once it boots: SSH, then DSI panel driver (generate from the stock panel node with
   linux-mdss-dsi-panel-driver-generator), GPU with `a612_zap.*`/`a612_rgmu.bin`/`a630_sqe.fw`, Mesa,
   KWin 6, Finder. Then touch, charging (PM6150 SMB5/QG is weak upstream), audio, Wi-Fi, modem.

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
| `mainline/dummy-overlay.dts` | the dtbo experiment (ABL rejected it) |
| `mainline/NOTES.md` | facts pulled from the stock device tree |
| `tools/` | lpunpack.py (super.img), hwprobe.sh, evrec.py, vtype.py |
