# Read-only: does each expected chip ACK on the i2c3 bus (0x88c000)? Reads one byte from register 0 only.
import fcntl,os,glob,errno
bus=[os.path.basename(d).split("-")[1] for d in glob.glob("/sys/class/i2c-dev/i2c-*") if "88c000" in os.path.realpath(d)][0]
print("bus i2c-%s (88c000)"%bus)
fd=os.open("/dev/i2c-"+bus,os.O_RDWR)
for addr,name in ((0x28,"wl2866d camera regulator"),(0x43,"fsa4480 USB-C audio switch"),(0x58,"aw87xxx PA #1"),(0x5b,"aw87xxx PA #2"),(0x65,"bq2597x charge pump")):
    fcntl.ioctl(fd,0x0703,addr)
    try:
        os.write(fd,bytes([0])); v=os.read(fd,1)
        print("0x%02x %-28s ACK reg0=0x%02x"%(addr,name,v[0]))
    except OSError as e:
        print("0x%02x %-28s no answer (%s)"%(addr,name,errno.errorcode.get(e.errno,e.errno)))
