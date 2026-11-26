# WLAN debugging tools and test trees (2026-11-27, second session)

Results are in HANDOFF.md, "Wi-Fi: second session". No firmware, dumps or logs here.

| File | What |
|---|---|
| `d.py`, `mem.py`, `NOTES-ccpm-2026-11-27.md` | static reading of `wlanmdsp.mbn` (`WLANMDSP=<file>` for mem.py) |
| `gpiowatch.py`, `wcnwatch.py` | on the phone: SW_CTRL (gpio102) edges, PMIC rail registers and kernel messages on one clock |
| `early-power.patch` | ath10k TEST: power the radio when WLFW appears (`early_power`, `early_delay_ms`) |
| `btprobe-downstream.py` | slot A: power through rfkill `bt_power`, ask the chip for its version |
| `kernel-7.2.10/mojito-on-7.2.10.patch` | the packaged patches rebased on linux 7.2.10 (built on a PC with `make LLVM=1`) |
| `dts/*.dtsi` | fragments appended to the board DTS for each test image |
| `qrtrcap/` | recorder for every QRTR packet (`/proc/qrtrcap`) on a 4.14 downstream kernel, and its decoder. Used on stock MIUI, see `stock-capture/` |
