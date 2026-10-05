import pathlib,json,subprocess,tarfile,io,hashlib,datetime
R=pathlib.Path(__file__).resolve().parents[2];O=R/'.artifacts/ai-sigma/resume-20261002/COOPERATIVE-ARENA-INDEPENDENT';G='c1b78f2d538f951a6115a0a8d0c7f30658ad27e0';B='research-data/ai-sigma/103-cooperative-arena/';H=lambda b:hashlib.sha256(b).hexdigest();expected={'handoff-summary.json':'b022be87a3323c21bdca111e037850ab56a6d9010bd715fd105d4e46179b84bf','runtime-source-stopped-final.json':'9453df367fe983f365aaf7edc099207c2aaef06613e4c0a5da8f9db30a025baf','writer-runtime-stopped-final.json':'6e2451841907f15de0ce38a557dd0dd7be11bad2da38bc2a6126c18fe66636be','run-controls-manifest.json':'8cf88842b0a20368b722510aec29e6b640c4309c6fe29ddfb963c2ddc65a360c'};fixed={}
for n,w in expected.items():
 b=subprocess.check_output(['git','show',G+':'+B+n]);assert H(b)==w;fixed[n]={'hash':H(b),'bytes':len(b)}
s=json.loads(subprocess.check_output(['git','show',G+':'+B+'runtime-source-stopped-final.json']));m=json.loads(subprocess.check_output(['git','show',G+':'+B+'run-controls-manifest.json']));a=subprocess.check_output(['git','show',G+':'+m['archive']]);assert H(a)==m['SHA256'];t=tarfile.open(fileobj=io.BytesIO(a),mode='r:gz');jobs=[];ids=set();sourceHashes={};
for run in ['initial-pair-r1','asym-pair-r1','jump-pair-r1']:
 n='nn-'+run+'.process.json';b=t.extractfile(n).read();assert H(b)==m['restored_hashes'][n];x=json.loads(b);print(n,list(x));
 for v in x.get('tracked',[]):ids.add((int(v['pid']),int(v.get('start_ticks',v.get('starttick',0)))))
 # child/runner identities retained explicitly even if not in tracked.
 for p,st in [('runner_pid','runner_starttick'),('child_pid','child_starttick')]:
  if x.get(p) and x.get(st):ids.add((int(x[p]),int(x[st])))
 jobs.append({'run':run,'hash':H(b),'start':x.get('start'),'end':x.get('end'),'exit':x.get('exit'),'remaining':x.get('remaining'),'unknown_adopted':x.get('unknown_adopted'),'peakRSS':x.get('peak_group_plus_runner_RSS'),'peakStorage':x.get('peak_allocated_bytes'),'assignedCPU':x.get('assigned_CPU'),'kernel_boundary':x.get('kernel_boundary'),'adopted_waits':x.get('adopted_waits')})
for item in s['recorded_identities']:ids.add((int(item['pid']),int(item['starttick'])))
boot=pathlib.Path('/proc/sys/kernel/random/boot_id').read_text().strip();live=[]
for pid,st in sorted(ids):
 try:v=pathlib.Path(f'/proc/{pid}/stat').read_text().rsplit(')',1)[1].split();actual=int(v[19]);
 except (OSError,ValueError):continue
 if actual==st:live.append({'pid':pid,'starttick':st,'state':v[0]})
assert boot==s['boot_id'];assert not live
# Bind semantic source inspection to each measured Git, not today's mutable file.
for g in ['7eff5ad9900bf66d71cf37a20223ee5753f7692e','9dd49a00c77133a199401fd84efdac6c60abcba7','137b6bddd86eddfab4e61bebafb44988383f582b']:
 d={}
 for f in ['tools/ai-sigma-cooperative-arena/arena.cjs','tools/ai-sigma-tail-transport/early-worker.js','tools/ai-sigma-tail-transport/checkpoint.js','tools/ai-sigma-tail-transport/real-backend.cjs','tools/ai-sigma-actual-boundary-repair/final-envelope.cjs','tools/ai-sigma-actual-boundary-repair/early-cache.cjs','tools/ai-sigma-actual-boundary-repair/game-loop.cjs']:
  b=subprocess.check_output(['git','show',g+':'+f]);d[f]=H(b)
 sourceHashes[g]=d
out={'UTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'dataGit':G,'fixed_blob_hashes':fixed,'controls_archiveSHA':H(a),'processes':jobs,'owner_final_ledger_identity_count':len(s['recorded_identities']),'independent_union_with_3processes':len(ids),'same_identity_current_live':live,'boot':boot,'current_absence_not_historical_wait_proof':True,'sourceGitHashes':sourceHashes,'source_policy_note':'validation_finished/validated_cache_ms is sampled before cache assignment; caller marker after cutoff does not measure actual assignment. Internal API starts are later than wrapper budget checks.'};(O/'independent-stop-source-proof.json').write_text(json.dumps(out,indent=2));print('fixed4 hashes and current identity union',len(ids),'live',len(live))
