import json,os,time
from pathlib import Path
class Ledger:
 def __init__(self,path,ack,root,boot,event):
  self.path=Path(path);self.ack=Path(ack);self.root=root;self.boot=boot;self.event=event;self.offset=0;self.accepted={};self.rejected={};self.known={(root['pid'],root['start_ticks']):root};self.rows=[]
 def read(self,table,monitor_known=()):
  if not self.path.exists():return
  with self.path.open() as f:
   f.seek(self.offset);lines=[]
   while True:
    start=f.tell();line=f.readline()
    if not line:break
    if not line.endswith('\n'):f.seek(start);break
    lines.append(line)
   self.offset=f.tell()
  for line in lines:
   try:r=json.loads(line);p=r['identity'];parent=r['parent'];k=(p['pid'],p['starttick']);pk=(parent['pid'],parent['starttick']);key=f'{k[0]}:{k[1]}';current=table.get(p['pid']);why=None
   except Exception as e:self.event('registration_parse_failure',error=str(e));continue
   if r['boot_id']!=self.boot:why='BOOT_MISMATCH'
   elif (r['root']['pid'],r['root']['starttick'])!=(self.root['pid'],self.root['start_ticks']):why='ROOT_MISMATCH'
   elif pk not in self.known or p['ppid']!=parent['pid']:why='UNKNOWN_PARENT'
   elif p['pid']==os.getpid():why='MONITOR_FORBIDDEN'
   elif current and current['start_ticks']!=p['starttick']:why='PID_REUSED'
   if why:self.rejected[key]=why;self.event('registration_refused',record=r,reason=why);continue
   self.known[k]={'pid':p['pid'],'start_ticks':p['starttick'],'origin':'node_ledger','parent_identity':pk}
   self.accepted[key]={'parent':parent,'root':r['root'],'UTC':r['UTC'],'received_monotonic':time.monotonic(),'currently_present':current is not None};self.rows.append(r);self.event('registration_accepted',record=r,current=current)
  known=set(self.known)|set(monitor_known);unknown=[v for v in table.values() if v.get('ppid')==os.getpid() and (v['pid'],v['start_ticks']) not in known];tmp=self.ack.with_suffix('.tmp');tmp.write_text(json.dumps({'boot_id':self.boot,'accepted':self.accepted,'rejected':self.rejected,'unknown_adopted':unknown,'registered_live':self.live(table)}));os.replace(tmp,self.ack)
 def live(self,table):return [table[p] for p,t in self.known if table.get(p,{}).get('start_ticks')==t]
