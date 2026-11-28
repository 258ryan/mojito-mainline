#!/bin/sh
# Generate the call-audio firmware files for mojito from the stock vendor image (vendor_a.img from the official ROM).
# Usage: tools/acdb/extract-voice-cal.sh vendor_a.img outdir
# Needs: debugfs (e2fsprogs), aarch64-linux-gnu-gcc, qemu-aarch64 (qemu-user / qemu-user-static), python3. No root.
set -e
V=$(realpath "$1"); O=$(realpath -m "$2"); T=$(dirname "$(realpath "$0")")
W=$(mktemp -d); trap 'rm -rf "$W"' EXIT; mkdir -p "$O" "$W/db" "$W/out"
debugfs -R "dump /lib64/libaudcal.so $W/libaudcal.so" "$V" >/dev/null 2>&1
for f in IDP_Bluetooth_cal IDP_Codec_cal IDP_General_cal IDP_Global_cal IDP_Handset_cal IDP_Hdmi_cal IDP_Headset_cal IDP_Speaker_cal; do
	debugfs -R "dump /etc/acdbdata/IDP/$f.acdb $W/db/$f.acdb" "$V" >/dev/null 2>&1
done
debugfs -R "dump /etc/acdbdata/adsp_avs_config.acdb $W/db/adsp_avs_config.acdb" "$V" >/dev/null 2>&1
[ -s "$W/libaudcal.so" ] && [ -s "$W/db/IDP_Global_cal.acdb" ] || { echo "files not found in $V" >&2; exit 1; }
aarch64-linux-gnu-gcc -O1 -static -o "$W/q" "$T/load.c" "$T/init.c" "$T/q.c"
# TX device 4 = handset mic, RX device 7 = earpiece (stock ACDB ids)
(cd "$W" && qemu-aarch64 ./q ./libaudcal.so ./db 4 7)
cp "$W/out/vocproc_static.bin"  "$O/mojito-voice-static.bin"
cp "$W/out/vocproc_dynamic.bin" "$O/mojito-voice-volume.bin"
cp "$W/out/vocproc_devcfg.bin"  "$O/mojito-voice-devcfg.bin"
cp "$W/out/stream_static.bin"   "$O/mojito-voice-stream.bin"
cp "$W/out/columns0.bin"        "$O/mojito-voice-columns.bin"
python3 "$T/mk-voice-topologies.py" "$W/db/IDP_Global_cal.acdb" "$O/mojito-var_two.bin"
echo "done: $(ls "$O" | tr '\n' ' ')"
