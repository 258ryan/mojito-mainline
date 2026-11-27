#!/bin/sh
# Build U-Boot for the Redmi Note 10 (mojito): generic qcom_defconfig + qcom-phone.config + mojito.config.
# Usage: build.sh <u-boot-src (git checkout of v2026.10; patches/ are applied to it)> <build-dir> [debug]
#   debug: also start fastboot automatically at power-on (preboot), so USB is set up only once
#          (restarting the USB gadget within one U-Boot boot fails on this phone: dwc3 -110).
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
if [ "${3:-}" = debug ]; then
	sed 's/^preboot=.*/preboot=scsi scan; run fastboot/' "$SRC/board/qualcomm/qcom-phone.env" > "$OUT/mojito-debug.env"
	grep -q '^preboot=scsi scan; run fastboot$' "$OUT/mojito-debug.env"
	echo "CONFIG_ENV_DEFAULT_ENV_TEXT_FILE=\"$OUT/mojito-debug.env\"" >> "$OUT/mojito-frag.config"
fi
make -s -C "$SRC" O="$OUT" qcom_defconfig qcom-phone.config >/dev/null
"$SRC/scripts/kconfig/merge_config.sh" -m -O "$OUT" "$OUT/.config" "$OUT/mojito-frag.config" >/dev/null
make -s -C "$SRC" O="$OUT" olddefconfig
make -s -C "$SRC" O="$OUT" -j"$(nproc)"
ls -l "$OUT/u-boot-nodtb.bin"
