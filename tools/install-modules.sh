#!/bin/sh
# Install a kernel package's module tree on the phone (run on the PC, phone up in Linux over USB).
#
# Usage: tools/install-modules.sh <unpacked-apk-dir> [phone-ip]
#   <unpacked-apk-dir>  the linux-postmarketos-qcom-sm6150 apk extracted with tar -xzf
#   needs: SSH_ASKPASS set up for the phone's user (see HANDOFF.md) and the user's sudo password in $PHONE_PW
#
# Why depmod on the phone: the package's own depmod cannot read the .zst compressed modules, so its
# modules.dep has NO dependencies and `modprobe msm` fails with "Unknown symbol drm_dp_...".
# The old tree is kept as <release>.old so a bad build can be rolled back.
set -eu
SRC=${1:?unpacked apk dir}
IP=${2:-172.16.42.1}
REL=$(ls "$SRC/usr/lib/modules")
SSH="ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null user@$IP"
tar -C "$SRC/usr/lib/modules" -cf - "$REL" | $SSH 'cat > /tmp/mods.tar'
printf '%s\n' "$PHONE_PW" | $SSH "sudo -S sh -c 'rm -rf /lib/modules/$REL.old; [ -d /lib/modules/$REL ] && mv /lib/modules/$REL /lib/modules/$REL.old; tar -C /lib/modules -xf /tmp/mods.tar && depmod -a $REL && rm -f /tmp/mods.tar && echo installed $REL'"
