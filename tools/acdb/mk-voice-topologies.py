#!/usr/bin/env python3
# Build mojito-var_two.bin (the voice topologies q6core registers with the ADSP) from the stock IDP_Global_cal.acdb.
# The ACDB holds one list of custom topologies: u32 count, then entries {u32 version=2, u32 topology id, u32 flags,
# u32 module count, count x (u32 module id, u32 instance id)}. We keep the handset mic (0x10000003) and the earpiece
# (0x1000fffd) entries, in that order, as a list of the same format.
import struct, sys
WANT = (0x10000003, 0x1000FFFD)
d = open(sys.argv[1], 'rb').read()
def walk(o):
    n = struct.unpack_from('<I', d, o)[0]
    if not 1 <= n <= 500: return None
    p, ents = o + 4, {}
    for _ in range(n):
        if p + 16 > len(d): return None
        ver, tid, flags, nm = struct.unpack_from('<4I', d, p)
        if ver != 2 or nm > 64: return None
        ents[tid] = d[p:p + 16 + 8 * nm]; p += 16 + 8 * nm
    return ents
for o in range(0, len(d) - 20, 2):
    e = walk(o)
    if e and all(t in e for t in WANT):
        out = struct.pack('<I', len(WANT)) + b''.join(e[t] for t in WANT)
        open(sys.argv[2], 'wb').write(out); print(f'list at {o:#x}: {len(e)} topologies -> {sys.argv[2]} ({len(out)} bytes)'); break
else:
    sys.exit('topology list not found')
