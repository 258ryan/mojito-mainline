# postmarketOS on the Xiaomi Redmi Note 10 (mojito / sunny)

Two ports for the Redmi Note 10 (Qualcomm SM6150, Adreno 612):

- **`downstream/`** works: Xiaomi's 4.14 kernel boots postmarketOS (OpenRC), SSH over USB, a text console on
  the panel via kmscon, touch, buttons, vibrator, flashlight, battery readouts. No audio, modem, Wi-Fi or GPU.
- **`mainline/`** is in progress: Linux 7.4-rc4 with a new `sm6150-xiaomi-mojito.dts` on top of mainline's
  `talos.dtsi`. It does not boot yet; the goal is freedreno GPU acceleration for a KWin 6 / Qt 6 shell.

Start with [`HANDOFF.md`](HANDOFF.md): status, every fix that was needed, the mainline boot experiments,
next steps and the traps (read the NAT warning before giving the phone internet).

No firmware, boot images or device dumps are included: vendor blobs are not redistributable and dumps carry
device-unique identifiers. Extract firmware from your own phone's stock ROM (see `tools/lpunpack.py`).

## Credits

- [AbdulkareemQasem/Redmi-Note-10](https://github.com/AbdulkareemQasem/Redmi-Note-10): the original downstream
  postmarketOS packages this started from.
- [xiaomi-sdm678](https://github.com/xiaomi-sdm678): downstream kernel source.
- [VipinVIP/violet-sm6150-mainline](https://github.com/VipinVIP/violet-sm6150-mainline): mainline on the
  Redmi Note 7 Pro (same SoC); patches 0002 and 0003 come from there.
- postmarketOS / pmaports, and the upstream Linux Qualcomm maintainers for `talos.dtsi` and Adreno 612 support.

Flashing can brick a phone. Keep a working slot and your stock fastboot ROM.
