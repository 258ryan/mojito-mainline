#!/usr/bin/env python3
"""Log edges on TLMM gpio102 (WCN SW_CTRL) and WCN PMIC rail register changes next to ath10k/WLAN kernel messages.

Run as root on the phone BEFORE loading ath10k_snoc:  gpiowatch.py [seconds]
Only line 102 is requested (input); no other pin is touched.
"""
import fcntl, glob, os, re, select, struct, sys, time

LINE = 102
INPUT, RISING, FALLING = 1 << 2, 1 << 4, 1 << 5


def ioc(direction, nr, size):
    return direction << 30 | size << 16 | 0xB4 << 8 | nr


def tlmm():
    for path in sorted(glob.glob("/dev/gpiochip*")):
        fd = os.open(path, os.O_RDONLY)
        info = fcntl.ioctl(fd, ioc(2, 0x01, 68), bytes(68))
        label, lines = info[32:64].rstrip(b"\0").decode(), struct.unpack_from("<I", info, 64)[0]
        if lines > LINE and "pinctrl" in label:
            print(f"# {path} {label} ({lines} lines)")
            return fd
        os.close(fd)
    sys.exit("TLMM gpiochip not found")


chip = tlmm()
req = bytearray(592)
struct.pack_into("<I", req, 0, LINE)                       # offsets[0]
req[256:256 + 9] = b"gpiowatch"                            # consumer
struct.pack_into("<Q", req, 288, INPUT | RISING | FALLING)  # config.flags
struct.pack_into("<II", req, 560, 1, 256)                  # num_lines, event_buffer_size
fcntl.ioctl(chip, ioc(3, 0x07, len(req)), req)
line = struct.unpack_from("<i", req, 588)[0]


def level():
    return struct.unpack_from("<Q", fcntl.ioctl(line, ioc(3, 0x0E, 16), struct.pack("<QQ", 0, 1)))[0] & 1


kmsg = os.open("/dev/kmsg", os.O_RDONLY | os.O_NONBLOCK)
os.lseek(kmsg, 0, os.SEEK_END)
want = re.compile(r"ath10k|wlan|qmi|PDM|pwrseq|remoteproc", re.I)
print(f"# {time.monotonic():.6f} start, gpio{LINE}={level()}", flush=True)
# PMIC LDO registers (read-only, one 9-byte debugfs window each): bytes 0x40-0x47 plus status 0x08
RAILS = {"L9a": ("0-01", 0x4800), "L10a": ("0-01", 0x4900), "L1c": ("0-05", 0x4000),
         "L2c": ("0-05", 0x4100), "L10c": ("0-05", 0x4900), "L11c": ("0-05", 0x4a00)}
regs = {d: os.open(f"/sys/kernel/debug/regmap/{d}/registers", os.O_RDONLY) for d in ("0-01", "0-05")}
def rails():
    out = {}
    for name, (dev, base) in RAILS.items():
        v = [os.pread(regs[dev], 9, (base + o) * 9)[6:8].decode() for o in (*range(0x40, 0x48), 0x08)]
        out[name] = f"set[40-47]={' '.join(v[:8])} st={v[8]}"
    return out
last, polls = {}, 0
end = time.monotonic() + float(sys.argv[1] if len(sys.argv) > 1 else 40)
while (left := end - time.monotonic()) > 0:
    now = time.monotonic(); cur = rails(); polls += 1
    for name, v in cur.items():
        if last.get(name) != v:
            print(f"{now:.6f} RAIL {name} {v}", flush=True)
    last = cur
    for fd in select.select([line, kmsg], [], [], 0)[0]:
        if fd == line:
            data = os.read(line, 48 * 64)
            for off in range(0, len(data), 48):
                ts, kind, _, seq, _ = struct.unpack_from("<QIIII", data, off)
                print(f"{ts / 1e9:.6f} GPIO {'rise' if kind == 1 else 'fall'} seq={seq}", flush=True)
        else:
            try:
                head, msg = os.read(kmsg, 8192).decode(errors="replace").split(";", 1)
            except BrokenPipeError:
                continue
            msg = msg.splitlines()[0]
            if want.search(msg):
                print(f"{int(head.split(',')[2]) / 1e6:.6f} KMSG {msg}", flush=True)
print(f"# polls={polls}")
print(f"# {time.monotonic():.6f} end, gpio{LINE}={level()}")
