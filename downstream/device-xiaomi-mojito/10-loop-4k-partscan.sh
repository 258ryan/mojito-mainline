#!/bin/sh
# Kernels < 5.8 lack LOOP_CONFIGURE, so losetup scans the partition table
# before applying --sector-size 4096 and the pmOS subpartitions never appear.
# Attach userdata ourselves and force a rescan after the block size is set.
part=""
for i in $(seq 1 50); do
	for u in /sys/class/block/*/uevent; do
		grep -q '^PARTNAME=userdata$' "$u" 2>/dev/null || continue
		part="/dev/$(basename "$(dirname "$u")")"
	done
	[ -n "$part" ] && [ -e "$part" ] && break
	sleep 0.2
done
[ -n "$part" ] || { echo "loop-4k: userdata not found"; exit 0; }
loop="$(losetup --show -Pf --sector-size 4096 "$part")" || exit 0
blockdev --rereadpt "$loop" || echo "loop-4k: rereadpt failed on $loop"
mdev -s 2>/dev/null
echo "loop-4k: $part -> $loop"
ls -1 "${loop}"p* 2>/dev/null
