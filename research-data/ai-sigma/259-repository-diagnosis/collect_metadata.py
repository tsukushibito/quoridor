"""Read-only, bounded repository observations for issue 259; no tool execution."""
import collections
import datetime
import hashlib
import json
import os
from pathlib import Path
import stat
import subprocess

MAIN = Path('/workspaces/quoridor')
RESEARCH = MAIN / '.worktree/ai-sigma'
OUT = RESEARCH / 'research-data/ai-sigma/259-repository-diagnosis'


def command(root, *args):
    return subprocess.check_output(['git', '-C', str(root), *args], timeout=45)


def head_files(root):
    result = {}
    for row in command(root, 'ls-tree', '-r', '-z', 'HEAD').split(b'\0'):
        if not row:
            continue
        metadata, name = row.split(b'\t', 1)
        result[os.fsdecode(name)] = metadata.decode().split()[2]
    return result


def index_files(root):
    result = {}
    for row in command(root, 'ls-files', '--stage', '-z').split(b'\0'):
        if not row:
            continue
        metadata, name = row.split(b'\t', 1)
        result[os.fsdecode(name)] = metadata.decode().split()[1]
    return result


def group(path, depth=2):
    return '/'.join(Path(path).parts[:depth])


def inventory(root, excluded=()):
    totals = collections.defaultdict(lambda: {'files': 0, 'logical_bytes': 0,
                                             'allocated_bytes': 0})
    files = {}
    links = []
    seen = set()
    errors = []
    for base, directories, names in os.walk(root, followlinks=False):
        relbase = Path(base).relative_to(root)
        directories[:] = [d for d in directories
                          if not (relbase == Path('.') and d in excluded)]
        for name in [*directories, *names]:
            path = Path(base) / name
            relative = str(path.relative_to(root))
            try:
                info = path.lstat()
            except OSError as error:
                errors.append({'path': relative, 'error': type(error).__name__})
                continue
            if stat.S_ISLNK(info.st_mode):
                if len(links) < 40:
                    links.append({'path': relative, 'target': os.readlink(path)})
                continue
            if not stat.S_ISREG(info.st_mode):
                continue
            files[relative] = (info.st_size, info.st_blocks * 512)
            inode = (info.st_dev, info.st_ino)
            if inode in seen:
                continue
            seen.add(inode)
            values = totals[group(relative)]
            values['files'] += 1
            values['logical_bytes'] += info.st_size
            values['allocated_bytes'] += info.st_blocks * 512
    return files, dict(totals), links, errors


def summarize_git(root, files):
    head = head_files(root)
    index = index_files(root)
    statuses = collections.Counter()
    representatives = collections.defaultdict(list)
    raw = command(root, 'status', '--porcelain=v1', '-z', '--untracked-files=no')
    for row in raw.split(b'\0'):
        if not row:
            continue
        code = row[:2].decode(errors='replace')
        statuses[code] += 1
        if len(representatives[code]) < 8:
            representatives[code].append(os.fsdecode(row[3:]))
    head_only = sorted(set(head) - set(index))
    index_only = sorted(set(index) - set(head))
    missing = [p for p in head if not (root / p).exists()]
    indexed_changes = [p for p in set(index) & set(head) if index[p] != head[p]]
    candidates = [p for p in files if p not in head]
    ignored = set()
    if candidates:
        proc = subprocess.run(['git', '-C', str(root), 'check-ignore', '--no-index',
                               '-z', '--stdin'], input=b'\0'.join(os.fsencode(p)
                                                                 for p in candidates)+b'\0',
                              capture_output=True, timeout=45)
        if proc.returncode not in (0, 1):
            raise RuntimeError(proc.stderr.decode(errors='replace'))
        ignored = {os.fsdecode(p) for p in proc.stdout.split(b'\0') if p}
    classes = collections.defaultdict(lambda: {'files': 0, 'logical_bytes': 0,
                                              'allocated_bytes': 0})
    untracked = []
    for path, (logical, allocated) in files.items():
        category = 'HEAD_tracked' if path in head else 'ignored' if path in ignored else 'untracked'
        values = classes[category]
        values['files'] += 1
        values['logical_bytes'] += logical
        values['allocated_bytes'] += allocated
        if category == 'untracked' and len(untracked) < 25:
            untracked.append(path)
    return {
        'head': command(root, 'rev-parse', 'HEAD').decode().strip(),
        'index_entries': len(index), 'head_entries': len(head),
        'head_only_count': len(head_only), 'head_only_sample': head_only[:12],
        'head_only_existing_count': sum((root / p).exists() for p in head_only),
        'index_only_count': len(index_only), 'index_only_sample': index_only[:12],
        'same_path_index_vs_HEAD_blob_difference_count': len(indexed_changes),
        'same_path_index_vs_HEAD_blob_difference_sample': sorted(indexed_changes)[:12],
        'HEAD_paths_missing_from_worktree_count': len(missing),
        'HEAD_paths_missing_sample': missing[:15],
        'default_status_counts': dict(statuses),
        'default_status_sample': dict(representatives),
        'physical_files_by_git_category_relative_to_HEAD': dict(classes),
        'untracked_sample': untracked,
        'classification_note': 'HEAD membership, not stale default-index membership; symlinks not followed',
    }


def source_duplicates(files):
    suffixes = {'.py', '.js', '.cjs', '.mjs', '.rs'}
    groups = collections.defaultdict(list)
    scanned = 0
    for relative, (size, _) in files.items():
        path = Path(relative)
        if not relative.startswith('tools/') or path.suffix not in suffixes:
            continue
        if not (path.parts[1].startswith('ai-sigma-') or path.parts[1] == 'nnue-training'):
            continue
        if any(p in {'deps', 'node_modules', 'target', 'build'} for p in path.parts) or size > 524288:
            continue
        groups[(size, hashlib.sha256((RESEARCH/path).read_bytes()).hexdigest())].append(relative)
        scanned += 1
    duplicates = [{'bytes_per_file': size, 'sha256': digest, 'paths': sorted(paths),
                   'redundant_logical_bytes': size*(len(paths)-1)}
                  for (size, digest), paths in groups.items() if len(paths) > 1]
    duplicates.sort(key=lambda x: x['redundant_logical_bytes'], reverse=True)
    return {'scanned_small_research_source_files': scanned,
            'exact_duplicate_groups': len(duplicates),
            'redundant_source_logical_bytes': sum(x['redundant_logical_bytes'] for x in duplicates),
            'representative_groups': duplicates[:20],
            'excluded': 'deps/build/target/node_modules, files >512KiB; no history-wide scan',
            'deletion_eligibility_proven': False}


def main():
    observations = {'at': datetime.datetime.now(datetime.timezone.utc).isoformat(),
                    'measurement': 'current stat metadata, per-root inode de-dup; logical vs allocated separately',
                    'symlink_targets_followed': False, 'scopes': {}}
    allresearch = None
    for name, root, excluded in [('main', MAIN, {'.git', '.worktree'}),
                                  ('research', RESEARCH, set())]:
        files, totals, links, errors = inventory(root, excluded)
        observations['scopes'][name] = {
            'root': str(root), 'excluded_top_level': sorted(excluded),
            'top_level_total': {key: sum(v[key] for v in totals.values())
                                for key in ['files', 'logical_bytes', 'allocated_bytes']},
            'directory_groups': totals, 'symlink_sample': links, 'read_errors': errors,
            'largest_files': [{'path': p, 'logical_bytes': values[0], 'allocated_bytes': values[1]}
                              for p, values in sorted(files.items(), key=lambda x:x[1][0], reverse=True)[:20]],
            'git': summarize_git(root, files),
        }
        if name == 'research':
            allresearch = files
    _, totals, links, errors = inventory(MAIN/'.git')
    observations['shared_git'] = {
        'root': str(MAIN/'.git'), 'directory_groups': totals,
        'allocated_bytes': sum(v['allocated_bytes'] for v in totals.values()),
        'count_objects_v': command(RESEARCH, 'count-objects', '-v').decode(),
        'read_errors': errors,
    }
    observations['source_duplication'] = source_duplicates(allresearch)
    tools = collections.Counter(Path(p).parts[1] for p in allresearch
                                if p.startswith('tools/') and len(Path(p).parts) > 1)
    observations['research_tool_directories'] = dict(sorted(tools.items()))
    (OUT/'metadata.json').write_text(json.dumps(observations, ensure_ascii=False, indent=2)+'\n')
    print(json.dumps({'scopes': {k:{'totals':v['top_level_total'], 'git':{
        key:v['git'][key] for key in ['head_entries','index_entries','head_only_count',
                                     'head_only_existing_count','HEAD_paths_missing_from_worktree_count',
                                     'default_status_counts']}}
         for k,v in observations['scopes'].items()},
        'shared_git_allocated_bytes': observations['shared_git']['allocated_bytes'],
        'tool_directory_count': len(tools),
        'exact_source_duplicate_groups': observations['source_duplication']['exact_duplicate_groups']},
         ensure_ascii=False))


if __name__ == '__main__':
    main()
