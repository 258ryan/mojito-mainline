#!/bin/sh
# Same hardware-state dump for stock Android and pmOS (root). Usage: dumpstate.sh <workdir with devrd + tlmm.addr>
W=$1; O=$W/out; rm -rf $O; mkdir -p $O
[ -d /sys/kernel/debug/regmap ] || mount -t debugfs none /sys/kernel/debug
sync
echo tlmm; $W/devrd < $W/tlmm.addr > $O/tlmm.txt; sync
# PMIC: one 256-register window per peripheral, only regulator/clock/gpio/revid blocks
echo pmic; : > $O/pmic.txt
rd() { f=/sys/kernel/debug/regmap/$1/registers; [ -f $f ] || f=/sys/kernel/debug/regmap/spmi$1/registers
  [ -f $f ] || { echo "no regmap $1"; return 0; }; p=$2
  while [ $p -le $3 ]; do echo "== $1 $(printf %04x $((p*256)))" >> $O/pmic.txt
    dd if=$f bs=9 skip=$((p*256)) count=256 2>/dev/null >> $O/pmic.txt; p=$((p+1)); done; sync; }
rd 0-00 1 1;   rd 0-00 80 95;  rd 0-00 192 201     # 0x01xx, 0x50-0x5f clocks, 0xc0-0xc9 gpios
rd 0-01 20 35; rd 0-01 64 82                       # 0x14-0x23 smps, 0x40-0x52 ldos
rd 0-04 1 1;   rd 0-04 80 95;  rd 0-04 192 203
rd 0-05 20 32; rd 0-05 64 75;  rd 0-05 160 160     # bob at 0xa0
echo clocks; cat /sys/kernel/debug/clk/clk_summary > $O/clk_summary.txt 2>/dev/null
[ -s $O/clk_summary.txt ] || for c in /sys/kernel/debug/clk/*/; do n=$(basename $c); echo "$n en=$(cat $c/clk_enable_count 2>/dev/null) rate=$(cat $c/clk_rate 2>/dev/null)"; done > $O/clk_summary.txt
echo regulators; for r in /sys/class/regulator/regulator.*; do echo "$(cat $r/name) $(cat $r/state 2>/dev/null) $(cat $r/microvolts 2>/dev/null) users=$(cat $r/num_users 2>/dev/null)"; done > $O/regulators.txt
uname -r > $O/kernel.txt; ls /sys/kernel/debug/regmap > $O/regmaps.txt 2>/dev/null
wc -l $O/*.txt; echo DONE
