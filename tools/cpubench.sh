#!/bin/sh
# CPU benchmark, run on the phone: sh cpubench.sh
# fixed work timed on one big core, one small core, then all cores; reports clock and hottest CPU sensor
temps() { m=0; for z in /sys/class/thermal/thermal_zone*; do case $(cat $z/type) in cpu*) t=$(cat $z/temp); [ $t -gt $m ] && m=$t;; esac; done; echo $((m/1000)); }
now() { cut -d' ' -f1 /proc/uptime; }
one() { s=$(now); taskset -c $1 sh -c 'dd if=/dev/zero bs=1M count=600 2>/dev/null | sha256sum >/dev/null'; echo "core $1: $(echo "$(now) $s" | awk '{printf "%.2f", $1-$2}') s"; }
echo "start max temp $(temps) C"; one 7; one 0
s=$(now); for i in 0 1 2 3 4 5 6 7; do taskset -c $i sh -c 'dd if=/dev/zero bs=1M count=1500 2>/dev/null | sha256sum >/dev/null' & done
sleep 6; echo "under load: policy0=$(cat /sys/devices/system/cpu/cpufreq/policy0/scaling_cur_freq) policy6=$(cat /sys/devices/system/cpu/cpufreq/policy6/scaling_cur_freq) temp $(temps) C"
wait; echo "all 8 cores: $(echo "$(now) $s" | awk '{printf "%.2f", $1-$2}') s, end temp $(temps) C"
