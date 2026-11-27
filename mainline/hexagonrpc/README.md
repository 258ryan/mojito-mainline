# hexagonrpcd for the Redmi Note 10

The ADSP sensor PD writes its parsed registry (a temporary file, then a rename), and Wi-Fi only comes up after the PD has been
served. Upstream hexagonrpcd 0.4.0 refuses every write, so the PD retried for ~35 s. The patch (on tag `v0.4.0`):

- `-w DIR`: `persist/sensors/registry` is the writable DIR (it holds `registry/`), as on the vendor system. Everything else
  stays read-only. Adds `fwrite` and `frename`, and dispatches extended method numbers.
- Receives input buffers larger than 256 bytes (`adsp_listener_get_in_bufs2`).
- `-i FILE`: creates FILE once requests have stopped for 3 s. This is the readiness signal for Wi-Fi and the sensors.

`rootfs/etc/init.d/mojito-wifi` needs this build as `/usr/local/bin/hexagonrpcd-mojito`; it seeds
`/var/lib/hexagonrpcd/mojito/registry` once from the firmware package (delete that directory to start over).

Measured on the phone with a saved registry (one boot): idle marker 15 s after boot, Wi-Fi 18 s, Bluetooth 19 s, no server
errors, sensors read. Not sent upstream yet.

Build on the phone (use `tar -m` for copied sources if the clock is wrong; meson rejects future timestamps):

    apk add --virtual .hexbuild build-base meson linux-headers
    git clone https://github.com/linux-msm/hexagonrpc && cd hexagonrpc && git checkout v0.4.0
    git apply 0001-hexagonrpcd-writable-registry-large-inputs-rename-idle-marker.patch
    meson setup build && ninja -C build && meson test -C build
    install -m755 build/hexagonrpcd/hexagonrpcd /usr/local/bin/hexagonrpcd-mojito

`test-writable-registry.c` exercises the write path and its limits on a PC (link it with `hexagonfs*.c` and `rpcd_builder.c`,
`-D_GNU_SOURCE -fsanitize=address,undefined`; run it in an empty directory containing `fw/sensors/{config,registry}`,
`fw/sensors/sns_reg.conf` and `state/registry/`).
