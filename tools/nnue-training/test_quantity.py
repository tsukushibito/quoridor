"""NN0 tests for the added fixed-last quantity contrast, no old suite repeat."""
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest

from common import resolve_config
from frame14_data import sha
from test_contrast import interval, quantity_freeze


class QuantityTests(unittest.TestCase):
    def test_pairing(self):
        i=interval({'g1':.2,'g2':.4},{'g2':.2,'g1':.1})
        self.assertAlmostEqual(i['delta'],.15)
        self.assertEqual(i['groups'],2)
        self.assertIsNone(interval({'g1':1},{'g1':0})['percentile95'])

    def test_complete_last_and_fixed_initial_bindings(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);cfg=resolve_config();cfg['training']['steps']=2000
            frozen={'kind':'QF1-one-candidate-test-freeze','initial_state_sha256':'sameinitial',
                    'stage_manifest':{'mask_sha256':'fixedmask'},'validation_sha256':'fixedval','source_sha256':{}}
            cf=root/'candidate.json';cf.write_text(json.dumps(frozen))
            dirs=[]
            for n in [24,96]:
                d=root/str(n);d.mkdir();dirs.append(str(d));w=d/'weights';w.mkdir();(w/'last.pt').write_bytes(b'NN0 mock only')
                (d/'config.json').write_text(json.dumps(cfg))
                (d/'dataset.json').write_text(json.dumps({'initial_state_sha256':'sameinitial','validation_sha256':'fixedval',
                    'stage_manifest':{'train_games':n,'mask_sha256':'fixedmask'}}))
                (d/'summary.json').write_text(json.dumps({'status':'max_steps','step':2000,'checkpoint_dir':str(w),
                                                        'last_evaluation':{'train_samples_seen':256000}}))
            args=SimpleNamespace(candidate_freeze=str(cf),stage24=dirs[0],stage96=dirs[1],output=str(root/'freeze.json'))
            quantity_freeze(args)
            f=json.loads(Path(args.output).read_text());self.assertTrue(f['quantity_declared_before_test'])
            self.assertEqual(f['quantity']['stage96_last']['checkpoint_sha256'],sha(Path(dirs[1])/'weights/last.pt'))
            p=Path(dirs[1])/'summary.json';j=json.loads(p.read_text());j['step']=1900;p.write_text(json.dumps(j))
            args.output=str(root/'rejected.json')
            with self.assertRaises(ValueError):quantity_freeze(args)
            self.assertFalse(Path(args.output).exists())


if __name__=='__main__':unittest.main()
