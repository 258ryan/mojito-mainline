#!/bin/sh
# Build a header v2 boot.img for the mainline kernel, the way Xiaomi's SM6150 ABL accepts it
# (recipe from github.com/VipinVIP/violet-sm6150-mainline: raw Image + ramdisk + DTB in one boot.img,
# DTB carrying the stock msm-id/board-id, and the dtbo partition ERASED before booting it).
#
# Usage:
#   PMOS_BOOT_UUID=... PMOS_ROOT_UUID=... ./mk-bootimg-v2.sh <Image> <dtb> <ramdisk> [out.img]
#
#   Image    raw arm64 kernel (linux-postmarketos-qcom-sm6150 installs it as /boot/Image)
#   dtb      sm6150-xiaomi-mojito.dtb (from the same package, /boot/dtbs/qcom/)
#   ramdisk  a pmOS initramfs (for now the downstream one, unpacked from vendor_boot.img with unpack_bootimg)
#
# Env: MKBOOTIMG (default: mkbootimg in PATH; android-tools' python script works),
#      CMDLINE_EXTRA (appended), RAMDISK_OFFSET / DTB_OFFSET (default: violet's 0x1000000 / 0x1f00000).
#
# Then: fastboot flash boot_b out.img && fastboot erase dtbo_b && fastboot set_active b && fastboot reboot
# Back to the working downstream slot: fastboot set_active a && fastboot reboot
set -eu

IMG=${1:?Image}
DTB=${2:?dtb}
RAMDISK=${3:?ramdisk}
OUT=${4:-boot-mainline-v2.img}
: "${PMOS_BOOT_UUID:?set PMOS_BOOT_UUID (pmOS_boot partition UUID)}"
: "${PMOS_ROOT_UUID:?set PMOS_ROOT_UUID (pmOS_root partition UUID)}"
MKBOOTIMG=${MKBOOTIMG:-mkbootimg}
RAMDISK_OFFSET=${RAMDISK_OFFSET:-0x01000000}
DTB_OFFSET=${DTB_OFFSET:-0x01f00000}

case "$(head -c 64 "$IMG" | tail -c 8 | head -c 4)" in
	ARMd) ;;
	*) echo "FATAL: $IMG is not a raw arm64 Image (EFI zboot? build with EFI_ZBOOT off)" >&2; exit 1 ;;
esac

TMPDTB=$(mktemp --suffix=.dtb)
trap 'rm -f "$TMPDTB"' EXIT
cp "$DTB" "$TMPDTB"
# The IDs Xiaomi's ABL matches (stock SM6150 base DTB msm-id, stock IDP overlay board-id).
fdtput -t x "$TMPDTB" / qcom,msm-id 0x163 0x0
fdtput -t x "$TMPDTB" / qcom,board-id 0x22 0x0
echo "dtb: msm-id=$(fdtget -t x "$TMPDTB" / qcom,msm-id) board-id=$(fdtget -t x "$TMPDTB" / qcom,board-id)"

CMDLINE="console=tty0 loglevel=7 clk_ignore_unused pmos_boot_uuid=$PMOS_BOOT_UUID pmos_root_uuid=$PMOS_ROOT_UUID pmos_rootfsopts=defaults ${CMDLINE_EXTRA:-}"

$MKBOOTIMG \
	--kernel "$IMG" \
	--ramdisk "$RAMDISK" \
	--dtb "$TMPDTB" \
	--pagesize 4096 \
	--header_version 2 \
	--base 0x00000000 \
	--kernel_offset 0x00008000 \
	--ramdisk_offset "$RAMDISK_OFFSET" \
	--second_offset 0x00000000 \
	--tags_offset 0x00000100 \
	--dtb_offset "$DTB_OFFSET" \
	--cmdline "$CMDLINE" \
	-o "$OUT"

echo "built $OUT ($(stat -c%s "$OUT") bytes): kernel $(stat -c%s "$IMG"), ramdisk $(stat -c%s "$RAMDISK")"
