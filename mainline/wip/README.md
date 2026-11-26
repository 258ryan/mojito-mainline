# Work in progress (not in the verified package)

The SMB5 charger driver that lived here is now patch 0008 of the kernel package (verified on hardware, see HANDOFF.md
"Battery, charging, ADSP, modem"). `charger-dts.txt` is kept as the original notes; the DTS now carries the real nodes.

## Wi-Fi: 0015-wifi-ath10k-qmi-register-for-pin-connect-result.patch

UNTESTED candidate fix for the WLFW capability rejection (QMI 119); see HANDOFF.md "Wi-Fi" and START HERE step 1 for the quick
module-only test.
