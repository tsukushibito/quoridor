"""Existing plotting environment; saved summaries only, no model or forward."""
from pathlib import Path
import datetime,json,time
start=time.monotonic();D=Path('research-data/ai-sigma/frame18-data-learning')
summary=json.loads((D/'learning-test-summary.json').read_text());stages=summary['stages'];test=summary['newtest']
histories={n:[json.loads(x)for x in(D/'learning-runs'/f'frame18-growth228-plan{n}-positive{n}-r1'/'history.jsonl').read_text().splitlines()]for n in [192,576]}
source=Path('tools/ai-sigma-frame18-data-learning/finalize.py').read_text();plot=source[source.index('import matplotlib\n'):];exec(compile(plot,'[saved plotting segment]','exec'))
