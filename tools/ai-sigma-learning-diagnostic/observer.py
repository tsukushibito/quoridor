"""Observe already charged train/eval forwards; no RNG or extra pass."""
import hashlib
import json
import math
from pathlib import Path
import torch
from model import Model

POINTS = [0,1,2,5,10,20,50,100,200,400]

def stats(t):
    t = t.detach().float()
    return {'mean':t.mean().item(),'std_population':t.std(unbiased=False).item(),
            'min':t.min().item(),'max':t.max().item(),'rms':t.square().mean().sqrt().item(),
            'zero_fraction':(t==0).float().mean().item()}

def relu_stats(t):
    a = torch.relu(t.detach())
    return {'preactivation':stats(t),'postactivation':stats(a),
            'dead_in_observed_batch_fraction':(a.reshape(-1,a.shape[-1]).amax(dim=0)==0).float().mean().item()}

class DiagnosticModel(Model):
    instances = []
    def __init__(self, config):
        super().__init__(config)
        self.train_step = 0
        self.eval_offset = 0
        self.selected_local = []
        self.pending, self.witness_layers = {}, {}
        self.batch_hasher = hashlib.sha256()
        self.observations = []
        self.initial_values = None
        self.__class__.instances.append(self)
        for name in ['ft','h','out']:
            getattr(self,name).register_forward_hook(self.layer_hook(name))

    def bind_rows(self, rows, all_inputs):
        eligible = [(hashlib.sha256(('209-witness-v1:'+r['id']).encode()).hexdigest(),i)
                    for i,r in enumerate(rows) if r['split']=='train']
        self.witness_indices = sorted(i for _,i in sorted(eligible)[:12])
        self.witness_ids = [rows[i]['id'] for i in self.witness_indices]
        self.witness_input = {'sparse':stats(all_inputs[0][self.witness_indices]),
                              'distance':stats(all_inputs[1][self.witness_indices]),
                              'active_per_view':all_inputs[0][self.witness_indices].sum(dim=-1).tolist()}

    def train(self, mode=True):
        result = super().train(mode)
        if not mode:
            self.eval_offset = 0
            self.witness_layers = {'ft':[],'h':[],'out':[]}
        return result

    def layer_hook(self, name):
        def hook(module, args, output):
            if self.training and self.train_step in POINTS:
                self.pending[name] = relu_stats(output) if name!='out' else {'pre_tanh':stats(output)}
            elif not self.training and self.selected_local:
                for local in self.selected_local:
                    t = output[local].detach()
                    self.witness_layers[name].append(relu_stats(t) if name!='out' else {'pre_tanh':float(t.item())})
        return hook

    def forward(self, x, d, side):
        if self.training:
            self.train_step += 1
            if self.train_step in POINTS:
                self.pending = {'inputs':{'sparse':stats(x),'distance':stats(d),
                                          'active_per_view':stats(x.sum(dim=-1))}}
                self.active_columns = x.detach().sum(dim=(0,1)) > 0
        else:
            self.selected_local = [i-self.eval_offset for i in self.witness_indices
                                   if self.eval_offset <= i < self.eval_offset+len(x)]
        result = super().forward(x,d,side)
        if not self.training:
            self.eval_offset += len(x)
        return result

def observed_step(optimizer, model, step, indices, targets, predicted):
    model.batch_hasher.update(json.dumps(indices,separators=(',',':')).encode()+b'\n')
    selected = step in POINTS
    before = {k:p.detach().clone() for k,p in model.named_parameters()} if selected else {}
    if selected:
        row = {'step':step,'batch_order_prefix_SHA':model.batch_hasher.hexdigest(),
               'batch_target':stats(targets),'batch_output':stats(predicted),
               'batch_residual':stats(predicted.detach()-targets.detach()),
               'tanh_derivative':stats(1-predicted.detach().square()),
               'output_saturation_abs_ge_0_9':(predicted.detach().abs()>=.9).float().mean().item(),
               'activation':model.pending,'layers':{}}
        for name in ['ft','h','out']:
            ps = list(getattr(model,name).parameters())
            grads = torch.cat([p.grad.detach().reshape(-1) for p in ps])
            weights = torch.cat([p.detach().reshape(-1) for p in ps])
            row['layers'][name] = {'gradient_norm':grads.norm().item(),
                 'gradient_zero_fraction':(grads==0).float().mean().item(),
                 'gradient_all_finite':bool(torch.isfinite(grads).all()),
                 'weight_norm_before':weights.norm().item()}
    optimizer.step()
    if selected:
        for name in ['ft','h','out']:
            old = torch.cat([v.reshape(-1) for k,v in before.items() if k.startswith(name+'.')])
            new = torch.cat([p.detach().reshape(-1) for k,p in model.named_parameters() if k.startswith(name+'.')])
            update = (new-old).norm().item()
            norm = old.norm().item()
            row['layers'][name].update({'actual_update_norm':update,
                  'update_to_weight_ratio':update/norm if norm else None,
                  'denominator_zero':norm==0})
        active = model.active_columns
        old = before['ft.weight'][:,active]
        diff = model.ft.weight.detach()[:,active]-old
        norm = old.norm().item()
        row['ft_active_columns'] = {'count':int(active.sum()),'total_columns':312,
               'actual_weight_update_norm':diff.norm().item(),'weight_norm_before':norm,
               'update_to_weight_ratio':diff.norm().item()/norm if norm else None,'denominator_zero':norm==0,
               'inactive_actual_weight_update_norm':(model.ft.weight.detach()[:,~active]-before['ft.weight'][:,~active]).norm().item(),
               'active_gradient_zero_fraction':(model.ft.weight.grad[:,active]==0).float().mean().item()}
        model.observations.append(row)

def observed_record(model, rows, values, record, out):
    import gzip
    values_w = [values[i] for i in model.witness_indices]
    if model.initial_values is None:
        model.initial_values = values_w
    changes = [v-v0 for v,v0 in zip(values_w,model.initial_values)]
    witness = {'step':record['step'],'IDs':model.witness_ids,'input_scale':model.witness_input,
               'prediction_step0_RMS_change':math.sqrt(sum(v*v for v in changes)/len(changes)),
               'prediction_step0_maxabs_change':max(abs(v) for v in changes),'rows':[]}
    for j,i in enumerate(model.witness_indices):
        witness['rows'].append({'id':rows[i]['id'],'prediction':values_w[j],'prediction_step0':model.initial_values[j],
              'target_rootmean':rows[i]['rootmean'],'residual':values_w[j]-rows[i]['rootmean'],
              'ft':model.witness_layers['ft'][j],'h':model.witness_layers['h'][j],
              'pre_tanh':model.witness_layers['out'][j]['pre_tanh']})
    # Each evaluation is stored as a deterministic gzip member; no raw duplicate.
    raw = (json.dumps(record,separators=(',',':'),allow_nan=False)+'\n').encode()
    with (Path(out)/'history.jsonl.gz').open('ab') as file:
        file.write(gzip.compress(raw,mtime=0))
    with (Path(out)/'witness.jsonl.gz').open('ab') as file:
        file.write(gzip.compress((json.dumps(witness,separators=(',',':'),allow_nan=False)+'\n').encode(),mtime=0))
