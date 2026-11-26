#!/bin/sh
# PC side: start-test.sh <name> <arg>...  Block every adsprpcd, start the ADSP, then start ONLY the listed instances
# ourselves from a copy of the program. Each <arg> is audiopd, sensorspd or default.
set -u
N=$1; shift; D=$HOME/.claude-work/pmos-mojito/statecmp; O=$D/stock/$N; mkdir -p $O; S=$(dirname $0)
{ cat <<'EOT'
#!/system/bin/sh
rm -f /data/adb/post-fs-data.d/00-test.sh
cp /vendor/bin/adsprpcd /data/local/tmp/arpc && chmod 755 /data/local/tmp/arpc
mount -o bind /dev/null /vendor/bin/adsprpcd && echo "adsptest: blocked system adsprpcd" > /dev/kmsg
( exec 3< /dev/subsys_adsp; sleep 3600 ) > /dev/null 2>&1 &
sleep 1
EOT
for a in "$@"; do x=$a; [ $a = default ] && x=
  echo "( LD_LIBRARY_PATH=/vendor/lib64:/system/lib64 /data/local/tmp/arpc $x > /data/local/tmp/arpc-$a.log 2>&1; echo \"adsptest: our $a instance exited rc=\$?\" > /dev/kmsg ) &"
  echo "echo 'adsptest: started our $a instance' > /dev/kmsg"
done; } > $S/00-test.sh
adb push $S/00-test.sh /data/local/tmp/ >/dev/null && adb shell "su -c 'rm -f /data/local/tmp/arpc* /data/local/tmp/q.bin /data/local/tmp/d.txt; cp /data/local/tmp/00-test.sh /data/adb/post-fs-data.d/ && chmod 755 /data/adb/post-fs-data.d/00-test.sh'" || exit 1
adb reboot; timeout 20 tail -f /dev/null
up=; for i in $(seq 1 130); do [ "$(timeout 3 adb get-state 2>/dev/null)" = device ] && { up=1; break; }; [ -n "$(timeout 3 fastboot devices)" ] && { echo "in fastboot"; exit 2; }; timeout 3 tail -f /dev/null; done; [ -n "$up" ] || { echo "no adb"; exit 3; }
adb shell 'i=0; while [ "$(getprop sys.boot_completed)" != 1 ] && [ $i -lt 90 ]; do sleep 3; i=$((i+1)); done; sleep 20; echo "boot_completed=$(getprop sys.boot_completed)"'
rm -f $O/qrtrcap.bin $O/dmesg.txt
adb shell 'which su' >/dev/null || { echo 'INVALID: no su after boot (Magisk safe mode?)'; exit 4; }
echo "== $N: our instances: ${*:-none}"
echo "  running adsprpcd processes: $(adb shell 'ps -A -o ARGS' | grep -a -E 'arpc|adsprpcd' | tr '\n' ';')"
adb shell "su -c 'cat /proc/qrtrcap > /data/local/tmp/q.bin; dmesg > /data/local/tmp/d.txt; chmod 644 /data/local/tmp/q.bin /data/local/tmp/d.txt; head -c 300 /data/local/tmp/arpc-*.log'" 2>&1 | cut -c1-150 | head -8
adb pull /data/local/tmp/q.bin $O/qrtrcap.bin >/dev/null 2>&1; adb pull /data/local/tmp/d.txt $O/dmesg.txt >/dev/null 2>&1
grep -a -q "adsptest: blocked system adsprpcd" $O/dmesg.txt || { echo "INVALID: the test script did not run"; exit 5; }
grep -a -E "adsptest:|lpass: adsp: Brought|QMI Server Connected" $O/dmesg.txt | cut -c1-110
python3 -I $HOME/.claude-work/pmos-mojito/qrtrcap/qrtrdecode.py $O/qrtrcap.bin -s 0x45 --bytes 8 2>/dev/null | awk '/req  msg 0x0024/ && !q {print "  capability sent " $1; q=1} /resp msg 0x0024/{print; getline; print; exit}' | cut -c1-120
