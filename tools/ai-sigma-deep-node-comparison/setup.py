"""Extract four preselected midgame prefixes and retain minimal private build inputs."""
from pathlib import Path
import json,hashlib,tarfile
ROOT=Path(__file__).resolve().parents[2];TOOL=Path(__file__).parent
DATA=ROOT/'research-data/ai-sigma/132-deep-node-comparison'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
inputs=[];refs=[]
for pair,color in [(1,1),(2,2)]:
    archive=ROOT/f'research-data/ai-sigma/119-diverse-prefix/prefix119-pair{pair}-r1.tar.gz'
    with tarfile.open(archive) as t:
        member=next(x for x in t.getnames() if x.endswith('browser-result.json'))
        raw=t.extractfile(member).read();document=json.loads(raw)
        game=next(x for x in document['games'] if x['id']==f'pair{pair}-color{color}')
        rows={x['identity']['request_id']:x for x in document['rows']}
        for newply in [8,16]:
            assert len(game['actions'])>=newply
            selected=[rows[i] for i in game['turn_indices'][:newply]]
            assert all(x['response']['classification']=='completed_legal' for x in selected)
            assert [x['response']['body']['action'] for x in selected]==game['actions'][:newply]
            inputs.append({'id':f'diverse-prefix-mid-pair{pair}-color{color}-new{newply}','legal_prefix':game['initial_prefix']+game['actions'][:newply],'new_public_plies':newply,'source_game':game['id'],'original_prefix_plies':len(game['initial_prefix']),'source_member':member,'source_member_SHA256':hashlib.sha256(raw).hexdigest()})
    refs.append({'path':str(archive.relative_to(ROOT)),'SHA256':sha(archive),'member':member,'member_SHA256':hashlib.sha256(raw).hexdigest()})
(DATA/'raw-input-prefixes.json').write_text(json.dumps({'inputs':inputs,'archive_refs':refs},indent=2)+'\n')
for variant in ['baseline','trace']:
    directory=TOOL/variant;(directory/'src').mkdir(parents=True,exist_ok=True)
    for name in ['lib.rs','kernel.rs','research.rs']:
        (directory/'src'/name).write_bytes((ROOT/'tools/ai-sigma-ort-search/src'/name).read_bytes())
    manifest=(ROOT/'tools/ai-sigma-ort-search/Cargo.toml').read_text().replace('../../crates/','../../../crates/')
    (directory/'Cargo.toml').write_text(manifest)
    (directory/'Cargo.lock').write_bytes((ROOT/'tools/ai-sigma-ort-search/Cargo.lock').read_bytes())
s=(ROOT/'tools/ai-sigma-tactical-evaluation/runner.py').read_text().replace('TACTICAL-EVALUATION','DEEP-NODE-COMPARISON').replace('tactical129-','deep132-').replace('quoridor-4lc.129','quoridor-4lc.132').replace('129-tactical-evaluation','132-deep-node-comparison').replace('FRAME129','FRAME132').replace("['tactical','protocol']","['count','build','protocol']")
s=s.replace('RSS_GUARD=939524096 if CPU==0 else 5905580032',"RSS_GUARD=3758096384 if PHASE=='build' else 939524096 if CPU==0 else 5905580032").replace('STORAGE_GUARD=58720256','STORAGE_GUARD=469762048').replace('CONTRACT_RAM=1073741824 if CPU==0 else 6442450944',"CONTRACT_RAM=4294967296 if PHASE=='build' else 1073741824 if CPU==0 else 6442450944").replace('MAX_WALL=60 if CPU==0 else 180',"MAX_WALL=300 if PHASE=='build' else 60 if CPU==0 else 180").replace('TOTAL_WALL=300 if CPU==0 else 600',"TOTAL_WALL=600 if PHASE=='build' else 300 if CPU==0 else 600")
(TOOL/'runner.py').write_text(s)
s=(ROOT/'tools/ai-sigma-tactical-evaluation/admission.py').read_text().replace('tactical129-','deep132-').replace('129-tactical-evaluation','132-deep-node-comparison').replace('DEPENDENCY127','DEPENDENCY129').replace('58720256','469762048')
(TOOL/'admission.py').write_text(s)
(TOOL/'commit-own.sh').write_text((ROOT/'tools/ai-sigma-tactical-evaluation/commit-own.sh').read_text().replace('TACTICAL-EVALUATION','DEEP-NODE-COMPARISON'))
print('four inputs/private source ready')
