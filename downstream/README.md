# postmarketOS packages for Xiaomi Redmi Note 10 (mojito)

Cleaned-up version of https://github.com/AbdulkareemQasem/Redmi-Note-10.

## Install
    pipx install pmbootstrap
    pmbootstrap init                 # device: xiaomi-mojito (pick any UI, e.g. phosh)
    cp -r device-xiaomi-mojito linux-xiaomi-mojito firmware-xiaomi-mojito \
          "$(pmbootstrap config aports)/device/testing/"
    pmbootstrap init                 # re-run so it picks up the device + nonfree firmware
    pmbootstrap build linux-xiaomi-mojito   # slow; fix compile errors here first
    pmbootstrap install

## Flash (phone in fastboot: Power + Vol-Down)
    pmbootstrap flasher boot         # one-off test boot, nothing written
    pmbootstrap flasher flash_rootfs # writes to userdata
    pmbootstrap flasher flash_kernel # writes to boot

Never erase/flash vendor_boot: it holds the device tree.
Recovery: flash the stock MIUI fastboot ROM with Mi Flash / flash_all.sh.
After editing files: `pmbootstrap checksum <pkgname>`.

## Notes from the first build (2026-11-25)
- Tested phone is "sunny" (M2101K7AG, the NFC-less Redmi Note 10, MIUI 14 / Android 12).
  Same hardware and kernel as mojito.
- Header v3: pmOS writes its own vendor_boot (initramfs + DTB). So the
  "flasher boot" test needs vendor_boot flashed first:
      pmbootstrap flasher flash_kernel   # writes boot + vendor_boot
      pmbootstrap flasher flash_rootfs   # writes userdata
- Prebuilt images from that build: images/boot.img, images/vendor_boot.img
- Bootloader must be unlocked first (Mi Unlock, wipes the phone).

## Working boot (2026-11-25) - fixes that were needed
1. Kernel: clang + gcc6 (only for aarch64 binutils), REPLACE_GCCH=0.
2. Boot header v3: pmOS builds vendor_boot (initramfs + DTB). DTB = concatenated
   kernel-built qcom/*.dtb; dtbo.img built from the kernel's overlays and flashed
   to `dtbo` (Xiaomi's board changes live in sm6150-idp*.dts; must match the DTB).
3. deviceinfo_initfs_compression="gzip" (4.14 can't unpack zstd initramfs).
4. OpenRC, not systemd: `pmbootstrap config service_manager openrc`.
5. Initramfs hook 10-loop-4k-partscan.sh: UFS uses 4096-byte sectors and
   kernels < 5.8 lack LOOP_CONFIGURE, so loop partitions need a rescan.
6. OpenRC `cgroups` service hangs on this kernel; it is removed from the default
   runlevel. After a fresh `pmbootstrap install` (new rootfs) run:
       pmbootstrap chroot -r -- rc-update del cgroups default
   before flashing userdata.
7. No /dev/fb0 (msm SDE driver), so no text console on screen: use SSH over USB:
       ssh user@172.16.42.1     # the password you set with `pmbootstrap install --password`
Flash (fastboot): dtbo, vendor_boot, boot, userdata - see images/.
Known TODO: root fs is only ~870 MB (not grown to fill userdata); haveged crashes.

## Screen: text console via kmscon (2026-11-25)
- msm_drm fbdev init fails ("failed to get buffer obj iova: -22") -> no /dev/fb0.
- Atomic KMS commits are rejected (-22); legacy KMS works (what plymouth uses).
- Fix: kmscon + LD_PRELOAD shim (shim/noatomic.c -> /usr/local/lib/libnoatomic.so)
  that makes drmSetClientCap(ATOMIC/UNIVERSAL_PLANES) fail, so kmscon uses legacy.
- Service /etc/init.d/kmscon-console (default runlevel) runs it on tty1;
  getty on tty1 is commented out in /etc/inittab.
- Build the shim on the PC: pmbootstrap chroot -b aarch64 --add gcc,musl-dev,
  then gcc -O2 -shared -fPIC -o libnoatomic.so noatomic.c

## WARNING: internet routed through the PC (NAT over USB) crashes the phone
Local USB traffic is fine (200 MB at 37 MB/s); disk I/O is fine. Large downloads
forwarded from the internet via the PC's NAT crash/reboot the phone within seconds.
Download packages on the PC and serve them over USB (python3 -m http.server).
