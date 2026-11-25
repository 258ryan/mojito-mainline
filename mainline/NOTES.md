# Mainline port notes (Redmi Note 10 "sunny"/mojito, SM6150 = Talos)

Mainline baseline (checked 2026-11-25, Linux 7.4-rc4, torvalds 4dce97c6c265):
- arch/arm64/boot/dts/qcom/talos.dtsi (SoC), qcs615-ride.dts, talos-evk*.dts (reference boards)
- Adreno 612: drivers/gpu/drm/msm/adreno/a6xx_catalog.c (chip id 0x06010200, fw a612_rgmu.bin)
- DPU: disp/dpu1/catalog/dpu_5_3_sm6150.h
- Templates: sm6125-xiaomi-ginkgo/willow/laurel-sprout.dts
- No pmaports kernel package for SM6150 yet.

Device facts from the live downstream DT (downstream-dt/mojito-downstream-live.dts):
- Bootloader picks dtb_idx=5 (SM6150 base), dtbo_idx=16. hwname=sunny, hwc=GLOBAL_K7A.
- Panel: "k7 38 0c 0a video mode fhdp dsi panel" (node qcom,mdss_dsi_k7_38_0c_0a_video),
  1080x2400 video mode -> generate driver with linux-mdss-dsi-panel-driver-generator.
- Touch: compatible "focaltech,fts" (driver fts_ts), avdd gpio 0x60, reset 0x58, irq 0x59 (TLMM).
- PMICs: pm6150 (SID 0/1), pm6150l (SID 4/5), WLED on pm6150l (backlight).
- UFS at 1d84000.ufshc; USB dwc3 a600000.
- Firmware (stock ROM extract): ../stock/extract/fw*  (adsp, cdsp, modem, a612_zap, a612_rgmu, a630_sqe)

Plan: phase 1 boot (simple-framebuffer, UFS, USB net) on slot B; slot A keeps downstream.
Phase 2: DSI panel + GPU -> Mesa freedreno -> KWin 6 + Finder. Phase 3: touch, charging, audio, modem, wifi.
