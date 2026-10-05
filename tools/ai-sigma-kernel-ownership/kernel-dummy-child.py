import os,sys,time,signal,json
# No parked intermediate: two fast exits intentionally evade ancestry polling.
if os.fork():os._exit(0)
os.setsid()
if os.fork():os._exit(0)
signal.signal(signal.SIGTERM,signal.SIG_IGN)
with open(sys.argv[1],'w') as f:json.dump({'pid':os.getpid(),'ppid':os.getppid(),'pgid':os.getpgrp(),'boot_id':open('/proc/sys/kernel/random/boot_id').read().strip(),'starttick':int(open('/proc/self/stat').read().rsplit(')',1)[1].split()[19])},f)
while True:time.sleep(.01)
