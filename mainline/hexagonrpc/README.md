# hexagonrpcd for the Redmi Note 10

The ADSP sensor PD rewrites its registry cache at every start. Stock hexagonrpcd 0.4.0 refuses every write, and the PD retries
for about 35 s, which delayed Wi-Fi to ~50 s after boot. The patch (on upstream tag `v0.4.0`) accepts writes and discards them,
fetches input buffers larger than 256 bytes, and ignores the rename that follows. Nothing on the phone is modified.
With it, `wlan0` appears about 20 s after boot (one measured boot; sensors read correctly afterwards).

Build on the phone (set the clock first or use `tar -m`; meson rejects timestamps in the future):

    apk add --virtual .hexbuild build-base meson linux-headers
    git clone https://github.com/linux-msm/hexagonrpc && cd hexagonrpc && git checkout v0.4.0
    git apply 0001-hexagonrpcd-accept-writes-large-inputs-and-rename.patch
    meson setup build && ninja -C build
    install -m755 build/hexagonrpcd/hexagonrpcd /usr/local/bin/hexagonrpcd-mojito

The binary links the distribution's libhexagonrpc 0.4. `rootfs/etc/init.d/mojito-wifi` uses it when present.
