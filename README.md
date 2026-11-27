# postmarketOS on the Xiaomi Redmi Note 10 (mojito / sunny)

Qualcomm SM6150 (Snapdragon 678), Adreno 612.

## Mainline (`mainline/`): the active port

Linux 7.4-rc4 with `sm6150-xiaomi-mojito.dts` on top of mainline's `talos.dtsi`, postmarketOS (OpenRC) and Phosh.

| Works | Not yet, or unreliable |
|---|---|
| Display with brightness and smooth dimming, touch, GPU, Phosh | Calls |
| Wi-Fi, Bluetooth (setup sometimes fails), mobile data | Headphones, second microphone |
| Both speakers, main microphone (some hiss) | Camera, GPS, NFC, fingerprint |
| Accelerometer, light sensor, compass, auto-rotation | Charging from a PC USB port |
| Full CPU speed with thermal throttling | |
| Power and volume keys, vibrator | |
| Wall charging, battery percentage | |
| Suspend (only briefly tested) | |

It is a development port. The device, kernel, firmware and U-Boot packages exist, but a clean install from them has not been
tested yet (see "Build and install" below).

## Downstream (`downstream/`)

The earlier port on Xiaomi's 4.14 kernel: SSH over USB, a text console on the panel, touch, buttons, vibrator, flashlight and
battery readouts. No audio, modem, Wi-Fi or GPU.

## Layout

| Path | What |
|---|---|
| [`HANDOFF.md`](HANDOFF.md) | current state, open problems, workflow, hazards: start here |
| [`docs/HANDOFF-history.md`](docs/HANDOFF-history.md) | how each problem was found and fixed |
| `mainline/sm6150-xiaomi-mojito.dts` | board device tree (source of kernel patch 0001) |
| `mainline/linux-postmarketos-qcom-sm6150/` | kernel package and patches |
| `mainline/rootfs/` | services, sound configuration and other files for the phone |
| `mainline/hexagonrpc/` | patched DSP file server (needed for Wi-Fi and sensors) |
| `mainline/mk-bootimg-v2.sh`, `mainline/build-dtb.sh` | boot image and quick device-tree builds |
| `tools/` | install and debugging scripts |

No firmware, boot images or device dumps are included: vendor files are not redistributable and dumps carry device-unique
identifiers. Extract firmware from your own phone's stock ROM (see `tools/lpunpack.py`).

## Credits

- [AbdulkareemQasem/Redmi-Note-10](https://github.com/AbdulkareemQasem/Redmi-Note-10): the original downstream
  postmarketOS packages this started from.
- [xiaomi-sdm678](https://github.com/xiaomi-sdm678): downstream kernel source.
- [VipinVIP/violet-sm6150-mainline](https://github.com/VipinVIP/violet-sm6150-mainline): mainline on the
  Redmi Note 7 Pro (same SoC); patches 0002 and 0003 come from there.
- [linux-msm/hexagonrpc](https://github.com/linux-msm/hexagonrpc) (GPL-3.0).
- postmarketOS / pmaports, and the upstream Linux Qualcomm maintainers for `talos.dtsi` and Adreno 612 support.

Flashing can brick a phone. Keep a working slot and your stock fastboot ROM.

## Build and install postmarketOS (current state)

Needs: an unlocked Redmi Note 10 (mojito/sunny), `pmbootstrap`, `fastboot`. Repositories:
[mojito-mainline](https://github.com/258ryan/mojito-mainline) (kernel), [mojito-device](https://github.com/258ryan/mojito-device)
(device, hexagonrpcd, U-Boot packages), [firmware-xiaomi-mojito](https://github.com/258ryan/firmware-xiaomi-mojito) (firmware).

```
git clone https://github.com/258ryan/mojito-mainline
git clone https://github.com/258ryan/mojito-device
git clone https://github.com/258ryan/firmware-xiaomi-mojito
pmbootstrap init                      # vendor xiaomi, device mojito, UI phosh (any init once, to get pmaports)
mojito-device/tools/sync-to-pmaports.sh "$(pmbootstrap config aports)" mojito-mainline firmware-xiaomi-mojito/package
pmbootstrap init                      # again: now picks up the mainline device-xiaomi-mojito
pmbootstrap install --add u-boot-xiaomi-mojito

# take the U-Boot image out of the installed system
cp "$(pmbootstrap config work)/chroot_rootfs_xiaomi-mojito/usr/share/u-boot/xiaomi-mojito/u-boot.img" .

# phone in Xiaomi fastboot (Power + Volume down). This replaces boot_b and ERASES userdata:
fastboot erase dtbo_b
fastboot flash boot_b u-boot.img
fastboot set_active b
pmbootstrap flasher flash_rootfs      # the pmOS disk image into userdata (U-Boot finds it there)
fastboot reboot
```

Updates are `apk upgrade` (boot-deploy writes /boot; nothing is flashed again). Status, known problems and how things work:
[HANDOFF.md](HANDOFF.md). Not yet verified end to end from a clean `pmbootstrap install` (the reference phone was set up
incrementally); the public firmware package (v2, official ROM only) has not been booted yet.
