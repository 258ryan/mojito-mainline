# Recording a working Wi-Fi boot on stock MIUI (2026-11-27)

## Recorder kernel
- Source: github.com/MiCode/Xiaomi_Kernel_OpenSource branch `mojito-r-oss` (4.14.190) + `../qrtrcap/qrtrcap-downstream-4.14.patch`.
- Config: the running stock `/proc/config.gz`, with `LOCALVERSION="-perf-gcfbf768af191"`, `LOCALVERSION_AUTO` and `MODULE_SIG_FORCE` off.
- Toolchain: clang 18 (`CC`) with AOSP `aarch64-linux-android-4.9` binutils 2.27 (tag android-10.0.0_r47) as `CROSS_COMPILE`;
  `KCFLAGS="-Wno-error -Wno-strict-prototypes -gdwarf-4"`; target `Image.gz`. Binutils 2.42 fails to link this tree.
- Boot image: the Magisk-patched stock `boot.img` (header v3) with only the kernel replaced, so root stays.
- Some vendor modules fail their version check (with the stock-derived config: wlan, two audio, exfat, ...).
- Adding DEBUG_FS/DEVMEM changes more module checksums; the audio modules that start the ADSP are then rejected.
- Decode `/proc/qrtrcap` with `../qrtrcap/qrtrdecode.py`; `analyze-before-cap.py <qrtrcap dir> <capture>` lists traffic before the capability request.

## Tools (static arm64, no libc: `clang --target=aarch64-linux-gnu -O2 -ffreestanding -fno-stack-protector -fno-builtin -nostdlib -static -fuse-ld=lld`)
- `devrd.c`: print MMIO registers. `rwatch.c`: log register changes with timestamps. `dumpstate.sh`: same state dump on both OSes.
  Never read TLMM pins 0-3, 6-9 or 123 on this phone.
- `adsprpcd-instance-test.sh <name> <instance>...`: one boot with the ADSP started and only the listed `adsprpcd` instances.
  Wait for `boot_completed` between reboots or Magisk enters safe mode and skips boot scripts.
