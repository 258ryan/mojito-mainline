import struct
import sys, os
d=open(os.environ.get('WLANMDSP','wlanmdsp.mbn'),'rb').read()
off=struct.unpack_from('<I',d,28)[0]; n=struct.unpack_from('<H',d,44)[0]
SEG=[struct.unpack_from('<6I',d,off+i*32) for i in range(n)]
SEG=[(v,fs,ms,o) for t,o,v,p,fs,ms in SEG if t==1]
def r(a,l=4):
    for v,fs,ms,o in SEG:
        if v<=a<v+fs: return d[o+a-v:o+a-v+l]
    return None
def w(a):
    b=r(a); return None if b is None else struct.unpack('<I',b)[0]
def s(a):
    b=r(a,80); return None if b is None else b.split(b'\0')[0]
