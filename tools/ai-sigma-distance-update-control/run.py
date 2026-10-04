"""One all-layer optimizer coordinate control; immutable trainer and observers."""
from pathlib import Path
import argparse,hashlib,importlib.util,json,sys,time
R=Path.cwd();D=R/'research-data/ai-sigma/frame15-distance-update-control';T=R/'tools/ai-sigma-distance-update-control';sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest();reg=json.loads((D/'preregister.json').read_text())
for p,h in {**reg['sources'],**reg['private_sources']}.items():assert sha(R/p)==h,p
assert sha(D/'scale.json')==reg['scale_SHA'];assert sha(reg['raw_initial_path'])==reg['raw_initial_checkpoint_SHA']
sys.path.insert(0,str(R/'tools/ai-sigma-learning-diagnostic'));sys.path.insert(0,str(R/'tools/nnue-training'))
spec=importlib.util.spec_from_file_location('stopped209',R/'tools/ai-sigma-learning-diagnostic/run.py');adapt=importlib.util.module_from_spec(spec);spec.loader.exec_module(adapt);trainer,edits=adapt.adapted()
import torch,model
RawModel=model.Model
from observer import DiagnosticModel,observed_step,observed_record,stats
scale=json.loads((D/'scale.json').read_text())
class ScaleModel(DiagnosticModel):
 def __init__(self,config):
  super().__init__(config);self.raw_cfg=config;self.mu=torch.tensor(scale['mu_f32']);self.sigma=torch.tensor(scale['sigma_f32']);self.parity_samples=0;self.parity_maxabs=0.;self.transformed=False
 def load_state_dict(self,state_dict,*args,**kwargs):
  result=super().load_state_dict(state_dict,*args,**kwargs);assert not self.transformed
  with torch.random.fork_rng(devices=[]):raw=RawModel(self.raw_cfg)
  raw.load_state_dict(state_dict);raw.eval();object.__setattr__(self,'raw_reference',raw)
  with torch.no_grad():
   w=self.h.weight[:,-2:].clone();self.h.bias.copy_(self.h.bias+w@self.mu);self.h.weight[:,-2:].copy_(w*self.sigma)
  self.transformed=True;return result
 def bind_rows(self,rows,all_inputs):
  super().bind_rows(rows,all_inputs);self.witness_input['distance_standardized']=stats((all_inputs[1][self.witness_indices]-self.mu)/self.sigma)
 def forward(self,x,d,side):
  assert self.transformed
  y=super().forward(x,(d-self.mu)/self.sigma,side)
  if not self.training and self.train_step==0:
   with torch.inference_mode():v=self.raw_reference(x,d,side)
   self.parity_samples+=len(x);self.parity_maxabs=max(self.parity_maxabs,(y-v).abs().max().item())
   assert self.parity_samples<=5901
  return y
model.Model=ScaleModel
def scale_observed_step(opt,mdl,step,indices,targets,predicted):
 selected=step in reg['points'];original_step=opt.step;before_w=mdl.h.weight[:,-2:].detach().clone();before_b=mdl.h.bias.detach().clone();proposal=None;applied=None;moment_equal=True;other_equal=True
 def state_sha():
  return hashlib.sha256(b''.join(v.detach().cpu().numpy().tobytes() for v in opt.state[mdl.h.weight].values() if torch.is_tensor(v))).hexdigest()
 def other_sha():
  parts=[]
  for name,v in mdl.named_parameters():parts.append((v[:,:-2] if name=='h.weight' else v).detach().cpu().numpy().tobytes())
  return hashlib.sha256(b''.join(parts)).hexdigest()
 def attenuated_step(*a,**kw):
  nonlocal proposal,applied,moment_equal,other_equal
  result=original_step(*a,**kw);proposal=mdl.h.weight[:,-2:].detach().clone()-before_w
  if selected:ms=state_sha();others=other_sha()
  with torch.no_grad():mdl.h.weight[:,-2:].copy_(before_w+proposal*mdl.sigma)
  applied=mdl.h.weight[:,-2:].detach().clone()-before_w
  if selected:moment_equal=ms==state_sha();other_equal=others==other_sha()
  if step==1:
   ratios=[]
   for c in range(2):
    nonzero=proposal[:,c]!=0;ratio=(applied[:,c][nonzero]/proposal[:,c][nonzero]).detach();ratios.append({'nonzero':int(nonzero.sum()),'proposal_zero_unknown_ratio':int((~nonzero).sum()),'nonzero_proposal_applied_rounding_zero':int((nonzero&(applied[:,c]==0)).sum()),'min':float(ratio.min())if len(ratio)else None,'max':float(ratio.max())if len(ratio)else None,'expected_sigma':float(mdl.sigma[c])})
   requested=proposal*mdl.sigma;error=(applied-requested).abs();bound=torch.finfo(before_w.dtype).eps*4*(before_w.abs()+(before_w+requested).abs()+requested.abs());passed=bool(torch.isfinite(proposal).all()and torch.isfinite(applied).all()and  (error<=bound).all()and moment_equal and other_equal)
   receipt={'PASS':passed,'step':1,'nonzero_proposal_count':int((proposal!=0).sum()),'proposal_zero_unknown_ratio_count':int((proposal==0).sum()),'nonzero_proposal_applied_zero_count':int(((proposal!=0)&(applied==0)).sum()),'zero_proposal_or_rounding_zero_is_fault':False,'proposal_to_applied_ratio_by_column':ratios,'maxabs_applied_minus_requested':float(error.max()),'max_f32_roundoff_bound':float(bound.max()),'roundoff_rule':'4*eps*(abs(before)+abs(before+requested)+abs(requested)); applied delta is difference of f32 params','proposal_moments_unchanged':moment_equal,'bias_otherparams_unchanged_afterproposal':other_equal,'optimizer_group_split_or_reset':False,'extra_forward_backward':0};(D/'first-proposal-finite.json').write_text(json.dumps(receipt,indent=2)+'\n');assert passed,'ATTENUATION_FINITE_FAILED'
  return result
 opt.step=attenuated_step
 try:observed_step(opt,mdl,step,indices,targets,predicted)
 finally:opt.step=original_step
 if selected:
  db=mdl.h.bias.detach()-before_b;rawdw=applied/mdl.sigma;rawdb=db-(applied*(mdl.mu/mdl.sigma)).sum(dim=1)
  def stat(t):return {'norm':t.norm().item(),'RMS':t.square().mean().sqrt().item(),'maxabs':t.abs().max().item()}
  mdl.observations[-1]['distance_coordinate_update']={'Before_Wd_standardized':stat(before_w),'After_Adam_proposal_Wd_standardized':stat(before_w+proposal),'After_applied_Wd_standardized':stat(mdl.h.weight[:,-2:].detach()),'Adam_proposal_Wd_standardized':stat(proposal),'Ideal_sigma_times_proposal_standardized':stat(proposal*mdl.sigma),'Applied_Wd_standardized':stat(applied),'DeltaBias_standardized':stat(db),'Applied_Wd_raw':stat(rawdw),'Applied_Bias_raw':stat(rawdb),'proposal_vs_raw_maxabs':float((rawdw-proposal).abs().max()),'proposal_zero_ratio_unknown':int((proposal==0).sum()),'proposal_nonzero_applied_zero':int(((proposal!=0)&(applied==0)).sum()),'proposal_moments_unchanged':moment_equal,'bias_otherparams_afterproposal_unchanged':other_equal,'raw_bias_rule':"dbprime-sum(actualdwprime*mu/sigma)",'extra_forward_backward':0};assert moment_equal and other_equal
trainer.observed_step=scale_observed_step
def record(mdl,rows,values,rec,out):
 if rec['step']==0:
  p={'PASS':mdl.parity_samples==5901 and mdl.parity_maxabs<=1e-6,'raw_additional_forward_samples':mdl.parity_samples,'scaled_initial_forward_already_charged':5901,'maxabs':mdl.parity_maxabs,'atol':1e-6,'train_rows':4653,'validation_rows':1248,'test_rows':0,'no_step_before_parity':True,'raw_tensor_SHA':reg['raw_initial_tensor_SHA'],'scaled_initial_tensor_SHA':json.loads((out/'dataset.json').read_text())['initial_state_sha256']};(D/'initial-function-parity.json').write_text(json.dumps(p,indent=2)+'\n');assert p['PASS'] and p['scaled_initial_tensor_SHA']==reg['expected_scaled_initial_tensor_SHA'],'INITIAL_FUNCTION_PARITY_FAILED'
 return observed_record(mdl,rows,values,rec,out)
trainer.observed_record=record
args=argparse.Namespace(run_id=reg['run_id'],config=D/'config.json',set=[],data=reg['stage_path'],dry_run=False,output=D/'runs',checkpoints=R/'models/experiments/nnue',init_checkpoint=reg['raw_initial_path'])
try:
 trainer.train(args)
finally:
 out=D/'runs'/reg['run_id'];mdl=ScaleModel.instances[-1] if ScaleModel.instances else None
 if (out/'summary.json').exists():
  finite_samples=json.loads((out/'summary.json').read_text())['all_samples']+(mdl.parity_samples if mdl else 0);(D/'actual-sample-receipt.json').write_text(json.dumps({'samples':finite_samples,'GPU':0,'warm':0},indent=2)+'\n')
summary=json.loads((out/'summary.json').read_text());assert summary['all_samples']==110210 and summary['step']==400 and mdl.parity_samples==5901
assert mdl.batch_hasher.hexdigest()==reg['same_batch_order_400_SHA']
(out/'observer.json').write_text(json.dumps({'batch_order_400_SHA':mdl.batch_hasher.hexdigest(),'observations':mdl.observations,'optimizer_all_parameter_names':[k for k,p in mdl.named_parameters()if p.requires_grad],'observer_extra_forward':0,'extra_raw_parity_forward':5901,'points':reg['points']},indent=2)+'\n')
summary['all_samples_including_parity']=summary['all_samples']+mdl.parity_samples;(D/'actual-sample-receipt.json').write_text(json.dumps({'samples':summary['all_samples_including_parity'],'train_samples':51200,'eval_samples':59010,'raw_parity_samples':5901,'GPU':0,'warm':0},indent=2)+'\n')
print(json.dumps({'samples':summary['all_samples_including_parity'],'initial_parity_maxabs':mdl.parity_maxabs,'same_batch_order':True}))
