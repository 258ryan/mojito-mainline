#!/usr/bin/env python3
# Find the I2C adapter at 0x884000 and ask 0x38 (FocalTech) / 0x48 (Himax) whether anything answers.
import fcntl, glob, os, errno
I2C_SLAVE = 0x0703
bus = None
for d in sorted(glob.glob("/sys/class/i2c-dev/i2c-*")):
    real = os.path.realpath(d); name = open(d + "/name").read().strip()
    print("adapter", os.path.basename(d), name, "->", real.split("/")[-3] if "884000" in real else "")
    if "884000" in real: bus = os.path.basename(d).split("-")[1]
print("touch bus:", bus)
if bus is None: raise SystemExit("no adapter for 884000 (bus did not probe)")
def ask(addr, regs=()):
    fd = os.open("/dev/i2c-" + bus, os.O_RDWR)
    try:
        fcntl.ioctl(fd, I2C_SLAVE, addr)
        try: os.read(fd, 1); ack = True
        except OSError as e:
            return ("NACK" if e.errno in (errno.EREMOTEIO, errno.ENXIO, errno.EIO) else "error %s" % e), {}
        out = {}
        for r in regs:
            try: os.write(fd, bytes([r])); out[r] = os.read(fd, 1)[0]
            except OSError as e: out[r] = "err"
        return "ACK", out
    finally: os.close(fd)
for addr, label, regs in ((0x38, "FocalTech", (0xA3, 0x9F, 0xA0, 0xA6, 0xA8, 0xA1, 0xA2)), (0x48, "Himax", ())):
    st, regs_out = ask(addr, regs)
    print("addr 0x%02x (%s): %s %s" % (addr, label, st, {hex(k): (hex(v) if isinstance(v, int) else v) for k, v in regs_out.items()} or ""))
