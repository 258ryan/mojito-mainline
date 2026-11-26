#!/bin/sh
# Install the Phosh autostart on the phone (run on the PC, phone up in Linux over USB).
#   PHONE_PW=<sudo password> tools/install-phosh-autostart.sh [phone-ip]
# Needs the PAM service /etc/pam.d/phosh (created here) so the lock screen accepts the user's password.
set -eu
IP=${1:-172.16.42.1}
D=$(cd "$(dirname "$0")/../mainline/autostart" && pwd)
SSH="ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null user@$IP"
for f in phosh-mojito.initd phosh-mojito-session phosh-autologin profile.phosh; do
	$SSH "cat > /tmp/$f" < "$D/$f"
done
printf '%s\n' "$PHONE_PW" | $SSH "sudo -S sh -c '
set -e
install -D -m 0755 /tmp/phosh-mojito.initd /etc/init.d/phosh-mojito
install -D -m 0755 /tmp/phosh-mojito-session /usr/local/libexec/phosh-mojito-session
install -D -m 0755 /tmp/phosh-autologin /usr/local/libexec/phosh-autologin
install -D -m 0644 -o 10000 -g 10000 /tmp/profile.phosh /home/user/.profile.phosh
grep -q profile.phosh /home/user/.profile 2>/dev/null || echo \"[ -f ~/.profile.phosh ] && . ~/.profile.phosh\" >> /home/user/.profile
chown 10000:10000 /home/user/.profile
[ -f /etc/pam.d/phosh ] || printf \"auth\\tinclude\\tbase-auth\\naccount\\tinclude\\tbase-account\\npassword\\tinclude\\tbase-password\\n\" > /etc/pam.d/phosh
addgroup user seat 2>/dev/null || true
rc-update del kmscon-console default 2>/dev/null || true
rc-update add elogind default 2>/dev/null || true
rc-update add phosh-mojito default 2>/dev/null || true
# the phone clock is stuck in 1970, so OpenRC thinks its cached dependency tree is newer than our new script and
# would never notice the service: rebuild the cache explicitly
rc-update -u
rm -f /tmp/phosh-mojito.initd /tmp/phosh-mojito-session /tmp/phosh-autologin /tmp/profile.phosh
echo installed; rc-update show | grep -E \"phosh|elogind|kmscon\"; id user'"
