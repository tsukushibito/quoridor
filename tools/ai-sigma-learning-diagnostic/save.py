"""209 in-memory subtree Git save, preserving default index."""
import importlib.util
from pathlib import Path
import sys
spec=importlib.util.spec_from_file_location('readonly_saver','tools/nnue-training/save_research.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
m.D=Path('research-data/ai-sigma/frame15-learning-diagnostic');m.T=Path('tools/ai-sigma-learning-diagnostic')
m.DOC=m.D/'unused-doc';m.REPORT=Path('docs/reports/ai-sigma-hypothesis-learning-diagnostic.md')
m.save(sys.argv[1])
