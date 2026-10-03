"""Five saved reference roots only. No NN, training, or rule replay."""
import argparse, copy, hashlib, json, math, re, struct, time, resource
from pathlib import Path

D=Path('research-data/ai-sigma/160-pv-pipeline-bootstrap')
RAW=Path('.artifacts/ai-sigma/resume-20261003/SIGMA-WEB-PORT/runs/port151-stageA-r2/browser-result.json')
FIX=Path('research-data/ai-sigma/151-sigma-web-port/stageA-inputs.json')
IDS=['initial-p1','asym-hv-p2','straight-jump-p2','frame10-prefix-13','frame10-prefix-14']
TOKENS=re.compile(r'[{}\[\]"]'); DEC=json.JSONDecoder()
def digest(b): return hashlib.sha256(b).hexdigest()
def canonical(x): return json.dumps(x,sort_keys=True,separators=(',',':')).encode()
def skip(s,i):
    while s[i].isspace(): i+=1
    if s[i]=='"': return DEC.raw_decode(s,i)[1]
    if s[i] not in '[{':
        j=i
        while j<len(s) and s[j] not in ',}]': j+=1
        return j
    depth,j=1,i+1
    while depth:
        m=TOKENS.search(s,j)
        if not m: raise ValueError('unterminated JSON')
        if m[0]=='"': j=DEC.raw_decode(s,m.start())[1]
        else: depth+=1 if m[0] in '[{' else -1; j=m.end()
    return j
def fields(s,i):
    assert s[i]=='{'; i+=1
    while True:
        while s[i].isspace() or s[i]==',': i+=1
        if s[i]=='}': return
        k,j=DEC.raw_decode(s,i)
        while s[j].isspace() or s[j]==':': j+=1
        e=skip(s,j); yield k,j,e; i=e
def floats(bits): return [struct.unpack('<f',struct.pack('<I',v))[0] for v in bits]
def perm(a):
    if a<8: return [1,0,2,3,6,7,4,5][a]
    base=8 if a<72 else 72; p=a-base
    return base+(7-p//8)*8+p%8
DIR=[(0,1),(0,-1),(-1,0),(1,0),(-1,1),(1,1),(-1,-1),(1,-1)]
def mapping(key,side,legal):
    p=key.split('|'); pawns=[list(map(int,p[i].split(','))) for i in (0,1)]
    assert int(p[2])==side
    own,other=pawns[side],pawns[side^1]; out={}
    for a in legal:
        if a>=145: physical=72+a-145
        elif a>=81: physical=8+a-81
        else:
            dest=[a%9,a//9]; dx=dest[0]-own[0]; dy=dest[1]-own[1]
            direction=((dx>0)-(dx<0),(dy>0)-(dy<0)); physical=DIR.index(direction)
            x,y=own[0]+direction[0],own[1]+direction[1]
            if (not direction[0] or not direction[1]) and [x,y]==other:
                x+=direction[0]; y+=direction[1]
            assert [x,y]==dest, ('actual pawn landing mismatch',a)
        assert 0<=physical<136
        out[a]=perm(physical) if side else physical
    assert len(set(out.values()))==len(out)
    return out
def group(r): return digest(canonical(r['state']))
def validate(rows):
    groups={}; folds={}
    for r in rows:
        assert r['schema']=='pv-diagnostic-v1'
        st=r['state']; side=st['side']; assert side in (0,1)
        assert isinstance(st['ply'],int) and st['ply']>=0
        assert isinstance(st['history'],list) and isinstance(st['prefix'],list)
        assert len(st['prefix'])==st['ply']
        assert len(r['features_bits'])==648 and all(type(v)==int and 0<=v<2**32 for v in r['features_bits'])
        f=floats(r['features_bits']); assert all(math.isfinite(v) for v in f)
        parts=st['key'].split('|'); pawns=[list(map(int,parts[i].split(','))) for i in (0,1)]
        for channel,player in [(0,side),(1,side^1)]:
            x,y=pawns[player]; index=(8-y if side else y)*9+x
            assert f[channel*81:(channel+1)*81]==[float(i==index) for i in range(81)]
        for channel,player in [(4,side),(5,side^1)]:
            assert all(abs(v-st['walls_remaining'][player]/10)<1e-6 for v in f[channel*81:(channel+1)*81])
        assert len(r['pi136'])==136 and all(math.isfinite(v) and v>=0 for v in r['pi136'])
        m=mapping(st['key'],side,r['legal_actions'])
        assert r['mapping136']==[[a,m[a]] for a in sorted(m)]
        t=r['teacher']; assert t['K']==32 and t['rootN']==32
        assert t['edge_sum']==31 and sum(e[1] for e in r['edge_visits'])==31
        expected=[0.0]*136
        assert len({e[0] for e in r['edge_visits']})==len(r['edge_visits'])
        for a,n in r['edge_visits']:
            assert type(n)==int and n>=0 and a in m; expected[m[a]]=n/31
        assert all(abs(a-b)<1e-12 for a,b in zip(expected,r['pi136']))
        assert abs(sum(r['pi136'])-1)<1e-12
        for k in ('root_nn_stm','rootmean_stm','root_nn_p1','rootmean_p1'):
            assert math.isfinite(t[k]) and -1<=t[k]<=1
        sign=1 if side==0 else -1
        assert t['root_nn_p1']==sign*t['root_nn_stm'] and t['rootmean_p1']==sign*t['rootmean_stm']
        assert abs(t['rootmean_stm']-t['root_valueSum']/t['rootN'])<1e-12
        assert t['game_z'] is None and t['leaf_nn'] is None
        assert r['group']==group(r) and r['split'] in ('train','validation')
        g=r['group']; assert g not in folds or folds[g]==r['split'], 'group leakage'
        folds[g]=r['split']; groups[g]=st
    return {'rows':len(rows),'groups':len(groups),'train':sum(r['split']=='train' for r in rows),'validation':sum(r['split']=='validation' for r in rows)}
def export():
    raw=RAW.read_bytes(); s=raw.decode(); fs={f['id']:f for f in json.loads(FIX.read_bytes())['fixtures']}
    start=next(a for k,a,b in fields(s,0) if k=='rows'); j=start+1; rows=[]
    while True:
        while s[j].isspace() or s[j]==',': j+=1
        if s[j]==']': break
        e=skip(s,j); spans={k:(a,b) for k,a,b in fields(s,j)}
        get=lambda k: json.loads(s[slice(*spans[k])]) if k in spans else None
        fid=get('fixture_id')
        if fid in IDS and get('engine')=='reference':
            cp=get('cp'); nstart=spans['numeric'][0]+1
            while s[nstart].isspace(): nstart+=1
            n=json.loads(s[nstart:skip(s,nstart)]); f=fs[fid]
            assert n['path']==[] and f['classification']=='legal-replay'
            bits=n['features_bits']; expected=f.get('features_bits')
            if expected is None: expected=[struct.unpack('<I',struct.pack('<f',v))[0] for v in f['raw_features_float32']]
            assert bits==expected
            assert sorted(n['history'])==sorted(f['history_counts'])
            legal=n['legal']; mp=mapping(n['key'],n['turn'],legal)
            saved_legal=f.get('legal_actions',f.get('legal_ids'))
            saved_ids=[v['rust209'] if isinstance(v,dict) else v for v in saved_legal]
            assert sorted(legal)==sorted(saved_ids)
            if 'P2_permutation136' in f: assert f['P2_permutation136']==[perm(a) for a in range(136)]
            edges=[[a,int(v)] for a,p,v,w in cp['root_edges']]; total=sum(v for a,v in edges)
            assert total>0, 'zero-visits policy not exportable'
            pi=[0.0]*136
            for a,v in edges: pi[mp[a]]=v/total
            N=cp.get('root_visits',cp.get('simulations')); side=n['turn']; sign=1 if side==0 else -1
            fv=floats(bits); remaining=[0,0]; remaining[side]=round(fv[324]*10); remaining[side^1]=round(fv[405]*10)
            state={'key':n['key'],'history':sorted(n['history']),'side':side,'ply':n['ply'],'prefix':f['legal_prefix'],'walls_remaining':remaining}
            r={'schema':'pv-diagnostic-v1','fixture':fid,'engine':'reference','state':state,'features_bits':bits,'legal_actions':legal,'mapping136':[[a,mp[a]] for a in sorted(mp)],'edge_visits':edges,'pi136':pi,
               'teacher':{'K':get('K'),'rootN':N,'edge_sum':total,'root_nn_stm':n['value'],'rootmean_stm':cp['root_mean'],'root_valueSum':cp['root_valueSum'],'root_nn_p1':sign*n['value'],'rootmean_p1':sign*cp['root_mean'],'game_z':None,'game_z_missing':'StageA search only','leaf_nn':None,'leaf_nn_missing':'deep payload not selected','actual_nn':cp.get('nn_calls')},
               'source':{'run':'port151-stageA-r2','raw_sha256':digest(raw),'raw_bytes':len(raw),'row_span_bytes':len(s[j:e].encode()),'row_span_sha256':digest(s[j:e].encode()),'fixture_sha256':digest(FIX.read_bytes()),'clock':'fixed K32, not equal wall/CPU','rule_replay_this_export':False}}
            r['group']=group(r); rows.append(r)
        j=e
    assert sorted(r['fixture'] for r in rows)==sorted(IDS)
    validation=min(r['group'] for r in rows)
    for r in rows: r['split']='validation' if r['group']==validation else 'train'
    summary=validate(rows); assert digest(RAW.read_bytes())==digest(raw)
    (D/'fixtures.jsonl').write_text(''.join(json.dumps(r,separators=(',',':'))+'\n' for r in rows))
    return summary
def mocks(rows):
    cases=[]
    for name,change in [('shape',lambda r:r['features_bits'].pop()),('NaN-value',lambda r:r['teacher'].update(rootmean_stm=float('nan'))),('illegal-mass',lambda r:r['pi136'].__setitem__(0,2.0)),('bad-visits',lambda r:r['edge_visits'][0].__setitem__(1,-1)),('wrong-P2-map',lambda r:r['mapping136'][0].__setitem__(1,135)),('wrong-sign',lambda r:r['teacher'].update(root_nn_p1=2.0))]:
        bad=copy.deepcopy(rows); change(bad[0])
        try: validate(bad)
        except (AssertionError,ValueError,KeyError): cases.append(name)
        else: raise AssertionError('accepted '+name)
    bad=copy.deepcopy(rows); twin=copy.deepcopy(bad[0]); twin['engine']='candidate'; twin['split']='train' if twin['split']=='validation' else 'validation'; bad.append(twin)
    try: validate(bad)
    except AssertionError: cases.append('candidate-reference-group-leak')
    else: raise AssertionError('accepted group leakage')
    # Pure mapping fixtures: P2 straight jump and both wall orientations.
    key='4,4|4,5|1||'; m=mapping(key,1,[31,81,145])
    assert m[31]==0 and m[81]==64 and m[145]==128
    assert all(perm(perm(a))==a for a in range(136))
    return cases
def main():
    parser=argparse.ArgumentParser(); parser.add_argument('command',choices=['export','validate','smoke']); args=parser.parse_args()
    started=time.time()
    if args.command=='export': out=export()
    else:
        rows=[json.loads(line) for line in (D/'fixtures.jsonl').read_text().splitlines()]
        out=validate(rows)
        if args.command=='smoke': out['rejected_mocks']=mocks(rows)
    out.update(command=args.command,start_UTC=started,end_UTC=time.time(),peak_RSS_KiB=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,new_NN=0,new_training=0)
    print(json.dumps(out))
if __name__=='__main__': main()
