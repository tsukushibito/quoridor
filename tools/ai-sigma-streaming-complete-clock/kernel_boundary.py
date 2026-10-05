import os,time
class Boundary:
 def __init__(self,launcher,boot,event):
  self.launcher=launcher;self.boot=boot;self.event=event;self.valid=True;self.spawn_count=0;self.reserved=False;self.root=None;self.ids={};self.adoptions=[]
  self.event('kernel_boundary_initial',launcher=launcher,boot_id=boot,initial_children=[],single_thread=True)
 def reserve_root(self):
  if self.root or self.spawn_count or self.reserved:self.valid=False;raise RuntimeError('SECOND_JOBROOT_FORBIDDEN')
  self.reserved=True
 def audit(self,event,args):
  if event in ('subprocess.Popen','os.fork','os.forkpty','os.posix_spawn'):
   if event!='subprocess.Popen' or not self.reserved or self.spawn_count:
    self.valid=False;self.event('launcher_spawn_refused',audit_event=event,spawn_count=self.spawn_count);raise RuntimeError('LAUNCHER_EXTRA_SPAWN_FORBIDDEN')
   self.spawn_count+=1
 def bind_root(self,p):
  assert self.reserved and self.spawn_count==1 and p['ppid']==self.launcher['pid'],'ROOT_BOOTSTRAP_FAILED'
  self.root=p;self.ids[(p['pid'],p['start_ticks'])]={'kind':'explicit_single_jobroot','observed':p};self.event('kernel_boundary_root_bound',proof=self.proof(),root=p)
 def proof(self):return {'valid':self.valid,'boot_id':self.boot,'launcher':self.launcher,'root':self.root,'initial_children':[],'spawn_count':self.spawn_count,'single_thread_initial':True,'sole_explicit_root':self.root is not None and self.spawn_count==1}
 def observe(self,t):
  if not self.root:return self.ids
  current=t.get(self.launcher['pid'])
  if not current or current['start_ticks']!=self.launcher['start_ticks'] or len(list(__import__('pathlib').Path('/proc/self/task').iterdir()))!=1:self.valid=False
  if self.valid:
   for p in t.values():
    k=(p['pid'],p['start_ticks'])
    if p['ppid']==self.launcher['pid'] and k not in self.ids:
     origin={'kind':'kernel_adopted_direct_child','observed':p,'launcher_identity':self.launcher,'sole_jobroot_identity':self.root,'boot_id':self.boot,'monotonic':time.monotonic()};self.ids[k]=origin;self.adoptions.append(origin);self.event('kernel_adoption_owned',origin=origin)
   live={pid for pid,tick in self.ids if t.get(pid,{}).get('start_ticks')==tick};more=True
   while more:
    more=False
    for p in t.values():
     if p['ppid'] in live and p['pid'] not in live:
      k=(p['pid'],p['start_ticks']);self.ids[k]={'kind':'observed_owned_parent_edge','observed':p,'parent':t[p['ppid']]};live.add(p['pid']);more=True
  return self.ids
 def may_wait(self,p):return p['ppid']==self.launcher['pid'] and (p['pid'],p['start_ticks']) in self.ids
