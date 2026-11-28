echo mojito-var_two.bin > /sys/module/q6core/parameters/register_topologies; echo "topology upload $?"
echo 4 > /sys/module/q6voice/parameters/volume_step
grep . /sys/module/q6voice/parameters/calibrate | sed 's,.*/,,'
echo 268500989 > /sys/module/q6cvp/parameters/rx_topology
for m in q6voice_common q6mvm q6cvp q6cvs q6voice q6voice_dai q6core; do echo "module $m +p" > /sys/kernel/debug/dynamic_debug/control; done
printf "armed rx 0x%x tx 0x%x step %s\n" $(cat /sys/module/q6cvp/parameters/rx_topology) $(cat /sys/module/q6cvp/parameters/tx_topology) $(cat /sys/module/q6voice/parameters/volume_step)
