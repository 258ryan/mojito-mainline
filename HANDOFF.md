# Handoff: postmarketOS on the Redmi Note 10 (mojito / sunny)

State as of 2026-11-27, mainline Linux 7.4-rc4, kernel package `pkgrel=40`, device package 2-r5, hexagonrpcd-mojito r3, installed as a package and booted through U-Boot (`boot_b`) + systemd-boot. Read this file first.
Older detail (how each thing was found, dead ends, reverse engineering): [`docs/HANDOFF-history.md`](docs/HANDOFF-history.md).

## Update 2026-11-28: owner's phone back on stock; how to try calls

The owner's phone was returned to stock MIUI 14 (V14.0.9.0.SKGMIXM) with a locked bootloader on 2026-11-28, so the
author can no longer test on hardware. Everything below works on a phone installed as described here. The owner's
long-term goal is Sailfish OS on this mainline kernel (kernel, DT, firmware and U-Boot are distro-neutral).

Calls on top of the packaged install (WIP, not packaged yet), see "Calls: received audio" below for the why:
1. Kernel: apply `mainline/wip/calls/q6voice-test-tree-on-r42.patch`, then `q6voice-probe-on-test-tree.patch`.
2. Firmware: base firmware and the voice calibration tables + `mojito-var_two.bin` topologies, generated from the
   official ROM on your own machine: [docs/firmware-from-stock.md](docs/firmware-from-stock.md)
   (`tools/acdb/extract-voice-cal.sh vendor_a.img out/`).
3. Audio backend PipeWire + WirePlumber, and start the user session at boot (fixes GNOME login racing the user
   D-Bus): `ln -s user /etc/init.d/user.user; rc-update add user.user default`.
4. As root after each boot: `sh mainline/wip/calls/phone-setup/arm10.sh` (topology upload, no CVS session,
   1-channel earpiece back end). Then calls work on the earpiece both ways.
Known open: speaker during a call (any profile switch kills the downlink), earpiece volume fixed, media is mono while
`rx0_channels=1` (needs a `RX_CODEC_DMA_RX_0 Channels` control), no Bluetooth call audio.

## Status

| Area | State |
|---|---|
| Boot chain: Xiaomi ABL -> U-Boot (`boot_b`) -> systemd-boot -> kernel from `/boot`; packaged (device package) | works (2026-11-27) |
| Boot, display (DPU/DSI/panel), brightness with smooth dimming, touch, GPU, Phosh | works |
| Wi-Fi (~18 s after boot), Bluetooth (~19 s) | works |
| Mobile data (LTE) | works; calls not set up |
| CPU at full speed (1.71 / 2.21 GHz) with thermal throttling at 90 / 95 C | works (DTS, pkgrel=30) |
| Accelerometer, light sensor, compass; auto-rotation (landscape direction fixed 2026-11-27, device 2-r5) | works |
| Speakers: left = earpiece (top), right = main speaker (bottom) | works (bottom speaker fixed 2026-11-27, pkgrel=34) |
| Microphone (main, AMIC1) | works; hiss around 7 kHz, faint at the stock gain |
| Power and both volume keys, vibrator | works; very short vibration pulses are hardly felt |
| Charging from a wall charger, battery percentage | works |
| Charging from a PC USB port | broken or unreliable (old notes disagree: 500 mA / 50 mA) |
| Suspend (s2idle) | works in a 20 s test since pkgrel=29; longer sleeps, desktop-initiated sleep and power draw untested |
| Headphones, second microphone, calls, camera, GPS, NFC, fingerprint | not working or never tried |

### Added in pkgrel=29 and still to be verified by hand
Flashed to slot B (build #30) with the matching UCM. Boot checked: Wi-Fi 16 s, Bluetooth 17-19 s, modem connected, sensors,
sound card, `RX HPH Mode` names correct with value 3 = `CLS_AB`; no modem stall on this boot.
Item 1 VERIFIED: right channel heard from the bottom speaker; codec 3008=c3 3408=07, macro 0x504=18, amp registers as stock.
(It first seemed quiet in the Settings test.) UCM now uses the stock speaker levels (`RX_RX0` 84, `RX_RX2` 77,
`EAR_PA Volume` 6 = -3 dB; headphones stay at 72), confirmed good by ear while raising the volume. There is no speaker
protection processing: lower these if distortion or heating shows up.
Item 2 VERIFIED: screen off looks right (no bars).
Item 3 VERIFIED (one run): 20 s s2idle with RTC wake: screen back, ADSP and modem running, no crash lines, Wi-Fi reassociated
(gateway reachable), sensors and Bluetooth fine.

1. Patch 0019: `RX HPH Mode` item names fixed; UCM selects `CLS_AB` by name (older kernels would pick another mode).
   Check: speaker test in Phosh (both sides).
2. Patch 0005: panel blanked in `disable` (video still running). Check: screen off shows no bars.
3. Patch 0020: fastrpc invoke wait is freezable. Check: the suspend test below keeps the ADSP and Wi-Fi alive.

## Clean install and calls (2026-11-28)

- A clean `pmbootstrap install` from the public repositories (GNOME Mobile) boots through U-Boot; display, storage resize,
  modem/LTE, calls (signalling), sound card, sensors and the public firmware v2 work. Fixed: the firmware's empty sensor
  registry directory is not in git, so `hexagonrpcd-mojito` failed and with it Wi-Fi, Bluetooth and sensors (r4).
- `qbootctl` could not read the slot under U-Boot: `androidboot.slot_suffix=_b` on the kernel command line (WORKAROUND:
  assumes U-Boot in boot_b; device r6). OpenRC still shows the one-shot service as "crashed".
- **Calls, half working** (kernel r42 patches 0022-0031, `q6voiced`, UCM "Voice Call"): the MICROPHONE reaches the other side
  with the vendor's TX topology SM_ECNS_V2 (0x10F89), one channel (the older 0x10F71 passes nothing on this firmware, CVD
  2.4; echo cancellation not yet judged by ear). RECEIVED audio is silent. Matching already: AFE ports 0xB030 / 0xB037 at
  48 kHz, RX topology default 0x10F77 (the vendor's fallback without calibration), routes, codec and amplifiers powered, the
  earpiece route plays media, every command accepted (the RX volume step is rejected). Tried without sound: RX default and
  none, 1/2 RX channels, stream and vocproc unmute, early and late start, the SDM845 driver's sequence by parameters.
  Current state and next steps: "Calls: received audio (handoff)" below.
- **Modem startup stall still happens** on r40/r41 (`packet before probe, dropped`, then the watchdog at ~50 s; it
  recovers). Patch 0021 is therefore incomplete.
- **Pressing the power button restarted the phone** (GNOME's default is suspend). Likely suspend/resume; not confirmed.
- Camera: `mainline/wip/camera/mojito-camera-probe.dts` (untested) describes the ultrawide IMX355 in slots 3 and 4;
  `CONFIG_VIDEO_IMX355=m` since r41. Stock module files decoded: address 0x1a, 19.2 MHz, 4 lanes, one switched supply.

## Calls: received audio (handoff, 2026-11-28)

Goal: hear the other side. Calls connect and the microphone is heard; the earpiece stays silent.

**Proven**
- The earpiece path works during a call: tones played on the "Voice Call" earpiece sink in a live call were heard, so the
  AFE port (RX_CODEC_DMA_RX_0, 0xB030), codec and amplifier are fine. Not proven: that the voice processor feeds that port.
- A test build registers everything below with every command successful, in real calls: custom topology upload (q6core
  0x12924/0x12923; the variable-length list format), physical memory map on MVM (0x11334, table size 24, reply 0x11336),
  stream calibration on CVS (0x11369), device config (0x11371), static (0x11373) and volume tables (0x1307B) on CVP, then
  the RX volume step (0x112C2, rejected until the volume table was registered). Rejected here: 0x11374, 0x13079, 0x1307D.
- Still silent with the stock earpiece chain 0x1000fffd + tables + volume step 4, with 2 RX channels and with 1.

**Downlink probe results (2026-11-28, later)**: host-PCM level probe added to the test build (`pcm_probe`, `pcm_rate`,
`probe_now` parameters of q6voice; event hook + no-wait send in q6voice-common; buffers at 64K in the calibration block;
logs peak/RMS only). Results:
- Call-free (hw:0,4 held open with libasound, `scripts/hold.py`, `cf.sh` in the private calls folder): TX tap 50 frames/s with
  real mic levels; RX tap **no events at all** (any rx_channels, 8/16 kHz, topology 0x1000fffd or 0x10F77).
- Real calls: routing is fine (UCM turns on `RX_CODEC_DMA_RX_0 Voice Mixer CS-Voice` and the TX capture mixer; hw:0,4 open at
  8 kHz mono; PulseAudio also keeps MultiMedia1 at 2 ch/44.1 kHz on the same back end). Both taps nearly starve: TX gives the
  first tick ~3 s after start, then ~5 events in 55 s; restarted mid-call (probe_now) it gives none for 15 s; RX never ticks.
  So during a call the vocproc's processing loop hardly runs. (Session names and creation order match the vendor.)
- **REFINED (call 8): the stall comes from the stream calibration table, not the CVS session.** With the CVS session
  and its unmutes kept but `stream_cal=0` (new q6voice switch: skip VSS_ISTREAM_CMD_REGISTER_CALIBRATION_DATA_V2 0x11369)
  the call runs and the mic is heard fully. Earpiece still silent with: stock 1-ch earpiece back end (new
  snd_soc_sm8250 `rx0_channels=1` test parameter), vocproc 1 ch, topology 0x1000fffd + device tables + volume step 4; also
  with no calibration, topology 0x10F77, 2 ch (sdm670-like). RX tap: still no events in any call.
- **FOUND (call 5): our passive CVS session stalls the call** (see the refinement above).
- **Calls 9-10: the RX side of the vocproc never runs in a call.** RX tap alone (`pcm_taps=2`) and with RX topology
  0x10F77 (which surely has the default tap point): start accepted, 0 events, while the TX tap runs at 50 frames/s and
  the far end hears the mic. So the downlink stops before or at the vocproc's RX input. Not the cause (checked): CVP V3
  create layout and direction (2) match vendor; RX unmute (0x1138B dir 1) sent; port 0xB030; session names, creation
  order and the absence of timing/media-type commands for CS calls match vendor and sdm670-mainline; codec DMA port
  channels (1 or 2); PulseAudio holding the ports.
- **Call 11 (kprobes on q6afe_port_start/stop, q6voice_start, q6cvp_session_create):** both ports run before the CVP
  is created (PulseAudio starts 0xB030 with its ASM/ADM stream, q6voiced starts 0xB037), the CVP gets tx 0xB037 / rx
  0xB030, and no port stops or restarts until hang-up. DAPM: `RX_CODEC_DMA_RX_0 Playback` On, stream active. So the AFE
  RX port is running for the whole call; a port restart does not explain the idle RX vocproc. (q6voiced and hold.py
  prepare twice; DPCM does not re-prepare a running back end, checked.)
- **SOLVED in a test (call 12): received audio plays when PulseAudio is not on the earpiece port.** PulseAudio stopped
  (autospawn off for the test), UCM "Voice Call" + Earpiece + Mic applied with alsaucm, so q6voiced's voice stream alone
  started both codec DMA ports: the far end was heard in the earpiece (owner confirmed; mic heard too). In every
  earlier call PulseAudio's MultiMedia1 stream (ASM + ADM COPP on RX_CODEC_DMA_RX_0) was on the port before the voice
  path started, and the downlink never played. Settings: stream_cal=0, rx0_channels=1, vocproc 1 ch in/out, topology
  0x1000fffd + device tables, volume step 4. NB the **RX host-PCM tap gives 0 events even with working downlink**: it is
  useless on this firmware; only the TX tap is a valid health check. Speakerphone not tested (needs PulseAudio/callaudiod).
  Open: is it the ADM stream's presence or only its order (ADM before the vocproc)? Test: with PulseAudio off, start
  `aplay` on hw:0,0 during a call. Then fix properly (kernel or UCM, e.g. no MultiMedia1 route in the Voice Call verb).
- **ROOT CAUSE (calls 13-17): the downlink plays only if the voice stream starts the RX codec DMA port.** PulseAudio's
  Voice Call profile opens its MultiMedia1 sink on RX_CODEC_DMA_RX_0 ~20 ms before q6voiced opens the voice PCM, so the
  port (0xB030) is started by the ADM stream and the voice downlink never plays. Not the cause: media joining later (call
  13, aplay on hw:0,0 mid-call: no drop), closing PulseAudio's sink (14) or sink+source (15) mid-call, rebuilding the
  vocproc mid-call with no PulseAudio stream open (16, new q6voice `restart_now` switch). Works (17, normal PulseAudio +
  callaudiod): mid-call, suspend PulseAudio and stop q6voiced (port stops), reopen the voice PCM alone (scripts/hold.py),
  resume PulseAudio: far end loud and clear, mic heard. Speaker shares the port, so anything playing when a call starts
  (ringtone) would break it too: the fix belongs in the kernel (voice start must (re)start the AFE port) or in the
  daemons (voice PCM first). Test recipe: calls-2026-11-28/scripts/watch17.sh (private).
- **Kernel "HAL" attempt failed (calls 18-20).** New test code: `q6routing_port_suspend/resume` (close/reopen the ADM
  streams on a port), `q6afe_dai_restart_port` (+ q6afe_dai `restart_port` parameter), q6voice `hal_reroute` (default on
  in the installed test build: take ADM off the call's ports, restart them, start voice, reopen ADM). Runs as intended
  at call start (call 18) and after answer with PulseAudio held off 2 s (call 19): still silent. Trace C (normal call,
  12 payload words) vs trace B (working): AFE port config (0x100EF: 48 kHz, 16 bit, 1 ch, mask 1), ADM opens
  (0x10326), CVP create identical word for word; codec digital mutes all released in both. So the DSP-side order is not
  enough: what works is the whole back end (codec + SoundWire + DAPM + AFE) stopped and started again with the voice
  stream first, i.e. the vendor HAL's device disable/enable. The place for that on Linux is userspace (callaudiod, which
  already switches PulseAudio's profile at call start): keep PulseAudio's call sink/source suspended until q6voiced has
  opened the voice PCM. Traces: phonelog/trace-{A,B,C}.txt (private).
- **WORKS ON PIPEWIRE (calls 21-24, 2026-11-28 ~04:35):** switched the audio backend (`apk add
  postmarketos-base-ui-audio-backend-pipewire`: removes PulseAudio, adds pipewire-pulse; back:
  `...-backend-pulseaudio`) and enabled the user services (`rc-update --user add pipewire|wireplumber|pipewire-pulse
  default`: pmOS did not enable them; without them GNOME Calls starts before PipeWire, libcallaudio fails to init and
  Speaker/Mute are greyed out). Calls then play both ways with no hand steps. Trace D: WirePlumber switches to the Voice
  Call profile at call setup and PipeWire reopens its streams ~5 s before q6voiced opens the voice PCM at answer; the
  PulseAudio failure was the voice path starting ~20-30 ms after the port and ADM stream started (the "ADM first"
  rule above is too strong; it is a start-up race or settling problem in the DSP).
- **Needed settings for that:** `rx0_channels=1` (earpiece back end 1 channel, as stock in calls) and vocproc
  `rx_channels=1 rx_speakers=1`; with a 2-channel back end the downlink is silent. But media needs 2 channels (earpiece
  = left, bottom speaker = right). To do (no calls needed): a stock-style mixer control `RX_CODEC_DMA_RX_0 Channels`
  (One/Two) in the machine driver, set to One by the Voice Call verb and Two by HiFi.
- **OPEN: speakerphone in calls.** PipeWire puts Earpiece and Speaker in separate Voice Call profiles (one mapping per
  UCM device; shared PCM -> separate profiles; ConflictingDevice does not change it), so the switch is a profile
  switch. Stock callaudiod switches sink ports only (button does nothing); a patched callaudiod that switches profiles
  (source in pmos-mojito/callaudiod-src, not installed any more) makes the switch happen, but the downlink then dies
  until hang-up, also after switching back (mic keeps working). Trace E: at the switch PipeWire closes/reopens its ADM
  streams; no AFE port or SoundWire restart when the voice PCM is held started (hold2.py, stop threshold = boundary);
  with q6voiced (prepare only) the whole back end would stop. Reopening the voice PCM 1 s after the switch (call 27)
  did not help. In-call speaker with a 1-channel port also needs `RX INT2_1 MIX1 INP0` = RX0 in the Voice Call Speaker
  device. Next step: read wcd937x / SoundWire port handling on a route change during a running stream (no test calls).
  Call 28 (2026-11-28 17:02, last speakerphone test): voice PCMs closed at the profile switch and reopened 5 s later
  (start playback/capture 0) -> speaker still dead, mic fine. So it is NOT the reopen timing; parked as open.
  Patched callaudiod removed again (stock restored), packaged UCM restored.
- **Login race (packaging):** after the PipeWire user services were enabled (~/.config/rc/runlevels/default has only
  pipewire, pipewire-pulse, wireplumber) GNOME login sometimes returns to the user picker: gnome-session starts before
  the user D-Bus socket exists ("Failed to upload environment to DBus: Could not connect"), quits, and pam_openrc stops
  the user services again. FIXED on the phone (2026-11-28 17:07): start the user session at boot, the standard OpenRC
  way: `ln -s user /etc/init.d/user.user; rc-update add user.user default`. dbus/pipewire/wireplumber are up before
  GDM; GNOME then uses that bus (DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/10000/bus), login worked first try.
  To do: ship this in the device package (post-install for the default user).
- **Earpiece volume during calls is not adjustable:** PulseAudio's sink volume does not reach the voice path (fixed CVP
  volume step 4). Likely fix: UCM PlaybackMixerElem for the Voice Call devices on a codec gain (e.g. RX_RX0 Digital
  Volume), or a mixer control for VSS_IVOLUME_CMD_SET_STEP.
- **Superseded:** record an APR trace from stock Android during a call (the only reference left; needs stock booted, see
  "The phone"), compare every voice packet incl. AFE commands sent around call start. Patch for all of the above:
  `mainline/wip/calls/q6voice-probe-on-test-tree.patch` (on top of q6voice-test-tree-on-r42.patch). With `stream=0` (no CVS session, so no stream calibration
  and no stream unmute; as sdm670-mainline, whose working driver never creates one) the vocproc runs the whole call at
  50 frames/s and the far end hears the mic fully. With CVS it ran until the answer, then stalled (far end heard fragments).
  PulseAudio holding the codec DMA ports (tested by suspending its sink/source mid-call) and the port channel counts made
  no difference. The RX tap still never ticked, and the earpiece stayed silent (owner confirmed).

**Untried leads, in suggested order**
1. Measure the downlink inside the DSP: host PCM tap (VSS_IVPCM_CMD_START_V2 0x11339, NOTIFY 0x1133B, PUSH_BUFFER 0x1133A;
   vendor `asoc/msm-pcm-host-voice-v2.c` and `dsp/q6voice.c`), RX at stream and at vocproc; report only peak levels, record
   no audio. Silent at both = the downlink never reaches the stream; sound then silence = the chain; sound at both = the
   hand-over to the AFE port.
2. AFE port channel count: stock sets `RX_CDC_DMA_RX_0 Channels = One` for the earpiece; with our UCM the media path uses
   two. The vocproc was set to one, the port itself was not checked during a call.
3. Smaller differences from the vendor `voc_start_voice_call`/`voice_setup_vocproc`: it sends the TTY mode
   (VSS_ISTREAM_CMD_SET_TTY_MODE) and, only with more than one RX channel, a channel mixer + MFC config (we send neither).
4. Record what stock Android sends during a call (APR trace).

**Test build** (`mainline/wip/calls/q6voice-test-tree-on-r42.patch`, applies on kernel patches 0022-0031; module-only build:
`make M=sound/soc/qcom/qdsp6` in a patched tree with the package config; no MODVERSIONS or signing). Before packaging:
the memory map borrows the q6asm-dais SMMU device (workaround), tables are loaded as files, firmware names are
hard-coded, and `calibrate` defaults to on.
- Files it reads from /lib/firmware (generated on the owner's machine from the stock database, vendor data, never commit):
  `mojito-voice-{columns,stream,devcfg,static,volume}.bin` for TX device 4 / RX device 7, and a topology list.
- How the tables were made: Qualcomm's `libaudcal.so` (vendor image) loaded by a small static aarch64 loader under
  qemu-aarch64 (now public: `tools/acdb/`), `acdb_ioctl` initialise 0x1138C, then 0x13097/6 static, 0x13095/4 "dynamic" (= volume), 0x11397 device
  config, 0x13099/8 stream, 0x1309A column info (324 bytes).
- Topology IDs come from database property 0x113af: earpiece (7) 0x1000fffd (works after upload), handset mic (4)
  0x10000003 (still rejected at commit; the mic uses SM_ECNS_V2 0x10F89, one channel).

**Runtime recipe** (as root, after each boot): write the topology file name to
`/sys/module/q6core/parameters/register_topologies` (a second write fails, harmlessly); `echo 268500989 >
/sys/module/q6cvp/parameters/rx_topology`; `echo 1 >` q6cvp `rx_channels` and `rx_speakers`; `echo 4 >
/sys/module/q6voice/parameters/volume_step`. Call-free test: enable the mixers `RX_CODEC_DMA_RX_0 Voice Mixer CS-Voice`
and `CS-Voice Capture Mixer TX_CODEC_DMA_TX_3`, run `aplay` and `arecord` on hw:0,4 together for 3 s, read dmesg with
dynamic debug on the q6voice modules (aplay's own parameter errors are harmless). A failed topology commit leaves a stuck
session until reboot: judge each ID on a clean boot.

## Open problems, most useful first

1. **Suspend, further testing.** Fixed for a 20 s s2idle (patch 0020; before it the ADSP crashed on every resume). Still to
   check: audio after resume, long sleeps, sleep started by Phosh/gsd-power (battery, 900 s idle; goes through elogind),
   wake by power button, incoming calls/data, and idle power draw. Only `s2idle` exists. Test:
   `echo +20 > /sys/class/rtc/rtc0/wakealarm; echo freeze > /sys/power/state` (run detached; write logs to disk).
2. **Modem stalled at boot on ~40% of boots: FIXED by patch 0021 (kernel pkgrel=40); keep an eye on it.**
   `dog_hal_common.c:173: DOG detects stalled initialization` ~40 s after start, restart, sometimes repeatedly (one boot:
   3 stalls in a row). Light qrtr tracing (`qrtr_ns_message`, enabled from a boot-runlevel service) caught it: in a stalled
   run the modem's `hello` never reaches the name service, so the name service never sends it the server list (rmtfs 14,
   pd-mapper 64, IPA 49, TFTP 4096); the modem registers 43 and 66, never contacts rmtfs, and its watchdog fires. Cause in
   `net/qrtr/smd.c`: with the driver-level `.callback` the rpmsg core creates/opens the channel endpoint before probe; a
   HELLO arriving before probe has set the driver data makes the callback return -EAGAIN, which glink ignores (buffer
   released), so the HELLO is lost. Patch 0021 (r40) sets the driver data first, queues packets until the qrtr endpoint is
   registered, delivers them in order, and warns ("packet before probe, dropped") if one still arrives before probe.
   Upstream candidate (net/qrtr). Verified: 5 untraced boots on r40, 0 stalls, 0 early drops, modem 42 services, Wi-Fi and
   ModemManager up each time (before: 3 stalls in 7 boots; 5 clean by chance at 40% would be ~8%). Series stopped there.
   FAILED attempt r39 (do not retry): driver without `.callback`, endpoint created in probe with rpmsg_create_ept() - on
   glink that needs the core-created `rpdev->ept` as parent; QRTR to modem AND ADSP was dead (rolled back to r38).
   Earlier findings, for the record: not rmtfs starting the modem early (delayed start still stalled); command-line qrtr
   tracing hid the race (0/5). Not tested: EFS writes (`rmtfs_avoid_writing="true"`). Logs: /var/tmp/modemboot-logs/.
3. PC-port charging (add module parameters to the SMB5 driver to try register settings live; a bad setting can suspend USBIN
   until a replug). Stock leaves `0x1366 = 0x03` on an SDP; the driver writes `0x02`.
4. Modem appears to ModemManager only ~30 s after boot (OpenRC also lists `modemmanager` as failed although it runs).
5. One boot hung at udev "Waiting for uevents" (cause unknown).
6. Pops on the speakers (2026-11-27): one at shutdown, one when the lock screen loads, one when the home screen appears; none
   from ordinary sounds or idle power cycles (tested with silent streams). Reproduced by `pulseaudio -k`: the UCM
   DisableSequence switches the amp switches off while PulseAudio's stream is still running, so DAPM powers the whole speaker
   path down mid-stream (trace: amps, EAR/AUX PGA, RDAC3/4, RX_MCLK within 20 ms). Idle power-down after the stream stops does
   not pop. PARKED (user, 2026-11-27): only at these hand-overs, never in normal use. Tried without effect: UCM disable
   sequence muting digitally + staged amp-off with msleep (the stream closes and DAPM powers down before it matters),
   20 ms amp ramp-down wait in the amp PRE_PMD (pkgrel=37, removed in 38), amp shutdown handler (kept, as vendor).
   Both paths pop on their own (only EAR or only AUX enabled), so the shared class-H/VDD_BUCK/RX clock power-down is
   the next suspect; next try: the vendor's RX mute (bolero RX_MUTE around the PA) / keeping supplies up until the PAs
   are off, in wcd937x/lpass-rx-macro.
7. Bluetooth setup flaky (any boot, with or without `clk_ignore_unused`): the second setup (bluetoothd power-on) or a
   re-probe sometimes fails during the firmware download: UART frame errors (-84), "QCA TLV response size mismatch",
   "Failed to request file: qca/cmbtfw12.tlv", retries, then hci0 is removed. Not a clock (stock leaves the 23 unclaimed
   clocks off; the UART clock chain is identical). Suspects: baud switch / flow control on the QUP UART.
8. `modprobe -r hci_uart` after such a failure oopses (NULL in `tty_lock` from `ttyport_close` <- `serdev_device_close`
   <- `hci_uart_unregister_device` <- `qca_serdev_remove`): upstream bug, closing an already closed serdev port.
9. Calls: received audio silent (see the calls handoff above). Mic noise (retest in a quiet room; speaker amps ruled out), second mic
   (needs `qcom,tx-channel-mapping` and probably driver work).

## Speakers: bottom speaker silent after boot (FIXED 2026-11-27, kernel pkgrel=34)

Symptom: the main (bottom) speaker gave no sound after every boot until its path was re-powered once during a stream
(`AUX Amp PA Switch` 0/1), then worked until the next boot. Cause, from DAPM tracing
(`/sys/kernel/tracing/events/asoc/snd_soc_dapm_widget_power`): the WCD937x RX inputs `IN1_HPHL`/`IN2_HPHR`/`IN3_AUX` are DAPM
inputs, so without routes from the RX macro outputs the codec's analog paths (RDAC3/4, EAR/AUX PGA, class-H, buck) and the
amplifiers powered up at login, with no RX clock or data, and never powered down; the AUX stage does not come up that way.
Fix: `audio-routing` `"IN1_HPHL", "HPHL_OUT"`, `"IN2_HPHR", "HPHR_OUT"`, `"IN3_AUX", "AUX_OUT"` (as upstream sm8250-mtp,
sm8450-hdk, X13s). Now the paths power with each stream after `RX_MCLK` and off when PulseAudio suspends the sink.
Also corrected (pkgrel=33): the amplifier roles were swapped. Stock DT + vendor wcd937x ("AW87xxx_SPK" after AUX PGA =
pa-channel 0): 0x5b AW87559 = main speaker on AUX ("AUX Amp"), 0x58 AW87519 = earpiece on EAR ("EAR Amp").
Ruled out on the way (for the record): amp register tables, codec/rx-macro registers (identical), SoundWire port switch,
ignored SoundWire commands (debug patch, removed in pkgrel=35). pkgrel=36 adds an amp `shutdown` handler (off table +
reset, as the vendor driver). Still open: pops (retest now that the paths follow
the stream; the vendor also mutes RX3 until the AUX PA is up and starts the SoundWire datapath in AUX PA PRE_PMU).
Vendor sources used: Neternels/android_kernel_xiaomi_sunny (techpack wcd937x, aw87xxx), LineageOS sm6150 lineage-22.2.

## Going public: status (2026-11-27)

- Public on GitHub: `258ryan/mojito-mainline`, `258ryan/mojito-device`, `258ryan/firmware-xiaomi-mojito`.
- Firmware: built ONLY from the official ROM (455 files, empty sensor registry), tagged v2, checksum pinned in the package.
  NOT yet booted on the phone (user will test later; the phone still runs the private 1-r0).
- Finder packages live in the private local repo `~/.claude-work/finder-packages`; their recipes remain in mojito-device's
  history (build steps and private repo names only), left as they are.
- Fresh install: the initramfs resizes the nested GPT correctly (tested: a 4K-sector image grown into a larger device shows
  the free space to `parted -s print free`). The 917 MB root of the current phone came from the downstream initramfs (no
  rootfs_image_sector_size). To prove on a real from-scratch `pmbootstrap install`.
- Kernel patches: checkpatch on 0003/0009/0011/0013/0017-0021: only MISSING_SIGN_OFF (the author must add Signed-off-by)
  and commit-log lines over 75 characters; no code findings.

## Public firmware package (details)

Goal: a public firmware source so the port can go to pmaports (testing). The private package is a full copy of the vendor
firmware partitions and must not be published as is.
- Must NOT go public: `sensors/registry` (this unit's persist data incl. factory calibration). Not needed: with an empty
  registry the sensor PD rebuilt it (142 files) from `sensors/config`; sensors, rotation and Wi-Fi worked (tested, the
  original registry was restored).
- Not needed / keep out: TrustZone apps and DRM (widevine, mlipay, soter64, secauth, mfido, fpctzapp, hdcp*, vsimapp,
  cardapp, haventkn, gptest, smplap*, securemm, rtic, cmnlib*), cpe_9340, CAMERA_ICP, other chips' BT files.
- Actually loaded (dmesg + modem TFTP log): modem.*, adsp.*, ipa_fws.*, a612_zap.*, wlanmdsp.mbn, modem_pr/mcfg, ath10k
  board.bin + android/{bdf_gl,regdb}.bin, qca/cmbtfw12.tlv + cmnv12.bin, hexagonrpcd sensors/config + sns_reg.conf +
  dsp/adsp + socinfo; a630_sqe.fw + a612_rgmu.bin come from Alpine linux-firmware-qcom.
- Provenance check against the official V14.0.9.0.SKGMIXM fastboot ROM extract (`pmos-mojito/stock/extract`): 337 of 443
  needed files identical. The 26 adsp.* files DIFFER (the package has another ADSP build than this ROM: earlier notes say
  ADSP.VT.5.3-00316 vs the phone's -00323); sensors/config, dsp/adsp and socinfo were not in that extract yet.
  Next: take every public file from the official ROM images (NON-HLOS.bin, BTFM.bin, dspso.bin, vendor), re-test, then
  the user decides where to host it (public repo of blobs, as other pmOS ports do, or extraction from the ROM at build).

## Camera, GPS, NFC, fingerprint, PC charging: assessment (2026-11-27)

- Camera: the SoC part is upstream already: 7.4-rc4 has SM6150 CAMSS (csiphy/csid/vfe_res_sm6150, VFE 170) and talos.dtsi
  has `camss: isp@acb3000` (`qcom,sm6150-camss`). Stock modules (camera dump): wide Sony IMX582 (no mainline driver),
  ultrawide Sony IMX355 (driver has `sony,imx355` OF match + binding: DT nodes only), front OmniVision OV13B10 (driver is
  ACPI-only: needs OF match + clock), macro GC02M1 / depth GC02M1B or OV02B1B (no drivers). First target: ultrawide via DT
  (CCI bus, regulators, MCLK, reset GPIO, CSI-PHY lanes from the stock DT), then libcamera (CAMSS + software ISP).
  IMX582 is NOT in 7.4-rc4 (no imx582.c/imx586.c; only imx576.c), but Luca Weiss (Fairphone, FP4 uses IMX582) wrote a
  mainline-style driver: github.com/danascape/linux-billie branch sm6350-6.19.y, drivers/media/i2c/imx582.c (1201 lines,
  CCI regmap, DT, regulators, inclk, reset GPIO, 4-lane CSI-2, one 4000x2256 mode, chip ID 0x0582 at 0x0016). Use it as
  a kernel patch (credit Luca Weiss) + mojito DT wiring. Macro/depth: the armbian
  Rockchip kernel (github.com/armbian/linux-rockchip, branch rk-6.1-rkr7.2) has gc02m0.c (chip ID 0x02e0, likely the
  GC02M1 base; confirm the ID from the stock module or over I2C) and ov02b10.c (0x2B, for the OV02B1B depth module);
  both use Rockchip's rkmodule interface (~20 uses) and need porting to plain V4L2 + DT bindings. Lowest priority.
- GPS: modem QMI location service 16 is up; ModemManager offers gps-raw/nmea/agps, but enabling fails:
  "Couldn't start GPS engine: QMI protocol error (46): GeneralError". Next: QMI LOC engine lock / NV settings.
- NFC: stock DT has `st,st21nfc` at i2c a84000 (0x08) with rpmh clock 4 (LN_BB_CLK3?); mainline ST NCI drivers to check.
- Fingerprint: runs in a TrustZone app (fpctzapp, QSEECOM): no mainline path.
- PC charging: on a PC port the charger detects SDP and limits input to 450 mA (correct for USB 2). Not testable at 100 %:
  retest at 50-80 % (current should reach ~450 mA). `health=Over voltage` with VBAT 4.444 V below the 4.45 V float: the
  BAT_OV bit stays set after a battery was above float (driver comment); stock floats to 4.47 V (qcom,fv-max-uv).

## CPU speed and throttling (done in pkgrel=30, DTS only)

The cpufreq hardware table offers 1017.6 / 1708.8 MHz (little) and 2016 / 2112 / 2208 MHz (big) that `talos.dtsi`
(QCS615) lacks, so `qcom-cpufreq-hw` rejected them ("Voltage update failed"). The mojito DTS adds those OPPs and gives
every CPU zone passive trips at 90 and 95 C (2 C hysteresis, 250 ms polling, step_wise); `cpuss-*` cool `cpu0`'s
policy, `cpu-1-*` `cpu6`'s (stock mapping: cpuss-2 cpu0-1, cpuss-1 cpu2-3, cpuss-0 cpu4-5, cpu-1-0/1 cpu6,
cpu-1-2/3 cpu7). Stock's kernel trips are at 110 C but Android's thermal-engine throttles earlier; we have no such daemon.

`tools/cpubench.sh`, r29 -> r30 DTB: big core 5.32 -> 4.58 s, little core 14.87 -> 13.79 s, all eight 38.73 -> 34.87 s;
86 C at the end of the run. Sustained 2.5 min all-core load: big cluster steps down 2208 -> 2112 (once 2016) MHz and holds
88-91 C; the little cluster stays at 1708.8 MHz. Not done: skin/battery temperature limits (only the SoC sensors are used).

## U-Boot (DONE 2026-11-27: flashed to `boot_b`, boots the packaged kernel)

Goal: the Xiaomi ABL chainloads generic upstream U-Boot (`qcom_defconfig` + `qcom-phone.config`, no mojito code) from
`boot_b`; U-Boot boots the kernel from `/boot` the standard way, so kernel/DTB updates stop needing hand-packed boot images.
Files: `mainline/u-boot/` (`build.sh`, config fragment `mojito.config`, `patches/`). Source: U-Boot v2026.10 (has QCS615
clock/pinctrl, the UFS/QUSB2/dwc3/SMMU drivers match talos.dtsi; USB 3 PHY has none, U-Boot forces high-speed).

Build: `mainline/u-boot/build.sh <u-boot v2026.10 git tree> <out> [debug]` (needs `gcc-aarch64-linux-gnu`; ~35 s), then
`mk-bootimg-v2.sh <out>/u-boot-nodtb.bin <mojito dtb> <empty ramdisk> u-boot.img`. Test RAM-only: `fastboot boot u-boot.img`.
`debug` starts fastboot at power-on (preboot), for `fastboot oem run:<cmd>` + `fastboot oem console`.

Verified (RAM-only, nothing flashed), 2026-11-27:
- ABL accepts the image; U-Boot runs; screen console via `cont_splash`; menu works with the keys; all 6 UFS LUNs found.
- `blkmap` exposes the pmOS partition table nested in `userdata`: partition 1 = boot (ext4, ESP type GUID), 2 = root.
  `blkmap create pmos; blkmap map pmos 0 <userdata blocks> linear scsi 0 <userdata start>` (4 KiB blocks; get both with
  `part start/size scsi 0 userdata`), then `load blkmap 0:1 ...` works.
- **Linux boots through U-Boot**: initramfs loaded from `blkmap 0:1 /initramfs`, r29 `Image` + r30 DTB sent with
  `fastboot stage`, `booti`. Display, ADSP, modem, Wi-Fi, USB networking all fine; U-Boot supplies KASLR seed and initrd.
  Linux sees 0x80000000-0x17dcfffff as RAM (3527 MB total): still to compare with a normal ABL boot.

U-Boot problems found:
1. Fixed (`patches/0001`): fastboot dequeued every completed IN request; dwc3 logs "was not queued" per reply, and with
   console recording `oem console` reads those back forever. Upstream candidate.
2. Restarting the USB gadget within one U-Boot boot fails (`dwc3 failed to enable ep0out`, `g_dnl_register -110`), e.g.
   leaving fastboot and starting the serial gadget. Only the first USB session per boot works. Cause not found yet.
3. Aborting a fastboot reply from the PC (killing `fastboot` mid-transfer) crashes U-Boot (NULL write in the
   `dwc3_gadget_ep_dequeue` path). Never put `timeout` around `fastboot oem` commands.
4. Stock 1 KiB pre-relocation console record buffer overflows; `mojito.config` enlarges it.

**EFI + systemd-boot chain works** (user's choice over extlinux), RAM-booted U-Boot `efi1`, 2026-11-27:
ABL -> U-Boot (`preboot` runs `mojito_blkmap`: finds `userdata` by name with `part start/size`, maps it as `blkmap 0`)
-> `bootefi bootmgr` finds `EFI/BOOT/BOOTAA64.EFI` on the nested boot partition (ext4 works with U-Boot's EFI file
protocol) -> systemd-boot 262.2 -> loader entry -> Linux via the EFI stub (`efi: EFI v2.11 by Das U-Boot`, efivars,
`initrd=\initramfs`). Display, Phosh, Wi-Fi, USB, ADSP, modem fine; RAM as with booti.
Test files on the phone's `/boot` (added by hand, nothing else changed): `EFI/BOOT/BOOTAA64.EFI` (from the Alpine
`systemd-boot` apk, not installed), `loader/loader.conf`, `loader/entries/mainline-test.conf`, `mainline-test/{Image,dtb}`.

Packaged (2026-11-27) in the private repo `258ryan/mojito-device` (local `~/.claude-work/mojito-device-repo`):
`device-xiaomi-mojito` pkgver 2 (mainline deviceinfo: FAT32 boot, depends on `systemd-boot`, fallback header v2
`boot.img`, `flash_kernel_on_update` off since `boot_b` holds U-Boot; services/UCM/overlays from `mainline/rootfs/`),
`hexagonrpcd-mojito`, `u-boot-xiaomi-mojito` (builds `u-boot.img`). `tools/sync-to-pmaports.sh` copies them, the
firmware package and this kernel package into pmaports. Kernel r31: DTS board-id `0x22` (ABL refuses `<0 0>`; no more
patching when packing) and `CONFIG_EFI_ZBOOT` (`/boot/linux.efi` for systemd-boot, raw `Image` as `/boot/vmlinuz` for
the fallback boot.img). Slot A (downstream 4.14 on the same rootfs) is retired by the user; its boot image is saved in
`~/.claude-work/pmos-mojito/backups/pre-mainline-device-2026-11-27/`.
Installed and flashed 2026-11-27: the packages replaced the downstream device/kernel/firmware packages, `/boot` was
reformatted to FAT32 (label `pmOS_boot`, fstab by UUID, `vfat ... umask=0077`), boot-deploy wrote `linux.efi`,
`initramfs`, the DTB, systemd-boot (`EFI/BOOT/BOOTAA64.EFI`), `loader/entries/pmos.conf` and a fallback `boot.img`;
`u-boot.img` from the package is on `boot_b`. Verified: `efi: EFI v2.11 by Das U-Boot`, r31 kernel, Phosh, Wi-Fi, sshd,
sensors service, accelerometer mount matrix, sound card, GPU firmware (from `firmware-xiaomi-mojito-mainline` through
the `/lib/firmware/postmarketos` search path). Kernel updates are now just `apk upgrade` + reboot (boot-deploy updates
`/boot`; nothing to flash). The test files, `/usr/local/bin/hexagonrpcd-mojito`, `/etc/modprobe.d/ath10k-mojito.conf`
and the hand-copied modules are gone.

Through U-Boot the kernel has SMBIOS (`/sys/class/dmi/id`: vendor `xiaomi`, product `Xiaomi Redmi Note 10`), so ASoC
names the card `xiaomi-XiaomiRedmiNote10` and UCM looks for `conf.d/sm8250/xiaomi-XiaomiRedmiNote10.conf` (device package
pkgrel 2; the old name links to it). Without it PulseAudio shows only `auto_null`.

Rescue: `build.sh <src> <out> ums` makes a U-Boot that exports `userdata` (= the pmOS disk image) to the PC as USB mass
storage at power-on; `fastboot boot` it and the PC sees `pmOS_boot` + `pmOS_root` (fsck, mount, fix, unmount). A volume
key press ends it and U-Boot boots on. `ums 0 blkmap 0` does not work (the phone resets to fastboot). Pack it with the DTB
from the packaged `u-boot.img`: ABL silently refused images packed with the r29t (r30) DTB file, and after a refused
`fastboot boot` the next one fails until fastboot is re-entered with Power + Volume-down.

## Workarounds still in place (the user wants as few as possible; fix causes, record any new shortcut)

| Workaround | Proper fix |
|---|---|
| Wi-Fi and Bluetooth loaded by a service (`mojito-wifi`), modules blacklisted from udev autoload | the order is a firmware rule (below); needs a kernel-visible "sensor PD served" signal before it can be expressed in the drivers |
| "No DSP request for 3 s" means the sensor PD is served (hexagonrpcd-mojito's `served` marker) | a real ready notification from hexagonrpcd (propose with the patch upstream) |
| Plain wallpaper (the default JPEG XL one locks up the phone at login) | find why glycin-jxl exhausts memory into a hard lock-up |
| `aw87xxx-seq` amplifier driver replaying vendor register tables | load the vendor profiles in a mainline Awinic driver |
| SMMU identity domain (0006), stopping the bootloader timing engine (0007) | upstreamable fixes |
| hexagonrpcd patch not upstream | send it |

Wi-Fi/BT ordering, findings 2026-11-27 (all tests reverted). Structure since device 2-r4 / hexagonrpcd-mojito r3:
`hexagonrpcd-mojito` (OpenRC, user fastrpc, secure node, after QMI 69) -> `/run/hexagonrpcd-mojito/served` -> `mojito-wifi`
(ath10k_snoc, then hci_uart after wlan0) and `mojito-sensors` (iio-sensor-proxy). Verified on a clean boot: no 119, Wi-Fi
connected, BT powered, sensors up. The stock hexagonrpcd-adsp-sensorspd service hard-codes `/dev/fastrpc-adsp` and the
unpatched binary; making the node configurable there is a small pmaports change worth proposing.
- Not the WCN reference clock: with `clocks = <&rpmhcc RPMH_RF_CLK2>` on the wcn3990-pmu node (sequencer "clock-enable" unit)
  and as `cxo_ref_clk_pin` on the wifi node, an early `hci_uart` (6 s) still failed and Wi-Fi then got 119. RPMh keeps the
  RF clocks on anyway.
- `hci_uart` loaded right after QMI 69 (9.5 s, before ath10k): first power-on fails, the retry works (12.3 s); then
  bluetoothd's power-cycle drops the PMU rails and BT and WLAN are both dead for the boot (119 at 14.5 s).
- With ath10k loaded first (normal order) BT power cycles are reliable (5/5): ath10k's wlan pwrseq vote keeps the shared
  PMU rails up. So the real rule is "the WCN rails must stay up once the modem has initialised the chip" (stock icnss
  votes them at boot). Proper fix direction: ath10k_snoc loadable early (retry the capability request on 119 instead of
  failing), so it holds the rails from boot; then BT can autoload.

Already removed: `clk_ignore_unused` (2026-11-27: the simple-framebuffer node now holds the 8 scan-out clocks; the
23 clocks the cleanup turns off are off in stock Android too, per its boot clock trace), hand-installed files and the borrowed downstream initramfs (device package `mojito-device`), `pd_ignore_unused`, discarded sensor-registry writes, log-line readiness guessing, numeric `RX HPH Mode`,
hand-added `audio video input` user groups (same mechanism), greeter PulseAudio `autospawn = no` (not needed: elogind's uaccess ACLs hand `/dev/snd` to the user session; verified with a
test sound 2026-11-27. The greeter's PulseAudio does NOT exit at login: its feedbackd keeps it alive, and elogind does not kill
a closed session's processes. It keeps only `controlC0` open, no PCM; stock pmOS/phrog behaviour, harmless).

## The phone (slot B; slot A retired)

- `boot_b`: U-Boot (`u-boot-xiaomi-mojito`); `dtbo_b` erased. `qbootctl` marks each boot successful. Slot A (downstream)
  is retired; its kernel package is gone.
- Packages: `device-xiaomi-mojito` (mainline, private repo `mojito-device`), `linux-postmarketos-qcom-sm6150`,
  `firmware-xiaomi-mojito-mainline` (repo `258ryan/mojito-firmware`; EFS images are in no repo), `hexagonrpcd-mojito`
  (state in `/var/lib/hexagonrpcd/mojito`), `u-boot-xiaomi-mojito`. Still added by hand: `bootmac i2c-tools libgpiod
  bluez-btmgmt wlr-randr postmarketos-ui-phosh gmobile swclock-offset`, modem userspace (`tools/install-modem-userspace.sh`).
- Rootfs grown by hand to the full userdata partition (a clean install does not do this yet).
- SSH is OpenSSH (`sshd` in the default runlevel). The downstream port used dropbear from
  `postmarketos-base-downstream-dropbear`; removing the downstream packages removed it, so `sshd` was enabled by hand.
- User `user` has the pmOS default groups only (elogind's uaccess ACLs give the active session sound, display and input).
  PulseAudio (not PipeWire) drives the card.

## Workflow

The agent may run `pmbootstrap build` with the user's sudo password (askpass from the session; never stored). Ask for the
phone SSH password each session; never store it.

1. DTS change: `python3 tools/regen-dts-patch.py`; DTS-only test without a build: `mainline/build-dtb.sh <linux-tree> out.dtb`.
2. Kernel change: add or edit patches, bump `pkgrel`, update `sha512sums`; device/firmware/U-Boot changes go in the private
   repos. `mojito-device/tools/sync-to-pmaports.sh` copies all packages into pmaports.
3. `pmbootstrap build <pkg>` (~3 min for `.c`-only kernel changes, ~13 min after config/header changes).
4. Copy the apks to the phone over Wi-Fi (`ssh ... 'cat > /var/tmp/x.apk' < x.apk`), `apk add --simulate` first and read
   **all** of its output (the purges come first), then `apk add`. boot-deploy updates `/boot`; reboot; check `uname -v`.
5. Rollback: the previous kernel apk; or boot the fallback `/boot/boot.img` with `fastboot boot`; or the UMS rescue U-Boot.

Testing rules learned: give an audible or visible positive control before asking the user to judge a test (Phosh sound test for
audio); keep tones quiet and short; make trial settings revert themselves; ask before reboots or sleep tests.

## Hazards

- Hang/crash: TLMM pins 0-3 and 6-9; an `mdss` `resets` line; `rmmod msm`; LPASS 0x62b40000; reading the modem carve-out
  (0x8b000000) or `dd` of `modemst*`/`fsg`/`fsc`.
- Do not restart the modem while IPA is up (stalls, never recovers: reboot).
- Large transfers over USB networking can freeze the phone; use Wi-Fi. USB networking sometimes drops while the phone is fine.
- A stuck phone: Power + Volume-down for 10-15 s reaches fastboot. No log survives a reset.
- The speakers have no protection algorithm.
- One-shot test boots: a systemd-boot entry `<name>+1-0.conf` (sort-key before `postmarketOS`, no loader.conf) boots once;
  systemd-boot renames it `+0-1` and the next boot falls back to `pmos.conf`. Used for the `clk_ignore_unused` tests.
- Live SoundWire debugfs register writes leave the codec's register cache stale; reboot before judging anything after them.
- The clock starts in 1970 until swclock/NTP; meson and similar reject "future" timestamps (`tar -m`).
- `pkill -f pattern` kills the calling shell if its command line contains the pattern.
- `timeout N sh -c 'a | b'` kills only the shell; the pipeline keeps running (load tests: `pkill -x sha256sum` after).
- 2026-11-27, kernel r29 (ABL boot): CPU1 stopped answering (RCU stall, no NMI response) ~2 min after reformatting
  `/boot` and writing ~50 MB to it; writeback on `loop0` hung, `sync` and reboot hung, only a hard reset helped (data
  survived). Not seen on r31 yet; watch for `rcu_preempt detected stalls`.

## Public repository

No firmware, boot images, device dumps, device identifiers, carrier or network details, or passwords. Commit as
`258ryan <20981851+258ryan@users.noreply.github.com>`. The user's standing rule: commit and push whenever something works or is
close to working. Private working files are on the build PC under `~/.claude-work/pmos-mojito/` (audio work, boot images and
rollbacks in `audio-speaker-2026-11-27/`).
