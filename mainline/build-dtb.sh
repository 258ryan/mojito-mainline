#!/bin/sh
# Compile sm6150-xiaomi-mojito.dts to a DTB without rebuilding the kernel package.
# DTS-only changes need no pmbootstrap build and no sudo: this is the fast loop
# (edit the DTS -> build-dtb.sh -> mk-bootimg-v2.sh -> fastboot flash boot_b).
#
# Usage: ./build-dtb.sh <linux-tree> [out.dtb] [dts]
#   linux-tree  a mainline 7.4-rc4 tree, or a sparse checkout of just
#               arch/arm64/boot/dts/qcom, include/ and scripts/dtc/include-prefixes
#   dts         default: sm6150-xiaomi-mojito.dts next to this script
#
# The DTB is compiled with -@ (symbols). Header v2 packing adds qcom,msm-id / qcom,board-id
# afterwards (mk-bootimg-v2.sh), so they are not set here.
set -eu

TREE=${1:?linux tree}
OUT=${2:-sm6150-xiaomi-mojito.dtb}
DTS=${3:-$(dirname "$0")/sm6150-xiaomi-mojito.dts}
Q=$TREE/arch/arm64/boot/dts/qcom
PP=$(mktemp --suffix=.dts)
trap 'rm -f "$PP"' EXIT

cpp -nostdinc -undef -D__DTS__ -x assembler-with-cpp \
	-I "$Q" -I "$TREE/include" -I "$TREE/scripts/dtc/include-prefixes" \
	"$DTS" -o "$PP"
dtc -@ -I dts -O dtb -o "$OUT" "$PP" 2>&1 | grep -v 'Warning' || true
echo "built $OUT ($(stat -c%s "$OUT") bytes)"
