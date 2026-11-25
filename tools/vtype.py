# Type text into the console through a temporary virtual uinput keyboard.
import fcntl, os, struct, sys, time
UI_SET_EVBIT, UI_SET_KEYBIT = 0x40045564, 0x40045565
UI_DEV_CREATE, UI_DEV_DESTROY = 0x5501, 0x5502
EV_SYN, EV_KEY = 0, 1
K = {c: v for c, v in zip("1234567890", [2,3,4,5,6,7,8,9,10,11])}
K.update(dict(zip("qwertyuiop", range(16, 26))))
K.update(dict(zip("asdfghjkl", range(30, 39))))
K.update(dict(zip("zxcvbnm", range(44, 51))))
K["\n"] = 28; K[" "] = 57; K["-"] = 12; K["."] = 52; K["/"] = 53
fd = os.open("/dev/uinput", os.O_WRONLY | os.O_NONBLOCK)
fcntl.ioctl(fd, UI_SET_EVBIT, EV_KEY)
for code in range(1, 120):
    fcntl.ioctl(fd, UI_SET_KEYBIT, code)
dev = struct.pack("80sHHHHi", b"vtype-keyboard", 3, 1, 1, 1, 0) + b"\0" * (4 * 64 * 4)
os.write(fd, dev)
fcntl.ioctl(fd, UI_DEV_CREATE)
time.sleep(2.0)  # let kmscon hotplug the new keyboard
def ev(t, c, v):
    os.write(fd, struct.pack("llHHi", 0, 0, t, c, v))
for part in sys.argv[1:]:
    for ch in part.encode().decode("unicode_escape"):
        ev(EV_KEY, K[ch], 1); ev(EV_SYN, 0, 0)
        ev(EV_KEY, K[ch], 0); ev(EV_SYN, 0, 0)
        time.sleep(0.05)
    time.sleep(2.5)
time.sleep(0.5)
fcntl.ioctl(fd, UI_DEV_DESTROY)
os.close(fd)
