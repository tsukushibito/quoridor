"""Generation-owner NN0 export; shared canonical API and prior label-free exposure."""
from pathlib import Path
import datetime,gzip,hashlib,importlib.util,json,os,subprocess,sys,time
ROOT=Path(__file__).resolve().parents[2];D=ROOT/'research-data/ai-sigma/frame14-head-test'
interface=json.loads((D/'interface-binding.json').read_text())
for f,h in interface['source'].items():assert hashlib.sha256((ROOT/f).read_bytes()).hexdigest()==h,'INTERFACE_CHANGED'
assert interface['writer_stopped'] is True
os.sched_setaffinity(0,{2});start=time.monotonic()
output=D/'canonical-export-r1';assert not output.exists();output.mkdir();sealed=D/'test-sealed';sealed.mkdir(exist_ok=True)
summary=json.loads((D/'generation-summary.json').read_text());teacher=summary['outputs']['test']['teacher']['path']
meta=output/'test-metadata.jsonl.gz';canonical=output/'test-canonical.jsonl.gz';labels=sealed/'test-labels.jsonl.gz'
commands=[['/home/vscode/.local/bin/node','--max-old-space-size=512',str(ROOT/'tools/nnue-training/export_generated.cjs'),str(D/'openings.json'),teacher,str(meta),str(labels)],['python3','-B',str(ROOT/'tools/nnue-training/frame14.py'),'canonicalize','--metadata',str(meta),'--output',str(canonical)]]
for command in commands:subprocess.run(command,check=True,timeout=60,cwd=ROOT)
spec=importlib.util.spec_from_file_location('canonical_stopped',ROOT/'tools/nnue-training/frame14_data.py');api=importlib.util.module_from_spec(spec);spec.loader.exec_module(api)
new=api.read_rows(canonical);reference_binding=json.loads((D/'reference-binding.json').read_text());prior=[]
for item in reference_binding['references']:
 reference_path=Path(item['path']);assert api.sha(reference_path)==item['SHA'],'REFERENCE_CHANGED';prior.extend(api.read_rows(reference_path))
# Only reference split alias: old test joins val for NEW mask; original metadata/masks unchanged.
reference=[{**r,'split':'validation' if r['split']=='test' else r['split']}for r in prior]
allmask=api.make_mask(reference+new);ids={r['id']for r in new};families={g['family']for g in json.loads((D/'openings.json').read_text())['games']}
mask={**allmask,'rows':{k:v for k,v in allmask['rows'].items()if k in ids},'games':{g:allmask['games'].get(g,{'split':'test','rows':0,'eligible':0})for g in families},'reference_metadata_paths':reference_binding['references'],'reference_metadata_SHA':api.sha(D/'reference-binding.json'),'reference_rule':'old194 all144 + old201 fresh24 label-free state OR history OR sameQF1 input; oldtest split alias only for shared make_mask reference','labels_used':False,'new_metadata_SHA':api.sha(canonical),'metadata_sha256':api.sha(canonical)}
mask['zero_eligible_games']=sorted(g for g,v in mask['games'].items()if not v['eligible']);maskpath=output/'fixed-newtest-mask.json';maskpath.write_text(json.dumps(mask,indent=2)+'\n')
manifest={'issue':'quoridor-4lc.205','UTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'metadata':str(canonical),'metadata_sha256':api.sha(canonical),'mask':str(maskpath),'mask_sha256':api.sha(maskpath),'test_labels':str(labels),'test_labels_sha256':api.sha(labels),'all24_families':sorted(families),'all24_slots':json.loads((D/'all24-slot-status.json').read_text()),'shared_interface':interface,'test_label_analysis':False,'NN':0,'wall_s':time.monotonic()-start};(output/'dataset-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n');print(json.dumps({'metadata_rows':len(new),'planned24':len(families),'labels_analysis':False,'mask_SHA':api.sha(maskpath)}))
