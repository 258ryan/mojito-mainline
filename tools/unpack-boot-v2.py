#!/usr/bin/env python3
# Split a header v2 boot image: unpack-boot-v2.py <boot.img> <outdir>  (writes kernel, ramdisk, dtb, cmdline)
import struct,sys,os
img=open(sys.argv[1],'rb').read(); out=sys.argv[2]; os.makedirs(out,exist_ok=True)
assert img[:8]==b'ANDROID!'
ks,ka,rs,ra,ss,sa,ta,ps,hv,osv=struct.unpack_from('<10I',img,8)
cmd=img[64:64+512].split(b'\0')[0]; extra=img[608+32:608+32+1024].split(b'\0')[0]
o=1632; rds,=struct.unpack_from('<I',img,o); rdo,=struct.unpack_from('<Q',img,o+4); hs,=struct.unpack_from('<I',img,o+12)
ds,=struct.unpack_from('<I',img,o+16); da,=struct.unpack_from('<Q',img,o+20)
pg=lambda n:(n+ps-1)//ps*ps
p=ps; open(out+'/kernel','wb').write(img[p:p+ks]); p+=pg(ks)
open(out+'/ramdisk','wb').write(img[p:p+rs]); p+=pg(rs); p+=pg(ss); p+=pg(rds)
open(out+'/dtb','wb').write(img[p:p+ds])
print(f"hv={hv} ps={ps} kaddr={ka:#x} raddr={ra:#x} taddr={ta:#x} daddr={da:#x} ks={ks} rs={rs} ds={ds}")
open(out+'/cmdline','wb').write(cmd+extra)
