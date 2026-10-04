from pathlib import Path
import hashlib
p=Path('tools/ai-sigma-frame18-data-learning/gen_guard.py')
assert hashlib.sha256(p.read_bytes()).hexdigest()=='2d211e4bd739344778bd68fe86973d85f65943495db1449ec4fb15035094d768'
code=p.read_text()
needle="exec(compile(s,str(P)+' [228 bounded private admission/lifecycle]','exec'),globals())"
assert code.count(needle)==1
code=code.replace(needle,'\nfor before,after in [(\'current=[];foreign=[];rss=0\', "owned_ancestor_ticks={}\\nancestor_tab=table();parent=ancestor_tab[os.getpid()][\'ppid\'];seen=set()\\nwhile parent in ancestor_tab and parent not in seen:\\n seen.add(parent);owned_ancestor_ticks[parent]=ancestor_tab[parent][\'tick\'];parent=ancestor_tab[parent][\'ppid\']\\ncurrent=[];foreign=[];rss=sum(ancestor_tab[p][\'RSS\']for p in owned_ancestor_ticks)"), ("if pid==os.getpid() or z[\'state\']==\'Z\':continue", "if pid==os.getpid() or z[\'state\']==\'Z\' or owned_ancestor_ticks.get(pid)==z[\'tick\']:continue"), ("if fp==os.getpid()or fz[\'state\']==\'Z\'or(fp,fz[\'tick\'])in tracked:continue", "if fp==os.getpid()or fz[\'state\']==\'Z\'or(fp,fz[\'tick\'])in tracked or owned_ancestor_ticks.get(fp)==fz[\'tick\']:continue"), (\'prior_jobwall_s=spent,\', \'owned_control_ancestor_PIDticks=owned_ancestor_ticks,prior_jobwall_s=spent,\')]:\n assert s.count(before)==1,before\n s=s.replace(before,after)\n'+needle)
exec(compile(code,str(p)+' [background exact ancestor adaptation]','exec'),globals())
