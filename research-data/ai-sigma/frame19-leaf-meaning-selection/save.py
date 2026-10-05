from pathlib import Path
import importlib.util,sys
s=importlib.util.spec_from_file_location('save_research','tools/nnue-training/save_research.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
m.D=Path('research-data/ai-sigma/frame19-leaf-meaning-selection');m.T=m.D/'no-tools';m.DOC=m.D/'no-doc';m.REPORT=Path('docs/reports/ai-sigma-hypothesis-frame19-leaf-meaning.md')
m.save(sys.argv[1])
