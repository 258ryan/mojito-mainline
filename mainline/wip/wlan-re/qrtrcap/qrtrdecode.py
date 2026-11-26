#!/usr/bin/env python3
"""Turn a /proc/qrtrcap dump into a readable message list.

  qrtrdecode.py capture.bin                 every packet
  qrtrdecode.py capture.bin -s 0x45         only one QMI service (0x45 = WLFW, Wi-Fi)
  qrtrdecode.py capture.bin --services      the services announced, in order
"""
import argparse, struct, sys

MAGIC = 0x50414351
DIRS = {0: "RX ", 1: "TX ", 2: "LOC"}
TYPES = {1: "DATA", 2: "HELLO", 3: "BYE", 4: "NEW_SERVER", 5: "DEL_SERVER", 6: "DEL_CLIENT",
         7: "RESUME_TX", 8: "EXIT", 9: "PING", 10: "NEW_LOOKUP", 11: "DEL_LOOKUP"}
CTRL = 0xFFFFFFFE
KIND = {0: "req ", 2: "resp", 4: "ind "}
NAMES = {0x0E: "rmtfs", 0x22: "coexistence", 0x40: "servreg-locator", 0x42: "servreg-notifier",
         0x45: "WLFW (Wi-Fi)", 0x1000: "tftp"}


def records(blob):
    off = 0
    while off + 24 <= len(blob):
        magic, direction, ts, origlen, caplen = struct.unpack_from("<IIQII", blob, off)
        if magic != MAGIC or off + 24 + caplen > len(blob):
            print(f"# stopped at byte {off}: bad or truncated record", file=sys.stderr)
            return
        yield direction, ts / 1e9, origlen, blob[off + 24:off + 24 + caplen]
        off += 24 + (caplen + 3 & ~3)


def header(p):
    """-> (type, src_node, src_port, dst_node, dst_port, payload) or None"""
    if len(p) >= 32 and p[:4] == b"\x01\x00\x00\x00":
        _, kind, sn, sp, _, size, dn, dp = struct.unpack_from("<8I", p)
        return kind, sn, sp, dn, dp, p[32:32 + size]
    if len(p) >= 16 and p[0] == 3:                      # QRTR_PROTO_VER_2 on the wire
        _, kind, _, opt, size, sn, sp, dn, dp = struct.unpack_from("<4BI4H", p)
        sp = CTRL if sp == 0xFFFE else sp
        dp = CTRL if dp == 0xFFFE else dp
        return kind, sn, sp, dn, dp, p[16 + opt:16 + opt + size]
    return None


def tlvs(body):
    off, out = 0, []
    while off + 3 <= len(body):
        t, n = struct.unpack_from("<BH", body, off)
        out.append((t, body[off + 3:off + 3 + n], n))
        off += 3 + n
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("capture")
    ap.add_argument("-s", "--service", type=lambda v: int(v, 0))
    ap.add_argument("--services", action="store_true")
    ap.add_argument("--bytes", type=int, default=64, help="value bytes shown per TLV")
    a = ap.parse_args()
    ports = {}                                          # (node, port) -> service id
    count = shown = 0
    for direction, ts, origlen, packet in records(open(a.capture, "rb").read()):
        count += 1
        h = header(packet)
        if not h:
            if a.service is None and not a.services:
                print(f"{ts:12.6f} {DIRS.get(direction)} unparsed {origlen}B {packet[:32].hex()}")
            continue
        kind, sn, sp, dn, dp, body = h
        if kind in (4, 5) and len(body) >= 20:
            _, service, instance, node, port = struct.unpack_from("<5I", body)
            if kind == 4 and service:
                ports[(node, port)] = service
            if a.services or a.service in (None, service):
                print(f"{ts:12.6f} {DIRS.get(direction)} {TYPES[kind]:10s} service {service:#x} "
                      f"{NAMES.get(service, '')} instance {instance:#x} at {node}:{port}")
                shown += 1
            continue
        if a.services:
            continue
        service = ports.get((dn, dp)) or ports.get((sn, sp))
        if a.service is not None and service != a.service:
            continue
        where = f"{sn}:{sp:#x} > {dn}:{dp:#x}"
        name = "" if service is None else f"[{service:#x} {NAMES.get(service, '')}]".replace(" ]", "]")
        qmi = kind == 1 and len(body) >= 7 and body[0] in KIND and struct.unpack_from("<H", body, 5)[0] == len(body) - 7
        if qmi:
            flags, txn, msg, length = struct.unpack_from("<BHHH", body)
            print(f"{ts:12.6f} {DIRS.get(direction)} {where:22s} {name} {KIND[flags]} msg {msg:#06x} txn {txn} len {length}")
            for t, value, n in tlvs(body[7:]):
                note = ""
                if flags == 2 and t == 2 and n == 4:
                    result, error = struct.unpack("<HH", value)
                    note = f"  => result {result} error {error}"
                more = "..." if n > a.bytes else ""
                print(f"{'':17s}tlv {t:#04x} ({n}) {value[:a.bytes].hex()}{more}{note}")
        else:
            cut = "" if len(packet) == origlen else f" (kept {len(packet)} of {origlen})"
            print(f"{ts:12.6f} {DIRS.get(direction)} {where:22s} {name} {TYPES.get(kind, kind)} {len(body)}B "
                  f"{body[:48].hex()}{cut}")
        shown += 1
    print(f"# {count} packets read, {shown} shown", file=sys.stderr)


if __name__ == "__main__":
    main()
