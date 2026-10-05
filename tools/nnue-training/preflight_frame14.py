"""NN0 interpreter/AST/argv/deadline checks; never imports Torch or a model."""
import ast
import hashlib
import json
import os
from pathlib import Path

HERE=Path(__file__).resolve().parent
PYTHON=Path('/home/vscode/.cache/inference/envs/quoridor-training/bin/python')
assert PYTHON.is_file() and os.access(PYTHON,os.X_OK)
sources={}
for p in HERE.glob('*.py'):
    ast.parse(p.read_text(),filename=str(p))
    sources[p.name]=hashlib.sha256(p.read_bytes()).hexdigest()
argv=[str(PYTHON),'-B',str(HERE/'train.py'),'--data','STAGE.stage.json','--config',
      'research-data/ai-sigma/frame14-learning/qf1-frame14.json','--run-id','frame14-train24-r1',
      '--output','research-data/ai-sigma/frame14-learning/runs','--checkpoints','models/experiments/nnue']
print(json.dumps({'AST_PASS':True,'executable':str(PYTHON),'launch_argv_example':argv,
                  'newheavy':'2026-10-04T02:45:00Z','science_stop':'2026-10-04T02:50:00Z',
                  'job_hard_seconds':120,'sample_total_cap':5000000,'source_sha256':sources,
                  'Torch_imported':False,'model_or_session_loaded':False}))
