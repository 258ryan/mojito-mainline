# WLAN firmware: CCPM / RF XO path (static analysis, wlanmdsp.mbn sha256 4b1510cc, no phone tests)

Corrects HANDOFF "Firmware RE": the ready flag 0xb0300ac0 is NOT set only by client-init.
- Image initial value is 1 (data segment). Only direct read: 0xb0147964. Only direct write: 0xb014b028.
- 0xb014b028 writes 1 on normal completion; writes 0 on the early exit at 0xb014ae38 (b0146400 returned 5).
- b0146400 = ccpm_rf_xo_enable (its log strings). Returns 5 after step 12 ("Wait WSI_CMD.RF_CMD_IP bit 31 to be 0",
  reg 0xfc0800e0) fails 5 retries; success path returns xo_type (and(reg 0xfc0800f8,3)).
- A (b0147d50 -> b01479a4 -> b014a8c0): after CCPM init it returns 0 on every path read (r18 zeroed at 0xb014ab08).
- B/C (b01478e8, type-1 client b0300300): b014a820 returns 0; fail only if flag != 1.
=> Inference: the 119 is exit B or C after client-init ran and RF XO enable failed. B's own walker (mask 5) matches no
   resource with a callback at node+0x34, so C (mask 2 = /icb/arbiter) is the likelier point. NOT PROVEN.

Resource table 0xb03010c8 (0x18 each; id = desc+4 low byte, subtype = next byte):
 1 /icb/arbiter (sub1), 2 wcn_ant_switch, 3 cpu/latency, 4 wcn_core, 6 wcn_pa, 7 wcn_pa_2, 8 wcss, 11 ccpm_mca (sub3),
 12 adrastea_clk (sub6), 13 /icb/alc (sub7), 14, 15, 17.
Callbacks installed at 0xb0148830.. (jump table 0xb02a4698): only sub6 gets +0x38 = b0148bdc (value==1 -> b014ada0).
Walker b0147670 filters by id bit, skips nodes with +0x34 == 0 (only subs 1,3,7 have it). Resources are applied by mask
via b014787c -> b0149070 (+0x2c) / b0149110 (+0x38/+0x3c). A applies mask 0x802 (ids 1, 11).

OPEN: what puts bit 12 (adrastea_clk) in an apply mask with value 1; whether delays (b003b4d8) account for ~200 ms
(step 12 alone is 5 x 6 x 1000 units).
Tools: d.py <objdump -d output> <start> <end>; exec mem.py for w()/r()/s() on image addresses.
