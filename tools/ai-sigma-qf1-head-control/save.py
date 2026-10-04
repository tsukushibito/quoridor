"""204-only in-memory Git subtrees; default index unchanged."""
import importlib.util
from pathlib import Path
import sys

spec = importlib.util.spec_from_file_location('readonly_saver', 'tools/nnue-training/save_research.py')
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
m.D = Path('research-data/ai-sigma/frame14-head-control')
m.T = Path('tools/ai-sigma-qf1-head-control')
m.DOC = m.D / 'unused-doc'
m.REPORT = Path('docs/reports/ai-sigma-hypothesis-head-control.md')
m.save(sys.argv[1])
