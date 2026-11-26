#!/usr/bin/env python3
# Dump the DPU/DSI/display-clock register blocks via /dev/mem (needs CONFIG_DEVMEM). Run as root on the phone:
#   python3 dpudump.py > dump.txt        (whole set)      python3 dpudump.py <name> <addr> <len>   (one block)
# Each block is read in its own process so a bus error only loses that block. Only read addresses known to be safe:
# a whole-GCC sweep and unknown ranges crashed the phone. Compare two dumps with cmpdump.py.
# Dump the DPU register blocks from /dev/mem in the same format as the mainline msm devcoredump.
import mmap,os,struct,subprocess,sys
MDP=0xae01000
BLOCKS=[("top",MDP+0x0,0x460),("ctl_0",MDP+0x1000,0x1e0),("ctl_1",MDP+0x1200,0x1e0),("ctl_2",MDP+0x1400,0x1e0),
 ("sspp_0",MDP+0x4000,0x1f0),("sspp_8",MDP+0x24000,0x1f0),("sspp_9",MDP+0x26000,0x1f0),("sspp_10",MDP+0x28000,0x1f0),("sspp_11",MDP+0x2a000,0x1f0),
 ("lm_0",MDP+0x44000,0x320),("lm_1",MDP+0x45000,0x320),("dspp_0",MDP+0x54000,0x200),
 ("pingpong_0",MDP+0x70000,0xd4),("pingpong_1",MDP+0x70800,0xd4),("pingpong_2",MDP+0x71000,0xd4),
 ("intf_0",MDP+0x6a000,0x280),("intf_1",MDP+0x6a800,0x2c0),("intf_3",MDP+0x6b800,0x280),
 ("vbif",0xaeb0000,0x400),("dsi0_ctrl",0xae94000,0x400),("dsi0_phy",0xae94400,0x100),("dsi0_lane",0xae94500,0x300),("dsi0_pll",0xae94800,0x124),("mdss_top",0xae00000,0x200),
 ("dispcc_a",0xaf00000,0x1000),("dispcc_b",0xaf01000,0x1000),("dispcc_c",0xaf02000,0x1000),("dispcc_d",0xaf03000,0x1000),("dispcc_e",0xaf04000,0x1000),("dispcc_f",0xaf05000,0x1000),("dispcc_g",0xaf06000,0x1000),("dispcc_h",0xaf07000,0x1000),("dispcc_i",0xaf08000,0x1000),("dispcc_j",0xaf09000,0x1000),
 ("gcc_disp",0x10b000,0x100),("gcc_disp2",0x10b100,0x100)]
def one(name,addr,ln):
    fd=os.open("/dev/mem",os.O_RDONLY|os.O_SYNC)
    pa=addr & ~0xfff; off=addr-pa
    m=mmap.mmap(fd,((off+ln+0xfff)//0x1000)*0x1000,mmap.MAP_SHARED,mmap.PROT_READ,offset=pa)
    print("====================%s================"%name)
    for o in range(0,ln,16):
        w=[struct.unpack("<I",m[off+o+4*i:off+o+4*i+4])[0] for i in range(4) if o+4*i<ln]
        print("0x%x : %s"%(o," ".join("%08x"%x for x in w)))
if len(sys.argv)>1:
    one(sys.argv[1],int(sys.argv[2],0),int(sys.argv[3],0)); sys.exit()
for n,a,l in BLOCKS:
    r=subprocess.run([sys.executable,__file__,n,hex(a),hex(l)],capture_output=True,text=True,timeout=20)
    if r.returncode==0: sys.stdout.write(r.stdout)
    else: print("====================%s================\nREAD FAILED rc=%s"%(n,r.returncode))
