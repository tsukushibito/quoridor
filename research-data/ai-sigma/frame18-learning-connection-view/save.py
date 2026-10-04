from pathlib import Path
import importlib.util,sys
s=importlib.util.spec_from_file_location('saved_git','tools/nnue-training/save_research.py')
m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
m.D=Path('research-data/ai-sigma/frame18-learning-connection-view')
m.T=m.D/'unused-tools';m.DOC=m.D/'unused-doc'
m.REPORT=Path('docs/reports/ai-sigma-hypothesis-learning-connection.md')
m.save(sys.argv[1])
