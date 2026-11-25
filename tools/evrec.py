import os, select, struct, time, sys
devs = {}
for n in sorted(os.listdir("/sys/class/input")):
    if n.startswith("event"):
        name = open(f"/sys/class/input/{n}/device/name").read().strip()
        devs[os.open(f"/dev/input/{n}", os.O_RDONLY | os.O_NONBLOCK)] = name
KEYS = {114: "VOLUME_DOWN", 115: "VOLUME_UP", 116: "POWER", 330: "BTN_TOUCH"}
stats = {}
end = time.time() + float(sys.argv[1])
while time.time() < end:
    r, _, _ = select.select(list(devs), [], [], 0.5)
    for fd in r:
        try:
            data = os.read(fd, 24 * 64)
        except BlockingIOError:
            continue
        for i in range(0, len(data) - 23, 24):
            _, _, t, c, v = struct.unpack("llHHi", data[i:i + 24])
            d = devs[fd]
            s = stats.setdefault(d, {"events": 0, "keys": [], "x": [], "y": []})
            s["events"] += 1
            if t == 1 and v in (0, 1):
                s["keys"].append(f"{KEYS.get(c, c)}:{'down' if v else 'up'}")
            if t == 3 and c == 53: s["x"].append(v)
            if t == 3 and c == 54: s["y"].append(v)
for d, s in stats.items():
    rng = ""
    if s["x"]: rng = f" x={min(s['x'])}..{max(s['x'])} y={min(s['y'] or [0])}..{max(s['y'] or [0])} points={len(s['x'])}"
    print(f"{d}: {s['events']} events{rng}")
    if s["keys"]: print("   keys:", " ".join(s["keys"][:30]))
if not stats: print("no input events")
