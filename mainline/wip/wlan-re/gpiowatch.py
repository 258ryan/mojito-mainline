#!/usr/bin/env python3
"""Log edges on TLMM gpio102 (WCN SW_CTRL) next to ath10k/WLAN kernel messages.

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
end = time.monotonic() + float(sys.argv[1] if len(sys.argv) > 1 else 40)
while (left := end - time.monotonic()) > 0:
    for fd in select.select([line, kmsg], [], [], left)[0]:
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
print(f"# {time.monotonic():.6f} end, gpio{LINE}={level()}")
