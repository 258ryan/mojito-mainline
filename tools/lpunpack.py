# Minimal lpunpack: list/extract logical partitions from a raw Android super image.
import struct, sys
src, outdir = sys.argv[1], sys.argv[2]
want = set(sys.argv[3:])
f = open(src, "rb")
f.seek(4096); g = f.read(4096)
assert struct.unpack("<I", g[:4])[0] == 0x616C4467, "no LP geometry"
meta_max, slots, lbs = struct.unpack("<III", g[40:52])
base = 4096 + 4096 * 2
f.seek(base); h = f.read(256)
magic, major, minor, hsize = struct.unpack("<IHHI", h[:12])
assert magic == 0x414C5030, hex(magic)
tsize = struct.unpack("<I", h[44:48])[0]
desc = [struct.unpack("<III", h[80 + 12 * i:92 + 12 * i]) for i in range(4)]
f.seek(base + hsize); t = f.read(tsize)
(po, pn, ps), (eo, en, es) = desc[0], desc[1]
exts = [struct.unpack("<QIQI", t[eo + i * es:eo + i * es + 24]) for i in range(en)]
for i in range(pn):
    e = t[po + i * ps:po + (i + 1) * ps]
    name = e[:36].rstrip(b"\0").decode()
    attr, first, num, grp = struct.unpack("<IIII", e[36:52])
    size = sum(exts[j][0] for j in range(first, first + num)) * 512
    print(f"{name:20s} {size/1048576:9.1f} MiB extents={num}")
    if name in want and size:
        with open(f"{outdir}/{name}.img", "wb") as o:
            for j in range(first, first + num):
                ns, ttype, tdata, tsrc = exts[j]
                f.seek(tdata * 512); left = ns * 512
                while left:
                    b = f.read(min(left, 1 << 24)); o.write(b); left -= len(b)
        print("  -> extracted")
