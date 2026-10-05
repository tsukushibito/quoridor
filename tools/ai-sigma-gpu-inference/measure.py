"""One fixed parity run; timing is conditional on all five inputs passing."""
import os, time, json, hashlib, resource, traceback, sys, copy, struct
from pathlib import Path
D = Path('research-data/ai-sigma/174-gpu-inference')
def write(o):
    (D/'results.json').write_text(json.dumps(o, indent=2)+'\n')
start = time.perf_counter()
out = {'run':'folded-gpu-r1','status':'STARTED','parity':[], 'timing':{}, 'training':0,'game':0,'batch':1}
write(out)
try:
    import numpy as np
    import torch
    import onnxruntime as ort
    from adapter import load
    import_done = time.perf_counter()
    torch.set_num_threads(1); torch.set_num_interop_threads(1)
    torch.set_float32_matmul_precision('highest')
    torch.backends.cuda.matmul.allow_tf32 = False
    torch.backends.cudnn.allow_tf32 = False
    torch.backends.cudnn.benchmark = False
    assert not torch.backends.cuda.matmul.allow_tf32 and not torch.backends.cudnn.allow_tf32
    cfg = json.loads((D/'preregister.json').read_text())
    inp = json.loads((D/'inputs.json').read_text())
    assert hashlib.sha256((D/'inputs.json').read_bytes()).hexdigest() == cfg['inputs_sha256']
    model = cfg['model']
    assert hashlib.sha256(Path(model).read_bytes()).hexdigest() == cfg['model_sha256']
    options = ort.SessionOptions(); options.intra_op_num_threads=1; options.inter_op_num_threads=1
    options.execution_mode=ort.ExecutionMode.ORT_SEQUENTIAL
    t=time.perf_counter(); session=ort.InferenceSession(model,options,providers=['CPUExecutionProvider']); ortinit=time.perf_counter()-t
    assert session.get_providers() == ['CPUExecutionProvider']
    t=time.perf_counter(); cpu=load(model); cpuinit=time.perf_counter()-t
    assert not cpu.training and all(x.dtype==torch.float32 for x in cpu.buffers())
    t=time.perf_counter(); torch.cuda.synchronize(); torch.cuda.reset_peak_memory_stats()
    torch.cuda.set_per_process_memory_fraction(cfg['VRAM_guard_B']/torch.cuda.get_device_properties(0).total_memory,0)
    gpu=copy.deepcopy(cpu).to('cuda'); gpu.eval(); torch.cuda.synchronize(); gpuinit=time.perf_counter()-t
    assert not gpu.training and all(x.dtype==torch.float32 for x in gpu.buffers())
    out['initialization_s']={'imports':import_done-start,'CPUORT_session':ortinit,'torchCPU_graph_and_weights':cpuinit,'CUDA_context_and_upload':gpuinit}
    out['settings']={'torch':torch.__version__,'ORT':ort.__version__,'device':torch.cuda.get_device_name(),'intra':torch.get_num_threads(),'interop':torch.get_num_interop_threads(),'AMP':False,'matmul_TF32':torch.backends.cuda.matmul.allow_tf32,'cudnn_TF32':torch.backends.cudnn.allow_tf32,'cudnn_benchmark':torch.backends.cudnn.benchmark,'dtype':'float32','CPU_affinity':sorted(os.sched_getaffinity(0))}
    write(out)
    def request(backend, a):
        if backend=='torchCUDA': torch.cuda.synchronize()
        t=time.perf_counter_ns(); fresh=a.copy(); input_ready=time.perf_counter_ns()
        if backend=='CPUORT':
            p,v=session.run(['policy_logits','value'],{'input':fresh}); p=p.copy();v=v.copy()
            stages=None
        elif backend=='torchCPU':
            tensor=torch.from_numpy(fresh); p,v=cpu(tensor); p=p.numpy().copy();v=v.numpy().copy();stages=None
        else:
            tensor=torch.from_numpy(fresh).to('cuda'); torch.cuda.synchronize(); h2d=time.perf_counter_ns()
            p,v=gpu(tensor); torch.cuda.synchronize(); kernel=time.perf_counter_ns()
            p=p.to('cpu').numpy().copy();v=v.to('cpu').numpy().copy();torch.cuda.synchronize();d2h=time.perf_counter_ns()
            stages={'host_input_copy_ms':(input_ready-t)/1e6,'H2D_sync_ms':(h2d-input_ready)/1e6,'forward_sync_ms':(kernel-h2d)/1e6,'D2H_sync_ms':(d2h-kernel)/1e6}
        end=time.perf_counter_ns()
        if backend=='torchCUDA': assert torch.cuda.max_memory_reserved()<cfg['VRAM_guard_B'], 'VRAM_GUARD'
        assert p.shape==(1,136) and v.shape==(1,1) and np.isfinite(p).all() and np.isfinite(v).all()
        assert abs(float(v[0,0]))<=1
        return p,v,{'response_wall_ms':(end-t)/1e6,'stages':stages}
    arrays=[np.asarray(x['features_bits'],dtype=np.uint32).view(np.float32).reshape(1,8,9,9) for x in inp['inputs']]
    passed=True
    with torch.inference_mode(), torch.autocast(device_type='cuda',enabled=False):
        for fixture,a in zip(inp['inputs'],arrays):
            r={};times={}
            for backend in cfg['parity_backends']:
                p,v,tm=request(backend,a);r[backend]=(p,v);times[backend]=tm
            checks={}
            for pair in cfg['pairwise_comparisons']:
                one,two=pair.split('-');checks[pair]={}
                for j,name in enumerate(('policy','value')):
                    x,y=r[one][j],r[two][j];delta=np.abs(x-y)
                    ok=bool(np.all(delta<=cfg['abs_tol']+cfg['rel_tol']*np.abs(x)))
                    checks[pair][name]={'max_abs':float(delta.max()),'pass':ok};passed &= ok
            out['parity'].append({'fixture':fixture['fixture'],'outputs':{b:{'policy':r[b][0].reshape(-1).tolist(),'value':float(r[b][1][0,0])} for b in r},'response':times,'comparisons':checks})
            write(out)
        out['parity_pass']=bool(passed)
        if passed:
            for backend in cfg['parity_backends']:
                warm=request(backend,arrays[0])[2]
                steady=[request(backend,arrays[0])[2] for _ in range(8)]
                out['timing'][backend]={'fixture':inp['inputs'][0]['fixture'],'warm1':warm,'steady8':steady,'session_weights_reused':True,'input_fresh_copy_each_request':True}
                write(out)
        out['CUDA_memory']={'allocated_current_B':torch.cuda.memory_allocated(),'reserved_current_B':torch.cuda.memory_reserved(),'peak_allocated_B':torch.cuda.max_memory_allocated(),'peak_reserved_B':torch.cuda.max_memory_reserved()}
        assert out['CUDA_memory']['peak_reserved_B']<cfg['VRAM_guard_B'], 'VRAM_GUARD'
    out['status']='COMPLETED' if passed else 'PARITY_FAILURE_TIMING_NOT_STARTED'
    out['scientific_forwards_each']=5+(9 if passed else 0)
    torch.cuda.synchronize()
    del gpu,cpu,session
    torch.cuda.empty_cache();torch.cuda.synchronize()
    out['CUDA_after_release']={'allocated_B':torch.cuda.memory_allocated(),'reserved_B':torch.cuda.memory_reserved()}
except Exception as e:
    out['status']='TYPED_FAILURE';out['failure']={'type':type(e).__name__,'message':str(e),'traceback':traceback.format_exc()}
finally:
    out['total_elapsed_s']=time.perf_counter()-start;out['peak_RSS_KiB']=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    write(out)
    print(json.dumps({'status':out['status'],'elapsed_s':out['total_elapsed_s'],'peak_RSS_KiB':out['peak_RSS_KiB'],'parity_pass':out.get('parity_pass')}),flush=True)
