import pathlib,json,subprocess,io,tarfile,hashlib,datetime
R=pathlib.Path(__file__).resolve().parents[2];O=R/'.artifacts/ai-sigma/resume-20261002/COOPERATIVE-ARENA-INDEPENDENT';B='research-data/ai-sigma/103-cooperative-arena/'
pairs=[('initial-pair-r1','9dd49a00c77133a199401fd84efdac6c60abcba7'),('asym-pair-r1','137b6bddd86eddfab4e61bebafb44988383f582b')]
result=[]
for run,git in pairs:
 manifest=json.loads(subprocess.check_output(['git','show',git+':'+B+run+'.archive-manifest.json']));buf=subprocess.check_output(['git','show',git+':'+B+run+'.tar.gz']);assert hashlib.sha256(buf).hexdigest()==manifest['archive_sha256'];t=tarfile.open(fileobj=io.BytesIO(buf),mode='r:gz');members={v.name:v for v in t.getmembers() if v.isfile()};out={'run':run,'git':git,'archive_sha256':manifest['archive_sha256'],'compressed_bytes':len(buf),'member_count':len(members),'schema':{},'selected_hashes':{},'top_json':{},'tail_paths':[k for k in members if any(v in k for v in ['clock-start','clock-end','model-drop','controlled-stop','ready-state'])]}
 for suffix in ['config.json','summary.json','games-partial.json','game-start.jsonl','moves.jsonl','public.jsonl','turns.jsonl','backend-stop.json','pause-monitor-stop.json','ready.json']:
  name=run+'/'+suffix
  if name not in members:continue
  raw=t.extractfile(name).read();sha=hashlib.sha256(raw).hexdigest();assert sha==manifest['restored_hashes'][name];out['selected_hashes'][name]={'sha256':sha,'bytes':len(raw)};v=json.loads(raw.splitlines()[0]) if suffix.endswith('jsonl') else json.loads(raw);out['schema'][suffix]={'type':type(v).__name__,'keys':list(v) if isinstance(v,dict) else None}
  if suffix in ['config.json','summary.json','games-partial.json','ready.json']:out['top_json'][suffix]=v
  if suffix in ['moves.jsonl','public.jsonl','turns.jsonl','game-start.jsonl']:
   sample={k:(list(x)[:40] if isinstance(x,dict) else {'list':len(x),'first':x[0] if len(x)<12 and x else None} if isinstance(x,list) else x) for k,x in v.items()};out['schema'][suffix]['first_summary']=sample
 result.append(out)
(O/'schema-inventory.json').write_text(json.dumps({'UTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'runs':result},indent=2)+'\n')
for r in result:
 print(json.dumps({k:r[k] for k in ['run','git','compressed_bytes','member_count','schema','top_json','tail_paths']}))
