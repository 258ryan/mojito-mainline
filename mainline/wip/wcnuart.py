#!/usr/bin/env python3
# TEST ONLY: power the WCN3990 by hand and try UART start-up variants.
# Needs root, the regulator-output nodes (wcn-io/xo/rf/ch0/cxmx) and /dev/ttyHS1.
import os, sys, time, termios, fcntl, struct, select, glob

TTY = "/dev/ttyHS1"
ORDER = ["wcn-io", "wcn-xo", "wcn-rf", "wcn-ch0"]
BAUD = {2400: termios.B2400, 115200: termios.B115200, 3000000: termios.B3000000}
VER_CMD = bytes([0x01, 0x00, 0xFC, 0x01, 0x19])   # QCA EDL patch version request
HCI_RESET = bytes([0x01, 0x03, 0x0C, 0x00])


def rail(name, on):
    p = glob.glob(f"/sys/devices/platform/{name}/state") + glob.glob(f"/sys/devices/platform/*/{name}/state")
    with open(p[0], "w") as f:
        f.write("enabled" if on else "disabled")


def gpio(n):
    for line in open("/sys/kernel/debug/gpio"):
        if line.startswith(f" gpio{n} "):
            return "H" if " high " in line else "L"
    return "?"


def setup(fd, baud, rtscts):
    a = termios.tcgetattr(fd)
    a[0] = 0                      # iflag
    a[1] = 0                      # oflag
    a[2] = termios.CS8 | termios.CREAD | termios.CLOCAL | (termios.CRTSCTS if rtscts else 0)
    a[3] = 0                      # lflag
    a[4] = a[5] = BAUD[baud]
    a[6][termios.VMIN] = 0
    a[6][termios.VTIME] = 0
    termios.tcsetattr(fd, termios.TCSANOW, a)


def rts(fd, on):
    fcntl.ioctl(fd, termios.TIOCMBIS if on else termios.TIOCMBIC, struct.pack("I", termios.TIOCM_RTS))


def modem(fd):
    v = struct.unpack("I", fcntl.ioctl(fd, termios.TIOCMGET, struct.pack("I", 0)))[0]
    return "CTS" if v & termios.TIOCM_CTS else "cts"


def drain_read(fd, secs):
    out = b""
    end = time.time() + secs
    while time.time() < end:
        r, _, _ = select.select([fd], [], [], 0.05)
        if r:
            out += os.read(fd, 256)
    return out


def write(fd, data):
    import signal
    signal.signal(signal.SIGALRM, lambda *a: (_ for _ in ()).throw(TimeoutError()))
    signal.alarm(1)
    try:
        os.write(fd, data)
        termios.tcdrain(fd)
    except (TimeoutError, BlockingIOError):
        print("   (write blocked: CTS never asserted)", flush=True)
    finally:
        signal.alarm(0)


def trial(name, pulse_off=True, on_baud=115200, cmd_baud=115200, rtscts=False,
          cxmx=False, wait_after_on=0.1, rails_wait=0.05, cmd=VER_CMD):
    for r in ["wcn-cxmx"] + ORDER[::-1]:
        try:
            rail(r, False)
        except OSError:
            pass
    time.sleep(0.5)
    g0 = gpio(102)
    if os.environ.get("COLD") and g0 != "L":
        print(f"{name:34s} SKIPPED: sw_ctrl already high (not a cold start)", flush=True)
        return b""
    if cxmx:
        rail("wcn-cxmx", True)
    for r in ORDER:
        rail(r, True)
        time.sleep(rails_wait)
    fd = os.open(TTY, os.O_RDWR | os.O_NOCTTY | os.O_NONBLOCK)
    got = {}
    try:
        setup(fd, 2400, False)
        rts(fd, True)
        got["pwr"] = drain_read(fd, 0.05)
        if pulse_off:
            write(fd, b"\xC0")
            time.sleep(0.01)
        setup(fd, on_baud, False)
        write(fd, b"\xFC")
        time.sleep(wait_after_on)
        got["pulse"] = drain_read(fd, 0.05)
        setup(fd, cmd_baud, rtscts)
        rts(fd, True)
        termios.tcflush(fd, termios.TCIFLUSH)
        ctl = modem(fd)
        write(fd, cmd)
        got["reply"] = drain_read(fd, 0.8)
    finally:
        os.close(fd)
    g1 = gpio(102)
    rx = " ".join(f"{k}={v.hex()}" for k, v in got.items() if v)
    print(f"{name:34s} sw_ctrl {g0}->{g1} {ctl} | {rx or 'no rx'}", flush=True)
    return got.get("reply", b"")


V = [
    ("A mainline seq", {}),
    ("B on-pulse@2400", dict(on_baud=2400)),
    ("C no off-pulse", dict(pulse_off=False)),
    ("D no off, on@2400", dict(pulse_off=False, on_baud=2400)),
    ("E +cx-mx", dict(cxmx=True)),
    ("F +cx-mx on@2400", dict(cxmx=True, on_baud=2400)),
    ("G rtscts", dict(rtscts=True)),
    ("H wait 500ms after pulse", dict(wait_after_on=0.5)),
    ("I cmd@3M", dict(cmd_baud=3000000)),
    ("J no pulses at all", dict(pulse_off=False, on_baud=115200, cmd=VER_CMD)),
    ("K hci reset", dict(cmd=HCI_RESET)),
    ("L slow rails 20ms+cxmx on@2400 500ms", dict(cxmx=True, on_baud=2400, rails_wait=0.02, wait_after_on=0.5)),
]

sel = sys.argv[1:] or [v[0][0] for v in V]
for n, kw in V:
    if n[0] in sel:
        trial(n, **kw)
for r in ["wcn-cxmx"] + ORDER[::-1]:
    try:
        rail(r, False)
    except OSError:
        pass
