"""Private CPU QF1 distance standardization, preserving the raw initial function."""
import hashlib
import json
from pathlib import Path
import torch
import model as shared_model

RawModel = shared_model.Model
SCALE_PATH = Path('research-data/ai-sigma/frame15-input-scale-control/scale.json')
SCALE = json.loads(SCALE_PATH.read_text())

class ScaleModel(RawModel):
    instances = []
    def __init__(self, config):
        super().__init__(config)
        self.mu = torch.tensor(SCALE['mu_f32'], dtype=torch.float32)
        self.sigma = torch.tensor(SCALE['sigma_f32'], dtype=torch.float32)
        assert torch.isfinite(self.sigma).all() and (self.sigma > 0).all()
        self.raw_tensor_SHA = hashlib.sha256(b''.join(v.detach().numpy().tobytes() for v in self.state_dict().values())).hexdigest()
        with torch.random.fork_rng(devices=[]):
            raw = RawModel(config)
        raw.load_state_dict(self.state_dict()); raw.eval()
        object.__setattr__(self, 'raw_reference', raw)
        with torch.no_grad():
            w = self.h.weight[:, -2:].clone()
            self.h.bias.copy_(self.h.bias + w @ self.mu)
            self.h.weight[:, -2:].copy_(w * self.sigma)
        self.train_step = 0
        self.parity_samples = 0
        self.parity_maxabs = 0.0
        self.batch_hasher = hashlib.sha256()
        self.observations = []
        self.__class__.instances.append(self)

    def bind_rows(self, rows, all_inputs):
        assert not any(r['split'] == 'test' for r in rows)
        self.rows = rows
        self.witness_indices = sorted((i for i,r in enumerate(rows) if r['split']=='train'),
            key=lambda i: hashlib.sha256(('228-witness-v1:'+rows[i]['id']).encode()).digest())[:12]
        self.active_FT_ids = int(all_inputs[0].sum((0,1)).gt(0).sum())

    def forward(self, x, d, side):
        y = super().forward(x, (d-self.mu)/self.sigma, side)
        if not self.training and self.train_step == 0:
            with torch.inference_mode():
                original = self.raw_reference(x,d,side)
            self.parity_samples += len(x)
            self.parity_maxabs = max(self.parity_maxabs, (y-original).abs().max().item())
        return y

def observed_step(opt, mdl, step, indices, targets, predicted):
    assert mdl.parity_samples == len(mdl.rows) and mdl.parity_maxabs <= 1e-6, 'INITIAL_FUNCTION_PARITY'
    mdl.batch_hasher.update(json.dumps([mdl.rows[i]['id'] for i in indices],separators=(',',':')).encode()+b'\n')
    opt.step(); mdl.train_step=step

def observed_record(mdl, rows, values, rec, out):
    import gzip
    if rec['step']==0:
        p={'PASS':mdl.parity_samples==len(rows) and mdl.parity_maxabs<=1e-6,
           'maxabs':mdl.parity_maxabs,'atol':1e-6,'raw_additional_samples':mdl.parity_samples,
           'raw_tensor_SHA':mdl.raw_tensor_SHA,'test_joined':False,'scale_SHA':hashlib.sha256(SCALE_PATH.read_bytes()).hexdigest()}
        (out/'initial-function-parity.json').write_text(json.dumps(p,indent=2)+'\n')
        assert p['PASS']
    # These values come from the charged evaluation pass; observer adds no forward.
    with gzip.open(out/f'predictions-step{rec["step"]}.jsonl.gz','wt') as f:
        for row,value in zip(rows,values):
            f.write(json.dumps({'id':row['id'],'group':row['group'],'split':row['split'],
                'primary_eligible':row.get('primary_eligible',True),'prediction':value})+'\n')
    rec['witness']=[{'id':rows[i]['id'],'prediction':values[i]}for i in mdl.witness_indices]
    rec['active_FT_ids']=mdl.active_FT_ids
    rec['raw_parity_additional_samples']=mdl.parity_samples
    with (out/'history.jsonl').open('a') as f: f.write(json.dumps(rec,allow_nan=False)+'\n')
