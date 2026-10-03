"""Bounded NN0 evidence packing, memory restoration verification, no deletion."""
import hashlib, io, json, pathlib, tarfile, time
ROOT = pathlib.Path(__file__).resolve().parents[2]
A = ROOT / '.artifacts/ai-sigma/resume-20261003/CHECKPOINT-TEACHER'
D = ROOT / 'research-data/ai-sigma/181-checkpoint-teacher'
T = pathlib.Path(__file__).resolve().parent
start = time.monotonic()
files = [p for p in sorted(A.rglob('*')) if p.is_file() and not p.is_symlink()
         and 'xdg-cache' not in p.parts and 'xdg-config' not in p.parts and 't' not in p.relative_to(A).parts]
assert sum(p.stat().st_size for p in files) < 100*1024**2
members = {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
stream = io.BytesIO()
with tarfile.open(fileobj=stream, mode='w:gz', compresslevel=4) as archive:
    for p in files:
        body = p.read_bytes()
        info = tarfile.TarInfo(str(p.relative_to(ROOT))); info.size = len(body); info.mode = 0o644
        archive.addfile(info, io.BytesIO(body))
blob = stream.getvalue()
with tarfile.open(fileobj=io.BytesIO(blob), mode='r:gz') as restored:
    assert set(restored.getnames()) == set(members)
    for member in restored:
        assert hashlib.sha256(restored.extractfile(member).read()).hexdigest() == members[member.name]
allocated = 0; seen = set()
for base in [A,D,T]:
    for p in base.rglob('*'):
        if p.is_file():
            st=p.stat(); key=(st.st_dev,st.st_ino)
            if key not in seen: seen.add(key); allocated += st.st_blocks*512
# Archive, prospective compressed Git objects, restoration metadata stay inside reservation.
assert allocated + len(blob)*2 + 16*1024**2 < 224*1024**2
(D/'attemptpack.tar.gz').write_bytes(blob)
manifest = dict(issue='quoridor-4lc.181', archive='attemptpack.tar.gz',
    SHA256=hashlib.sha256(blob).hexdigest(), bytes=len(blob), members=members,
    contains='all seven attempt raw rows, game journals, commands, controls, input/source hashes, counters, resources and stops; no old model/cache copies',
    restore_prefix=str(ROOT), in_memory_restoration_verified=True, originals_retained=True,
    allocation_before_archive=allocated, conservative_Git_and_tail_headroom_bytes=16*1024**2,
    peak_forecast_allocated=allocated+len(blob)*2+16*1024**2, storage_guard_bytes=224*1024**2,
    wall_seconds=time.monotonic()-start)
(D/'archive-manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({k:v for k,v in manifest.items() if k not in ['members','contains']}))
