"""220 management-only subtree Git, in-memory trees, no default index edits."""
import importlib.util,sys
from pathlib import Path
s=importlib.util.spec_from_file_location('readonly_saver','tools/nnue-training/save_research.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
m.D=Path('research-data/ai-sigma/frame16-generalization-selection');m.T=m.D/'unused-tools';m.DOC=m.D/'unused-doc';m.REPORT=Path('docs/reports/ai-sigma-hypothesis-generalization-selection.md');m.save(sys.argv[1])
