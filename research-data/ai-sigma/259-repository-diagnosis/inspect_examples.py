"""Bounded read-only examples for diagnosis 259; no imports of research engines."""
import collections
import datetime
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tarfile

R = Path('/workspaces/quoridor/.worktree/ai-sigma')
M = Path('/workspaces/quoridor')
D = R / 'research-data/ai-sigma/259-repository-diagnosis'


def git(*args):
    return subprocess.check_output(['git', '-C', str(R), *args], timeout=45)


def main():
    result = {'at': datetime.datetime.now(datetime.timezone.utc).isoformat()}
    head = {}
    for row in git('ls-tree', '-r', '-z', 'HEAD').split(b'\0'):
        if row:
            meta, path = row.split(b'\t', 1)
            head[os.fsdecode(path)] = meta.split()[2].decode()
    result['HEAD'] = git('rev-parse', 'HEAD').decode().strip()
    result['missing_HEAD_paths'] = [p for p in head if not (R/p).exists()]
    exported = {os.fsdecode(p) for p in git('ls-files', '-z', '--cached', '--others',
                                          '--exclude-standard').split(b'\0') if p}
    omitted = [p for p in head if (R/p).exists() and p not in exported]
    result['exporter_enumeration'] = {
        'command': 'git ls-files -z --cached --others --exclude-standard',
        'existing_HEAD_paths_omitted_count': len(omitted),
        'omitted_by_top_path': dict(collections.Counter('/'.join(Path(p).parts[:2]) for p in omitted)),
        'sample': omitted[:12],
        'script_was_NOT_executed': True,
    }
    groups = {}
    largest = []
    archives = []
    for prefix in ['.artifacts/ai-sigma', 'research-data/ai-sigma']:
        seen = set()
        for base, dirs, files in os.walk(R/prefix, followlinks=False):
            for name in files:
                p = Path(base)/name
                if p.is_symlink():
                    continue
                st = p.stat()
                inode = (st.st_dev, st.st_ino)
                if inode in seen:
                    continue
                seen.add(inode)
                rel = str(p.relative_to(R))
                group = '/'.join(Path(rel).parts[:3])
                v = groups.setdefault(group, {'files': 0, 'logical': 0, 'allocated': 0,
                                             'HEAD_logical': 0, 'HEAD_allocated': 0})
                v['files'] += 1
                v['logical'] += st.st_size
                v['allocated'] += st.st_blocks*512
                if rel in head:
                    v['HEAD_logical'] += st.st_size
                    v['HEAD_allocated'] += st.st_blocks*512
                if st.st_size > 1_048_576:
                    largest.append({'path': rel, 'logical': st.st_size,
                                    'allocated': st.st_blocks*512, 'in_HEAD': rel in head})
                if rel.startswith('research-data/ai-sigma/frame20-learning-effect/') and name.endswith(('.tar.gz', '.tgz')):
                    archives.append(p)
    result['scoped_capacity'] = sorted(groups.items(), key=lambda x: x[1]['allocated'], reverse=True)
    result['large_scoped_files'] = sorted(largest, key=lambda x: x['allocated'], reverse=True)[:25]
    examples = [
        'tools/ai-sigma-native-baseline/game.js',
        'tools/ai-sigma-arena-matches/game.js',
        'tools/ai-sigma-manygame-generation/gamepool.cjs',
        'tools/ai-sigma-manygame-generation/pause-monitor.cjs',
        'tools/ai-sigma-worker-balance/generate.cjs',
        'tools/ai-sigma-frame20-distance-arena/engine.cjs',
        'tools/ai-sigma-frame18-native-connection/native.cjs',
        'tools/ai-sigma-nnue-qf1-prototype/qf1.cjs',
        'tools/nnue-training/model.py',
        'tools/nnue-training/frame14_data.py',
        'tools/ai-sigma-frame20-learning-effect/save_git.py',
        'scripts/export-fresh-source.mjs',
    ]
    records = []
    for rel in examples:
        data = (R/rel).read_bytes()
        blob = git('show', 'HEAD:'+rel) if rel in head else None
        lines = data.decode().splitlines()
        references = [{'line': i, 'text': s[:650]} for i, s in enumerate(lines, 1)
                      if any(t in s for t in ('require(', 'from frame', 'sys.path.', 'windowEndUTC',
                                             'ls-files', 'update-ref', 'private', 'cache/inference'))]
        records.append({'path': rel, 'bytes': len(data), 'lines': len(lines),
                        'max_line_chars': max(map(len, lines), default=0),
                        'sha256': hashlib.sha256(data).hexdigest(),
                        'matches_HEAD': blob == data, 'references': references[:8]})
    result['source_examples'] = records
    result['archive_sample'] = None
    for p in sorted(archives, key=lambda p: p.stat().st_size):
        if p.stat().st_size > 2_097_152:
            continue
        with tarfile.open(p, 'r:gz') as tar:
            members = tar.getmembers()
            checks = []
            for member in members:
                if not member.isfile() or member.size > 65_536:
                    continue
                stream = tar.extractfile(member)
                data = stream.read()
                current = R/member.name
                checks.append({'member': member.name, 'bytes': len(data),
                               'sha256': hashlib.sha256(data).hexdigest(),
                               'matches_current': current.is_file() and current.read_bytes() == data})
                if len(checks) == 3:
                    break
        result['archive_sample'] = {'path': str(p.relative_to(R)), 'compressed_bytes': p.stat().st_size,
                                    'in_HEAD': str(p.relative_to(R)) in head,
                                    'members': len(members), 'sample': checks,
                                    'extraction_to_disk': False, 'all_archives_verified': False}
        break
    (D/'examples.json').write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n')
    print(json.dumps({'missing_HEAD_paths': len(result['missing_HEAD_paths']),
                      'exporter': result['exporter_enumeration'],
                      'largest_scope_groups': result['scoped_capacity'][:12],
                      'archive': result['archive_sample'],
                      'source_examples': len(records)}, ensure_ascii=False))


if __name__ == '__main__':
    main()
