#!/usr/bin/env python3
# Compare two dpudump.py outputs block by block.   usage: cmpdump.py <a.txt> <b.txt> [block ...]
import re,sys
def parse(p):
    d={};cur=None
    for l in open(p):
        m=re.match(r"=+(\S+?)=+$",l.strip())
        if m: cur=m.group(1); d[cur]={}; continue
        m=re.match(r"(0x[0-9a-f]+) : (.*)",l.strip())
        if m and cur:
            o=int(m.group(1),16)
            for i,w in enumerate(m.group(2).split()): d[cur][o+4*i]=int(w,16)
    return d
a=parse(sys.argv[1]); b=parse(sys.argv[2]); want=sys.argv[3:] or list(a)
for k in want:
    rows=[(o,a[k][o],b.get(k,{}).get(o)) for o in sorted(a[k]) if o in b.get(k,{}) and a[k][o]!=b[k][o]]
    print("== %s: %d differing words"%(k,len(rows)))
    for o,x,y in rows[:80]: print("   +0x%03x  a=%08x  b=%08x"%(o,x,y))
