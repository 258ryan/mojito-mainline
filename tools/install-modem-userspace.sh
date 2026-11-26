#!/bin/sh
# Install and enable the modem userspace on the phone (mainline, slot B), from the PC.
# The phone has no internet before the modem works, so the packages are fetched on the PC
# and served over the USB network (same method as the Phosh install in HANDOFF.md).
#
# Usage: PHONE_PW=... tools/install-modem-userspace.sh [apn]
#   needs: SSH_ASKPASS set up for the phone's user (see HANDOFF.md), pmbootstrap's apk.static,
#          the kernel with the modem/IPA nodes (package r20+) already booted.
#   apn:   optional; creates a NetworkManager GSM connection "mobile" with it. The network also
#          reports the attach APN: mmcli -m any | grep "initial bearer apn".
#
# What it does on the phone: apk add rmtfs tqftpserv qrtr modemmanager (+ -openrc),
# adds tqftpserv, rmtfs, modemmanager to the default runlevel, runs rc-update -u (the clock may
# be in 1970, see HANDOFF), and keeps rmtfs's default "avoid writing" mode (EFS writes stay in RAM).
# Back up modemst1/modemst2/fsg/fsc first (HANDOFF: "Modem").
set -eu
APN=${1:-}
IP=172.16.42.1
PC=172.16.42.2
AS=${APK_STATIC:-$HOME/.local/var/pmbootstrap/apk.static}
KEYS=${APK_KEYS:-$(find "$HOME/.local" -path '*pmb/data/keys' -type d | head -1)}
SSH="ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null user@$IP"
W=$(mktemp -d)
trap 'kill $HP 2>/dev/null; rm -rf "$W"' EXIT

PKGS="rmtfs rmtfs-openrc tqftpserv tqftpserv-openrc qrtr modemmanager modemmanager-openrc"
mkdir -p "$W/root/etc/apk/keys" "$W/root/lib/apk/db" "$W/cache" "$W/repo/aarch64"
cp "$KEYS"/* "$W/root/etc/apk/keys/"
$SSH 'cat /lib/apk/db/installed' > "$W/root/lib/apk/db/installed"
$SSH 'cat /etc/apk/world' > "$W/root/etc/apk/world"
echo aarch64 > "$W/root/etc/apk/arch"
$SSH 'cat /etc/apk/repositories' > "$W/repos"
A="$AS --root $W/root --arch aarch64 --repositories-file $W/repos --keys-dir $W/root/etc/apk/keys --cache-dir $W/cache"
$A update >/dev/null
# everything apk would add, as package names
NEED=$($A add --simulate --no-scripts $PKGS | sed -n 's/^([ 0-9]*\/[0-9]*) Installing \([^ ]*\) (.*/\1/p')
[ -n "$NEED" ] || { echo "nothing to install"; exit 0; }
$A fetch -o "$W/repo/aarch64" $NEED >/dev/null
(cd "$W/repo/aarch64" && $AS mkndx --allow-untrusted -o Packages.adb *.apk >/dev/null)
python3 -m http.server 8000 --bind $PC --directory "$W/repo" >/dev/null 2>&1 & HP=$!
sleep 1

printf '%s\n' "$PHONE_PW" | $SSH "sudo -S sh -c '
echo http://$PC:8000/aarch64/Packages.adb > /tmp/modem-repo.txt
apk --repositories-file /tmp/modem-repo.txt --allow-untrusted add $PKGS
rm -f /tmp/modem-repo.txt
for s in tqftpserv rmtfs modemmanager; do rc-update add \$s default; done
rc-update -u
if [ -n \"$APN\" ]; then
	nmcli con add type gsm ifname \"*\" con-name mobile apn \"$APN\" gsm.auto-config no connection.autoconnect yes
fi
echo done
'"
