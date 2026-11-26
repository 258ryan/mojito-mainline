#!/bin/sh
# Phosh as the unprivileged user (so the lock screen can authenticate against a real password).
# Usage (as root): run-phosh-user.sh [seconds]
T=${1:-300}
UID_=10000
[ -f /etc/pam.d/phosh ] || printf 'auth\tinclude\tbase-auth\naccount\tinclude\tbase-account\npassword\tinclude\tbase-password\n' > /etc/pam.d/phosh
rc-service kmscon-console stop >/dev/null 2>&1
sleep 1
mkdir -p /run/user/$UID_ && chown user:user /run/user/$UID_ && chmod 700 /run/user/$UID_
chmod 666 /dev/dri/renderD128
seatd -g wheel > /var/tmp/seatd.log 2>&1 &
SEATD_PID=$!
sleep 1
echo "=== starting phosh-session as user $(date +%T)"
su user -s /bin/sh -c "export XDG_RUNTIME_DIR=/run/user/$UID_ HOME=/home/user LIBSEAT_BACKEND=seatd SEATD_SOCK=/run/seatd.sock WLR_DRM_DEVICES=/dev/dri/card0 WLR_RENDER_DRM_DEVICE=/dev/dri/renderD128 WLR_BACKENDS=drm,libinput WLR_RENDERER=gles2 WLR_LIBINPUT_NO_DEVICES=1 XDG_SESSION_TYPE=wayland XDG_CURRENT_DESKTOP=Phosh:GNOME; exec timeout $T /usr/bin/phosh-session" > /var/tmp/phosh.log 2>&1
echo "phosh-session exit: $?"
sleep 1; pkill -x gnome-session-binary 2>/dev/null; pkill -x squeekboard 2>/dev/null
kill $SEATD_PID 2>/dev/null; rm -f /run/seatd.sock
rc-service kmscon-console start >/dev/null 2>&1
echo "=== cleaned up"
