import pathlib,runpy,hashlib,json,subprocess,datetime
D=pathlib.Path("research-data/ai-sigma/frame16-coordinator")
m=runpy.run_path("tools/ai-sigma-manygame-plan/save_git.py");g=m["git"];edit=m["edit_tree"]
files=sorted(p for p in D.rglob("*") if p.is_file() and p.name!="Git-current.json")
files.append(pathlib.Path("docs/reports/ai-sigma-coordinator-current-priorities.md"))
assert sum(p.stat().st_size for p in files)<524288
index=pathlib.Path(g(["rev-parse","--git-path","index"]).decode().strip());before=hashlib.sha256(index.read_bytes()).hexdigest()
changes=[(p.parts,g(["hash-object","-w","--",str(p)]).decode().strip()) for p in files]
for attempt in range(5):
 parent=g(["rev-parse","HEAD"]).decode().strip();tree=edit(g(["rev-parse",parent+"^{tree}"]).decode().strip(),changes)
 c=g(["commit-tree",tree,"-p",parent,"-m","research: frame16 coordinator decisions and actual receipts"]).decode().strip()
 if subprocess.run(["git","update-ref","HEAD",c,parent],capture_output=True).returncode==0:break
else:raise RuntimeError("CAS conflict exhausted")
assert hashlib.sha256(index.read_bytes()).hexdigest()==before
for p in files:assert g(["show",c+":"+str(p)])==p.read_bytes(),str(p)
out={"UTC":datetime.datetime.now(datetime.timezone.utc).isoformat(),"Git":c,"files":len(files),"bytes":sum(p.stat().st_size for p in files),"byte_restore_PASS":True,"default_index_unchanged":True,"privateindex":0}
(D/"Git-current.json").write_text(json.dumps(out,indent=2)+"\n");print(json.dumps(out))
