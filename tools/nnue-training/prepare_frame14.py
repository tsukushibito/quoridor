"""NN0 SHA-bound stage preparation; never opens sealed test labels."""
import argparse
import json
from pathlib import Path
from types import SimpleNamespace

from common import load_data, write_json
from frame14 import stage
from frame14_data import bound_path, sha


def main(a):
    m=json.loads(Path(a.manifest).read_text())
    if len(m['all144_games'])!=144:raise ValueError('planned144 missing')
    for k in ['metadata','mask','training_labels']:bound_path(m,k)
    out=Path(a.output);out.mkdir(exist_ok=True)
    summaries=[]
    for n in [24,48,96]:
        p=out/('train'+str(n)+'.stage.json')
        stage(SimpleNamespace(metadata=m['metadata'],mask=m['mask'],training_labels=m['training_labels'],games=n,output=str(p)))
        rows,info=load_data(p,'report')
        train=[r for r in rows if r['split']=='train' and r.get('rootmean') is not None]
        val=[r for r in rows if r['split']=='validation'];primary=[r for r in val if r['primary_eligible']]
        g={}
        for r in train:g.setdefault(r['group'],[]).append(r['rootmean'])
        summaries.append({'stage':n,'manifest':str(p.resolve()),'manifest_sha256':sha(p),
                          'train_rows':len(train),'actual_train_groups':len(g),'validation_all':len(val),'validation_primary':len(primary),
                          'validation_sha256':info['validation_sha256'],'constant_gameequal':sum(sum(v)/len(v) for v in g.values())/len(g),
                          'predicted_training_samples':256000,'sample_upper':256000+21*len(rows),
                          'epochs_equivalent':256000/len(train)})
    if len({s['validation_sha256'] for s in summaries})!=1:raise ValueError('validation differs between stages')
    result={'dataset_descriptor':str(Path(a.manifest).resolve()),'dataset_descriptor_sha256':sha(a.manifest),
            'metadata_sha256':m['metadata_sha256'],'mask_sha256':m['mask_sha256'],'training_labels_sha256':m['training_labels_sha256'],
            'test_labels_path_ONLY':m['test_labels'],'test_labels_SHA_ONLY':m['test_labels_sha256'],'test_labels_opened':False,'stages':summaries}
    write_json(out/'preparation.json',result)
    print(json.dumps(result))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--manifest',required=True);p.add_argument('--output',required=True);main(p.parse_args())
