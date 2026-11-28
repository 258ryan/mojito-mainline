# call setup on PipeWire (2026-11-28): arm7 (topology upload, stock earpiece topology, volume step) + no CVS session,
# 1-channel codec port for calls, no probe, kernel HAL test code off
sh "$(dirname "$0")/arm7.sh" >/dev/null 2>&1
P=/sys/module
echo 0 > $P/q6voice/parameters/stream
echo 0 > $P/q6voice/parameters/pcm_probe
echo 0 > $P/q6voice/parameters/hal_reroute
echo 1 > $P/snd_soc_sm8250/parameters/rx0_channels   # calls need 1 channel (media then mono until the Channels control exists)
echo 1 > $P/q6cvp/parameters/rx_channels; echo 1 > $P/q6cvp/parameters/rx_speakers; echo 1 > $P/q6cvp/parameters/tx_channels
for f in q6voice/parameters/stream q6voice/parameters/stream_cal q6voice/parameters/hal_reroute snd_soc_sm8250/parameters/rx0_channels q6cvp/parameters/rx_topology q6cvp/parameters/rx_channels; do echo $f=$(cat $P/$f); done
dmesg | grep -c "registered the topologies"
