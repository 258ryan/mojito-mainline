import re,sys
# usage: d.py seg.s start end  -> compact listing with absolute targets/constants
f,a,b=sys.argv[1],int(sys.argv[2],16),int(sys.argv[3],16)
for l in open(f):
    m=re.match(r'^(b[0-9a-f]{7}):\s+(?:[0-9a-f]{2} ){3}[0-9a-f]{2}\s+[0-9a-f]{8}(.*)$',l.rstrip('\n'))
    if not m: continue
    ad=int(m[1],16)
    if not a<=ad<b: continue
    t=m[2].strip()
    if re.match(r'^\{?\s*immext',t): t='{' if t.startswith('{') else ''
    t=re.sub(r'(call|jump(?::n?t)?) 0x([0-9a-f]+)',lambda x:f'{x[1]} {0xb0000000+int(x[2],16):x}',t)
    t=re.sub(r'##-0x([0-9a-f]+)',lambda x:f'##{(-int(x[1],16))&0xffffffff:x}',t)
    print(f'{ad&0xffffff:06x} {t}')
