import subprocess,pathlib,json,hashlib,tarfile,io,os,time,datetime,resource
R=pathlib.Path(__file__).resolve().parents[2];D=R/'research-data/ai-sigma/142-wallless-oracle';start=datetime.datetime.now(datetime.timezone.utc).isoformat();tick=lambda pid:int(pathlib.Path(f'/proc/{pid}/stat').read_text().rsplit(')',1)[1].split()[19]);commands=[]
def gitbytes(path):
 cmd=['git','show','9143e12:'+path];p=subprocess.Popen(cmd,cwd=R,stdout=subprocess.PIPE,stderr=subprocess.PIPE);pt=tick(p.pid);b,e=p.communicate(timeout=20);commands.append({'cmd':cmd,'pid':p.pid,'starttick':pt,'exit':p.returncode});assert p.returncode==0,e;return b
manifest=json.loads(gitbytes('research-data/ai-sigma/142-wallless-oracle/archive-manifest.json'));b=gitbytes('research-data/ai-sigma/142-wallless-oracle/runs.tar.gz');assert hashlib.sha256(b).hexdigest()==manifest['sha256'];archive_members=0
with tarfile.open(fileobj=io.BytesIO(b),mode='r:gz') as t:
 for m in manifest['members']:
  x=t.extractfile(m['name']).read();assert len(x)==m['bytes'] and hashlib.sha256(x).hexdigest()==m['sha256'];archive_members+=1
for name in ['preregister.json','finite-results.json','runtime-source-stopped-before-report.json','resource-and-binding.json']:
 path='research-data/ai-sigma/142-wallless-oracle/'+name;assert gitbytes(path)==(R/path).read_bytes()
assert set(os.sched_getaffinity(0))=={0};assert resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024<939524096
result={'UTC_start':start,'UTC_end':datetime.datetime.now(datetime.timezone.utc).isoformat(),'self_pid':os.getpid(),'self_starttick':tick(os.getpid()),'data_git':'9143e12','archive_members_verified':archive_members,'canonical_Git_bytes_match':True,'commands':commands,'affinity':list(os.sched_getaffinity(0)),'ru_maxrss_bytes':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,'peak_not_current_RSS':True,'child_waited':True,'no_scientific_reexecution':True}
(D/'git-stream-restore-check.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
