import sys,struct,collections
sys.path.insert(0,sys.argv[1]); from qrtrdecode import records,header,NAMES
CTRL=0xfffffffe; ports={}; pk=[]
for d,ts,o,p in records(open(sys.argv[2],'rb').read()):
    h=header(p)
    if not h: continue
    k,sn,sp,dn,dp,b=h; pk.append((d,ts,k,sn,sp,dn,dp,b))
    if k==4 and len(b)>=20:
        _,svc,inst,node,port=struct.unpack_from('<5I',b)
        if svc: ports.setdefault((node,port),(svc,inst,ts))
cap=next(ts for d,ts,k,sn,sp,dn,dp,b in pk if ports.get((dn,dp),(0,))[0]==0x45 and k==1 and len(b)>=7 and b[0]==0 and struct.unpack_from('<H',b,3)[0]==0x24)
print('first capability request at %.6f'%cap)
print('nodes seen:',sorted({sn for *_,sn,sp,dn,dp,b in pk if sn<100}))
print('\n== services announced before it (node: service/instance, first seen)')
for (node,port),(svc,inst,ts) in sorted(ports.items(),key=lambda x:(x[0][0],x[1][0])):
    if ts<cap: print(f'  node {node:2d} svc {svc:#06x} inst {inst:#x} port {port:#x} t={ts:.3f}')
print('\n== QMI request traffic between AP (node 1) and others before it:  who hosts the service <- who asks : msg ids (count, first time)')
t=collections.OrderedDict()
for d,ts,k,sn,sp,dn,dp,b in pk:
    if ts>=cap or k!=1 or sn==dn: continue
    if (dn,dp) in ports: host,svc,cli=dn,ports[(dn,dp)][0],sn
    elif (sn,sp) in ports: continue
    else: host,svc,cli=dn,None,sn
    if len(b)>=7 and b[0]==0: msg=struct.unpack_from('<H',b,3)[0]
    else: msg=None
    key=(host,svc,cli); e=t.setdefault(key,collections.OrderedDict()); c=e.setdefault(msg,[0,ts]); c[0]+=1
for (host,svc,cli),m in t.items():
    s=' '.join(f"{'raw' if k is None else '%#x'%k}x{v[0]}@{v[1]:.2f}" for k,v in list(m.items())[:10])
    print(f"  node{host} {('svc %#x %s'%(svc,NAMES.get(svc,''))) if svc else 'non-service port':28s} <- node{cli}: {s}")
