"""NN0 generation-owner export via the stopped/hash-bound195 shared interface."""
from pathlib import Path
import datetime,gzip,hashlib,json,os,subprocess,sys,time
ROOT=Path(__file__).resolve().parents[2];D=ROOT/'research-data/ai-sigma/frame14-teachers';T=Path(__file__).resolve().parent
receipt=json.loads((D/'interface-binding.json').read_text());start=time.monotonic()
for f,h in receipt['source'].items():
    assert hashlib.sha256((ROOT/f).read_bytes()).hexdigest()==h,'SHARED_INTERFACE_BINDING_CHANGED'
assert receipt['writer_stopped'] is True,'INTERFACE_WRITER_NOT_STOPPED'
os.sched_setaffinity(0,{2})
out=D/sys.argv[1];assert not out.exists(),'EXPORT_ATTEMPT_EXISTS';out.mkdir()
summary=json.loads((D/'generation-summary.json').read_text())
assert all(x['attempt'] is not None for x in summary['jobs']),'ALL_JOB_STATUS_NOT_RESOLVED'
assert not any(x['status'] in ['NOT_STARTED','REGISTERED_UNFINISHED_UNKNOWN'] and x['split']=='train' for x in json.loads((D/'all144-status.json').read_text())),'MAX_TRAIN96_EXPOSURE_REFERENCE_INCOMPLETE'
commands=[];inputs=[]
def run(cmd):
    t=time.monotonic();p=subprocess.run(cmd,cwd=ROOT,capture_output=True,text=True,timeout=45)
    commands.append({'cmd':cmd,'wall_s':time.monotonic()-t,'exit':p.returncode,'stdout':p.stdout,'stderr':p.stderr})
    (out/'commands.json').write_text(json.dumps(commands,indent=2)+'\n')
    assert p.returncode==0,'EXPORT_INTERFACE_FAILED'
def rows(p):return [json.loads(x)for x in gzip.decompress(p.read_bytes()).splitlines()if x.strip()]
def write(p,r):p.write_bytes(gzip.compress(('\n'.join(json.dumps(x,separators=(',',':'))for x in r)+'\n').encode()))
sealed=D/'test-sealed';meta=[];training_labels=[];outputs={}
for split in ['train','validation','test']:
    teacher=Path(summary['outputs'][split]['teacher']['path'])
    metadata=out/(split+'-metadata.jsonl.gz');canonical=out/(split+'-canonical.jsonl.gz')
    labels=(sealed if split=='test' else out)/(sys.argv[1]+'-'+split+'-labels.jsonl.gz')
    run(['/home/vscode/.local/bin/node',str(ROOT/'tools/nnue-training/export_generated.cjs'),str(D/'openings.json'),str(teacher),str(metadata),str(labels)])
    run(['python3','-B',str(ROOT/'tools/nnue-training/frame14.py'),'canonicalize','--metadata',str(metadata),'--output',str(canonical)])
    canonical_rows=rows(canonical)
    for r in canonical_rows:
        r['featureSHA']=r['QF1_input_sha256'];r['family']=r['group']
    meta.extend(canonical_rows)
    if split!='test':training_labels.extend(rows(labels))
    outputs[split]={'metadata':str(canonical),'metadata_sha256':hashlib.sha256(canonical.read_bytes()).hexdigest(),'labels':str(labels),'labels_sha256':hashlib.sha256(labels.read_bytes()).hexdigest()}
combined=out/'all144-metadata.jsonl.gz';write(combined,meta)
trainlabels=out/'training-labels.jsonl.gz';write(trainlabels,training_labels)
mask=out/'fixed-exposure-mask.json'
run(['python3','-B',str(ROOT/'tools/nnue-training/frame14.py'),'mask','--metadata',str(combined),'--output',str(mask),'--openings',str(D/'openings.json')])
allstatus=json.loads((D/'all144-status.json').read_text());maskdata=json.loads(mask.read_text())
# Explicitly account for all planned games, including no eligible rows or no produced rows.
planned=json.loads((D/'openings.json').read_text())['games'];allgroups=[]
for g in planned:
    m=maskdata['games'].get(g['family'],{'rows':0,'eligible':0})
    allgroups.append({'game_id':g['game_id'],'group':g['family'],'split':g['split'],'train_slot':g['partition_slot']if g['split']=='train' else None,'status':next(x['status']for x in allstatus if x['game_id']==g['game_id']),'all_rows':m['rows'],'eligible_rows':m['eligible'],'eligible_zero':m['eligible']==0})
manifest={'issue':'quoridor-4lc.194','UTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'metadata':str(combined),'metadata_sha256':hashlib.sha256(combined.read_bytes()).hexdigest(),'mask':str(mask),'mask_sha256':hashlib.sha256(mask.read_bytes()).hexdigest(),'training_labels':str(trainlabels),'training_labels_sha256':hashlib.sha256(trainlabels.read_bytes()).hexdigest(),'test_labels':outputs['test']['labels'],'test_labels_sha256':outputs['test']['labels_sha256'],'outputs':outputs,'all144_games':allgroups,'mask_reference':'maximumtrain96 for validation; train96+allvalidation for test; fixed shared state OR history OR actual QF1 input before selection','shared_interface':receipt,'test_label_contents_opened_for_analysis':False,'new_model_forward':0,'NN':0,'wall_s':time.monotonic()-start}
(out/'dataset-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
print(json.dumps({'rows':len(meta),'train_validation_labels':len(training_labels),'all144_games':144,'maskSHA':manifest['mask_sha256'],'test_labels_unread':True,'wall_s':manifest['wall_s']}))
