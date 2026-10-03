"""NN0 boundary tests only; no torch/model/session import or data reads."""
import copy
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from common import load_data, measurements, resolve_config
from frame14_data import bound_path, canonical_model_input, feature_signature, make_mask, sha
from frame14 import evaluate, freeze


def row(name,split,group,side=1,views=None,distance=None):
    return {'id':name,'split':split,'group':group,'game_id':group,'side':side,
            'ids':views or [[1,82,290,301],[2,83,291,302]],
            'distance':distance or [.1,.2],'state_key':name,'history_key':'history-'+name}


class Frame14BoundaryTests(unittest.TestCase):
    def test_actual_stm_and_float32_input(self):
        a=row('a','train','g')
        b=row('b','test','h',side=2,views=list(reversed(a['ids'])),distance=[.1000000001,.2000000001])
        self.assertEqual(canonical_model_input(a),canonical_model_input(b))
        self.assertEqual(feature_signature(a),feature_signature(b))
        b['distance']=list(reversed(a['distance']))
        self.assertNotEqual(feature_signature(a),feature_signature(b))

    def test_or_mask_and_label_prohibition(self):
        t=row('t','train','t');v=row('v','validation','v',distance=[.3,.4]);e=row('e','test','e',distance=[.5,.6])
        v['state_key']=t['state_key']
        e['history_key']=v['history_key']
        m=make_mask([t,v,e])
        self.assertFalse(m['rows']['v']['primary_eligible'])
        self.assertFalse(m['rows']['e']['primary_eligible'])
        self.assertEqual(m['games']['e']['rows'],1)
        self.assertIn('e',m['zero_eligible_games'])
        e['rootmean']=0
        with self.assertRaises(ValueError):make_mask([t,v,e])

    def test_family_and_test_training_rejection(self):
        with self.assertRaises(ValueError):make_mask([row('t','train','shared'),row('v','validation','shared')])
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'leak.json';p.write_text(json.dumps([row('t','train','t'),row('x','test','x')]))
            with self.assertRaises(ValueError):load_data(p,'report')

    def test_train_constant_is_fixed_not_refit(self):
        rows=[{**row('a','validation','a'),'rootmean':1.,'z':1.}]
        self.assertEqual(measurements(rows,[0.],'rootmean',.25)['constant_mse'],.5625)

    def test_fixed_max96_not_stage_specific(self):
        a=row('a','train','first24',distance=[.3,.4]);b=row('b','train','later96');v=row('v','validation','v')
        self.assertFalse(make_mask([a,b,v])['rows']['v']['primary_eligible'])
        self.assertTrue(make_mask([a,v])['rows']['v']['primary_eligible'])

    def test_freeze_before_labels_and_artifact_binding(self):
        with tempfile.TemporaryDirectory() as tmp:
            d=Path(tmp);run=d/'run';run.mkdir();w=d/'weights';w.mkdir()
            for n in ['best.pt','initial.pt']:(w/n).write_bytes(b'fake-no-model')
            spec={'kind':'QF1-training-stage'}
            for k in ['metadata','mask','training_labels']:
                p=d/k;p.write_text('{}');spec[k]=str(p);spec[k+'_sha256']=sha(p)
            cfg=resolve_config();cfg['training']['sampling']='game'
            (run/'config.json').write_text(json.dumps(cfg))
            (run/'dataset.json').write_text(json.dumps({'stage_manifest':spec,'sha256':'dataset','validation_sha256':'val','constant':.25,'initial_state_sha256':'initial'}))
            (run/'summary.json').write_text(json.dumps({'status':'max_steps','step':cfg['training']['steps'],'checkpoint_dir':str(w),'best_step':100,'best_validation_mse':.1}))
            out=d/'freeze.json';sealed=d/'NOT_CREATED_sealed_test'
            freeze(SimpleNamespace(run=str(run),output=str(out),test_labels=str(sealed),test_sha='a'*64,reason='fake boundary test'))
            self.assertFalse(sealed.exists());self.assertFalse(json.loads(out.read_text())['test_labels_opened'])
            with self.assertRaises(ValueError):evaluate(SimpleNamespace(freeze=str(out),freeze_sha='wrong',output=str(d/'eval')))
            (w/'best.pt').write_bytes(b'changed')
            with self.assertRaises(ValueError):bound_path(json.loads(out.read_text()),'checkpoint')


if __name__=='__main__':unittest.main()
