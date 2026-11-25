#!/bin/sh
sec() { echo; echo "##### $1"; }
sec CPU; grep -m1 -i hardware /proc/cpuinfo; nproc; for c in /sys/devices/system/cpu/cpu[0-9]*; do printf "%s:%s/%s " ${c##*/} $(cat $c/cpufreq/scaling_cur_freq 2>/dev/null) $(cat $c/cpufreq/cpuinfo_max_freq 2>/dev/null); done; echo
sec MEMORY; free -m | head -2
sec STORAGE; cat /sys/block/sda/device/model 2>/dev/null; ls /sys/block | tr '\n' ' '; echo; df -h / | tail -1
sec DISPLAY; for c in /sys/class/drm/card0-*; do echo "${c##*/} $(cat $c/status) $(head -1 $c/modes 2>/dev/null)"; done; ls /sys/class/backlight/; for b in /sys/class/backlight/*; do echo "${b##*/} brightness=$(cat $b/brightness)/$(cat $b/max_brightness)"; done
sec INPUT; for d in /sys/class/input/event*; do echo "${d##*/}: $(cat $d/device/name)"; done
sec BATTERY/POWER; for p in /sys/class/power_supply/*; do echo "${p##*/}: type=$(cat $p/type 2>/dev/null) status=$(cat $p/status 2>/dev/null) cap=$(cat $p/capacity 2>/dev/null) online=$(cat $p/online 2>/dev/null) volt=$(cat $p/voltage_now 2>/dev/null) temp=$(cat $p/temp 2>/dev/null)"; done
sec THERMAL; for t in /sys/class/thermal/thermal_zone*; do printf "%s=%s " "$(cat $t/type)" "$(cat $t/temp)"; done | tr ' ' '\n' | grep -iE "cpu|battery|skin|xo|quiet|pa|gpu" | head -12
sec SENSORS-IIO; for d in /sys/bus/iio/devices/*; do echo "${d##*/}: $(cat $d/name 2>/dev/null)"; done; ls /dev | grep -iE "sensor|ssc|sns" | tr '\n' ' '; echo
sec REMOTEPROC; for r in /sys/class/remoteproc/*; do echo "${r##*/}: $(cat $r/name 2>/dev/null) $(cat $r/state 2>/dev/null)"; done; ls /sys/bus/msm_subsys/devices/ 2>/dev/null | while read s; do echo "subsys $s: $(cat /sys/bus/msm_subsys/devices/$s/name 2>/dev/null) $(cat /sys/bus/msm_subsys/devices/$s/state 2>/dev/null)"; done
sec WIFI; ls /sys/class/net | tr '\n' ' '; echo; cat /sys/module/wlan/parameters/fwpath 2>/dev/null; ls /dev/wcnss* 2>/dev/null; nmcli -t dev 2>/dev/null; rfkill list 2>/dev/null
sec BLUETOOTH; ls /sys/class/bluetooth 2>/dev/null; ls /dev | grep -iE "btfm|hci|bt" | tr '\n' ' '; echo
sec MODEM; ls /dev | grep -iE "rmnet|smd|qrtr|ipa|wwan|at_" | tr '\n' ' '; echo; ls /sys/class/net | grep -iE "rmnet|wwan" | head -3
sec AUDIO; cat /proc/asound/cards 2>/dev/null; ls /dev/snd 2>/dev/null | tr '\n' ' '; echo
sec CAMERA/VIDEO; for v in /sys/class/video4linux/*; do echo "${v##*/}: $(cat $v/name)"; done
sec GPU; ls -l /dev/kgsl-3d0 /dev/dri/renderD128 2>&1; cat /sys/class/kgsl/kgsl-3d0/gpu_model 2>/dev/null; cat /sys/class/kgsl/kgsl-3d0/devfreq/cur_freq 2>/dev/null
sec VIBRATOR/LEDS; ls /sys/class/leds | tr '\n' ' '; echo; ls /sys/class/timed_output 2>/dev/null
sec USB; cat /sys/class/udc/*/state 2>/dev/null; ls /sys/class/udc
sec FINGERPRINT/NFC/IR; ls /dev | grep -iE "fpc|goodix|fingerprint|nfc|nq-|ir|lirc" | tr '\n' ' '; echo
sec GPS; ls /dev | grep -iE "gps|gnss|loc" | tr '\n' ' '; echo
sec FIRMWARE-ERRORS; dmesg | grep -iE "firmware|fw load|Direct firmware|request_firmware|pil.*(fail|error)|subsys.*(fail|error)" | grep -viE "^\s*$" | tail -25
sec KERNEL-ERRORS; dmesg | grep -iE "error|fail" | grep -vE "geni_se_probe|Dump setup failed" | awk '{$1=""; print}' | sort | uniq -c | sort -rn | head -25
