#!/bin/sh
# Full Phosh session: scanout on simpledrm (card0), rendering on the Adreno (renderD128), seat from seatd.
rc-service kmscon-console stop >/dev/null 2>&1
sleep 1
mkdir -p /run/user/0 && chmod 700 /run/user/0
seatd -g video > /var/tmp/seatd.log 2>&1 &
SEATD_PID=$!
sleep 1
export XDG_RUNTIME_DIR=/run/user/0 LIBSEAT_BACKEND=seatd SEATD_SOCK=/run/seatd.sock
export WLR_DRM_DEVICES=/dev/dri/card0 WLR_RENDER_DRM_DEVICE=/dev/dri/renderD128
export WLR_BACKENDS=drm,libinput WLR_RENDERER=gles2 WLR_LIBINPUT_NO_DEVICES=1
export XDG_SESSION_TYPE=wayland XDG_CURRENT_DESKTOP=Phosh:GNOME HOME=/root
echo "=== starting phosh-session $(date +%T)"
( sleep 30; echo "=== process snapshot at +30 s:"; ps -o pid,args | grep -E 'phosh|phoc|gnome-session|squeekboard|gnome-shell|evolution|polkit|dbus' | grep -v grep | cut -c1-110 ) &
timeout 45 /usr/bin/phosh-session > /var/tmp/phosh.log 2>&1
echo "phosh-session exit: $? (143 = ran until the 45 s timeout)"
sleep 1; pkill -f gnome-session 2>/dev/null; pkill -f squeekboard 2>/dev/null
kill $SEATD_PID 2>/dev/null; rm -f /run/seatd.sock
rc-service kmscon-console start >/dev/null 2>&1
echo "=== cleaned up"
