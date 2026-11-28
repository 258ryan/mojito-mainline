# Firmware from the stock ROM

The port needs Xiaomi/Qualcomm firmware that this repository does not carry. Everything comes from Xiaomi's official
fastboot ROM for the Redmi Note 10, **`mojito_global_images_V14.0.9.0.SKGMIXM_20240616.0000.00_12.0_global`**
(MIUI 14, Android 12). Nothing below needs a rooted phone, a dump of your own phone or root on your PC.

Never mix in files from your own phone's `persist`, `modemst1/2`, `fsg` or EFS: they hold your IMEI and serials.

## 1. Unpack the ROM

```sh
tar xzf mojito_global_images_V14.0.9.0.SKGMIXM_*.tgz
cd mojito_global_images_*/images
simg2img super.img super.raw                 # android-sdk-libsparse-utils / simg2img
python3 <mojito-mainline>/tools/lpunpack.py super.raw . vendor_a   # -> vendor_a.img
```

You now have `NON-HLOS.bin`, `BTFM.bin`, `dspso.bin` (all in `images/`) and `vendor_a.img`.

## 2. Base firmware: modem, ADSP, GPU, IPA, Wi-Fi, Bluetooth, sensors

Use [firmware-xiaomi-mojito](https://github.com/258ryan/firmware-xiaomi-mojito), which is built from the same ROM:

```sh
git clone https://github.com/258ryan/firmware-xiaomi-mojito
cd firmware-xiaomi-mojito
mkdir in && cp <images>/{NON-HLOS.bin,BTFM.bin,dspso.bin} <images>/vendor_a.img in/
tools/build-tree.sh in tree/          # needs mtools, e2fsprogs
```

`tree/usr` is what the package `firmware-xiaomi-mojito-mainline` installs (`package/APKBUILD` builds it from a tagged
snapshot of that repository; see its README for the file-by-file table).

## 3. Call audio tables (only needed for voice calls)

Calls need the voice processing calibration for the handset mic and earpiece and the two custom voice topologies,
generated from Qualcomm's audio calibration database (ACDB) in `vendor_a.img`. The ACDB format is undocumented, so
`tools/acdb/` runs the vendor's own `libaudcal.so` (aarch64 Android library) under qemu-user with a ~100-line loader
and asks it for the same tables the stock audio HAL sends during a call.

Needs `e2fsprogs` (debugfs), `aarch64-linux-gnu-gcc`, `qemu-aarch64` (Debian/Ubuntu: `qemu-user`) and Python 3:

```sh
tools/acdb/extract-voice-cal.sh vendor_a.img voice-fw/
```

| Output | What it is (ACDB call) | Loaded by |
|---|---|---|
| `mojito-voice-static.bin` | vocproc static table, TX dev 4 / RX dev 7 (0x13096) | q6voice (CVP) |
| `mojito-voice-volume.bin` | vocproc "dynamic" = volume table (0x13094) | q6voice (CVP) |
| `mojito-voice-devcfg.bin` | vocproc device config (0x11397) | q6voice (CVP) |
| `mojito-voice-columns.bin` | column layout of the tables (0x1309A) | q6voice |
| `mojito-voice-stream.bin` | stream table (0x13098). **Not used**: it stalls calls, `stream_cal` stays off | q6voice (CVS) |
| `mojito-var_two.bin` | topologies 0x10000003 (handset mic) + 0x1000fffd (earpiece) from `IDP_Global_cal.acdb` | q6core `register_topologies` |

Copy them to `/lib/firmware/` on the phone (`/usr/lib/firmware`). The kernel side is the call patches in
`mainline/wip/calls/`, and `mainline/wip/calls/phone-setup/arm10.sh` sets the call parameters after boot
(see HANDOFF.md, "Update 2026-11-28").

Checked 2026-11-28: running the script on a clean ROM extraction reproduces, byte for byte, the files the
working phone used.

These files are vendor data. Generate them on your own machine; do not commit them here.
