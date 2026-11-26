#!/usr/bin/env python3
"""Slot A (downstream 4.14) probe: power the WCN chip through rfkill 'bt_power' and ask it for its
version over the Bluetooth UART. Touches only that rfkill switch and the ttyHS port(s). Run as root.
"""
import builtins, fcntl, glob, os, select, signal, struct, sys, termios, time

LOG = open(sys.argv[1] if len(sys.argv) > 1 else "/home/user/btprobe.log", "a")


def print(*args, **_):                          # every line reaches the disk before the next step
    builtins.print(*args, flush=True)
    builtins.print(*args, file=LOG, flush=True)
    os.fsync(LOG.fileno())


def step(text):
    print(f"step {time.monotonic():.3f} {text}")

TIOCPMGET, TIOCPMPUT = 0x544D, 0x544E          # msm_geni_serial clock votes
BAUD = {2400: termios.B2400, 115200: termios.B115200}
VER_CMD = bytes([0x01, 0x00, 0xFC, 0x01, 0x19])  # QCA EDL patch version request


def read(path):
    try:
        with open(path) as f:
            return f.read().strip()
    except OSError:
        return "?"


rfkill = next((d for d in glob.glob("/sys/class/rfkill/rfkill*") if read(d + "/name") == "bt_power"), None)
if not rfkill:
    raise SystemExit("no bt_power rfkill switch")


def power(on):
    step(f"rfkill {'on' if on else 'off'}")
    with open(rfkill + "/state", "w") as f:
        f.write("1" if on else "0")


def rails(tag):
    out = []
    for d in sorted(glob.glob("/sys/class/regulator/regulator.*")):
        name = read(d + "/name")
        if any(name.endswith(s) for s in ("_l1", "_l2", "_l9", "_l10", "l1c", "l2c", "l9a", "l10a", "l10c")):
            out.append(f"{name}={read(d + '/state')}/{read(d + '/microvolts')}uV/users={read(d + '/num_users')}")
    print(f"[{tag}] {' '.join(out) or 'no matching regulators'}")


def setup(fd, baud, rtscts):
    a = termios.tcgetattr(fd)
    a[0] = a[1] = a[3] = 0
    a[2] = termios.CS8 | termios.CREAD | termios.CLOCAL | (termios.CRTSCTS if rtscts else 0)
    a[4] = a[5] = BAUD[baud]
    a[6][termios.VMIN] = a[6][termios.VTIME] = 0
    termios.tcsetattr(fd, termios.TCSANOW, a)


def drain(fd, secs):
    out, end = b"", time.time() + secs
    while time.time() < end:
        if select.select([fd], [], [], 0.05)[0]:
            out += os.read(fd, 256)
    return out


def alarm(*_):
    raise TimeoutError


signal.signal(signal.SIGALRM, alarm)


def send(fd, data):
    signal.alarm(2)
    try:
        os.write(fd, data)
        termios.tcdrain(fd)
    except (TimeoutError, BlockingIOError):
        print("   write blocked (CTS never asserted)", flush=True)
    finally:
        signal.alarm(0)


def cts(fd):
    v = struct.unpack("I", fcntl.ioctl(fd, termios.TIOCMGET, bytes(4)))[0]
    return "CTS" if v & termios.TIOCM_CTS else "cts"


def trial(tty, name, off_pulse=True, on_baud=115200, rtscts=True, settle=0.1):
    power(False)
    time.sleep(0.5)
    power(True)
    time.sleep(0.2)
    got = {}
    step(f"open {tty} ({name})")
    signal.alarm(8)
    try:
        fd = os.open(tty, os.O_RDWR | os.O_NOCTTY | os.O_NONBLOCK)
    except (OSError, TimeoutError) as e:
        print(f"{tty} {name}: open failed: {e!r}", flush=True)
        return
    finally:
        signal.alarm(0)
    try:
        step("clock vote")
        try:
            fcntl.ioctl(fd, TIOCPMGET)
            vote = "voted"
        except OSError as e:
            vote = f"vote failed ({e.errno})"
        step("serial setup and pulses")
        setup(fd, 2400, False)
        if off_pulse:
            send(fd, b"\xC0")
            time.sleep(0.01)
        setup(fd, on_baud, False)
        send(fd, b"\xFC")
        time.sleep(settle)
        got["pulse"] = drain(fd, 0.05)
        setup(fd, 115200, rtscts)
        fcntl.ioctl(fd, termios.TIOCMBIS, struct.pack("I", termios.TIOCM_RTS))
        termios.tcflush(fd, termios.TCIFLUSH)
        line = cts(fd)
        step("send version request")
        send(fd, VER_CMD)
        got["reply"] = drain(fd, 1.0)
        rx = " ".join(f"{k}={v.hex()}" for k, v in got.items() if v)
        print(f"{tty} {name:22s} {vote} {line} | {rx or 'no rx'}", flush=True)
        rails("during " + name)
    finally:
        try:
            fcntl.ioctl(fd, TIOCPMPUT)
        except OSError:
            pass
        os.close(fd)


print("kernel", os.uname().release, "rfkill", rfkill, "state", read(rfkill + "/state"))
step("list ttys")
ttys = sorted(glob.glob("/dev/ttyHS*"))
print("ttys", ttys)
rails("before")
for tty in ttys:
    trial(tty, "HAL sequence")
    trial(tty, "on-pulse@2400", on_baud=2400)
    trial(tty, "no flow control", rtscts=False)
    trial(tty, "settle 500ms", settle=0.5)
power(False)
time.sleep(0.5)
rails("after power off")
