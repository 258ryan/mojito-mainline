#!/bin/sh
# Build U-Boot for the Redmi Note 10 (mojito): generic qcom_defconfig + qcom-phone.config + mojito.config.
# Usage: build.sh <u-boot-src (git checkout of v2026.10; patches/ are applied to it)> <build-dir> [debug|ums]
#   debug: also start fastboot at power-on (after the blkmap setup), so USB is set up only once
#          (restarting the USB gadget within one U-Boot boot fails on this phone: dwc3 -110).
#   ums:   rescue build: at power-on, export the userdata partition (= the pmOS disk image) to the PC as USB mass storage
#          (no button needed; boot it with `fastboot boot`, then repair the image from the PC).
# Output: <build-dir>/u-boot-nodtb.bin, packed by mk-bootimg-v2.sh like a kernel.
set -eu
SRC=$(realpath "$1"); OUT=$(realpath -m "$2"); HERE=$(dirname "$(realpath "$0")")
export CROSS_COMPILE=${CROSS_COMPILE:-aarch64-linux-gnu-}
mkdir -p "$OUT"
# our U-Boot patches (skipped when already applied)
for p in "$HERE"/patches/*.patch; do
	[ -e "$p" ] || continue
	git -C "$SRC" apply --reverse --check "$p" 2>/dev/null || git -C "$SRC" apply "$p"
done
cp "$HERE/mojito.config" "$OUT/mojito-frag.config"
# Environment: upstream qcom-phone.env, with preboot also mapping the pmOS disk image inside userdata
# (pmOS_boot = EFI system partition, pmOS_root) as "blkmap 0", so "bootefi bootmgr" finds BOOTAA64.EFI on it.
PRE='scsi scan; run mojito_blkmap'
[ "${3:-}" = debug ] && PRE="$PRE; run fastboot"
[ "${3:-}" = ums ] && PRE="$PRE; part number scsi 0 userdata ud_num; ums 0 scsi 0:\${ud_num}"
sed "s/^preboot=.*/preboot=$PRE/" "$SRC/board/qualcomm/qcom-phone.env" > "$OUT/mojito.env"
grep -q "^preboot=$PRE\$" "$OUT/mojito.env"
cat >> "$OUT/mojito.env" <<'ENV'

# pmOS installs its own partition table inside userdata; blkmap exposes it (4 KiB blocks like the UFS LUN).
mojito_blkmap=part start scsi 0 userdata ud_start && part size scsi 0 userdata ud_size && \
	blkmap create pmos && blkmap map pmos 0 0x${ud_size} linear scsi 0 0x${ud_start}
ENV
echo "CONFIG_ENV_DEFAULT_ENV_TEXT_FILE=\"$OUT/mojito.env\"" >> "$OUT/mojito-frag.config"
make -s -C "$SRC" O="$OUT" qcom_defconfig qcom-phone.config >/dev/null
"$SRC/scripts/kconfig/merge_config.sh" -m -O "$OUT" "$OUT/.config" "$OUT/mojito-frag.config" >/dev/null
make -s -C "$SRC" O="$OUT" olddefconfig
make -s -C "$SRC" O="$OUT" -j"$(nproc)"
ls -l "$OUT/u-boot-nodtb.bin"
