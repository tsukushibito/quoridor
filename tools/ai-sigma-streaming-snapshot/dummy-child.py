import os,sys,time,signal,json,subprocess
if sys.argv[1]=='leaf':
 os.setsid();signal.signal(signal.SIGTERM,signal.SIG_IGN)
 print(json.dumps({'pid':os.getpid(),'pgid':os.getpgrp()}),flush=True)
 while True:time.sleep(.1)
else:
 p=subprocess.Popen([sys.executable,__file__,'leaf'])
 time.sleep(5)
