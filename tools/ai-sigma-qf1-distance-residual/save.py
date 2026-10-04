"""Small 200-only Git trees; inherited research saver stays read-only."""
import importlib.util
import sys
from pathlib import Path

spec=importlib.util.spec_from_file_location('readonly_saver','tools/nnue-training/save_research.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
m.D=Path('research-data/ai-sigma/frame14-distance-residual')
m.T=Path('tools/ai-sigma-qf1-distance-residual')
m.DOC=m.D/'unused-doc-scope'
m.REPORT=Path('docs/reports/ai-sigma-hypothesis-frame14-distance-residual.md')
m.save(sys.argv[1])
