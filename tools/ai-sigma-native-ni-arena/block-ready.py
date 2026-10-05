import sys,json,time,datetime
from pathlib import Path
from admission import control,physical,storage
c=json.loads(Path(sys.argv[1]).read_text());out=Path(c['job_out']);base=out.parent.parent
assert time.time()+305<datetime.datetime.fromisoformat(c['newjob_deadline']).timestamp(),'BLOCK_DEADLINE_HEADROOM'
rows=control(base);current=physical(base,within=True);space=storage(base,Path(__file__).resolve().parent)
x={'UTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'decision':'launch_allowed','control':rows,'physical_current':current,'storage':space}
with(out/'block-admissions.jsonl').open('a')as f:f.write(json.dumps(x)+'\n')
print(json.dumps({'decision':'launch_allowed'}))
