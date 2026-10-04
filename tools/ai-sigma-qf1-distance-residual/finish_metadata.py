"""No-forward final metrics/costs and byte-preserving checkpoint archive."""
import datetime
import hashlib
import io
import json
import lzma
from pathlib import Path
import tarfile

D = Path('research-data/ai-sigma/frame14-distance-residual')
T = Path('tools/ai-sigma-qf1-distance-residual')
REPORT = Path('docs/reports/ai-sigma-hypothesis-distance-residual.md')
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
e = json.loads((D / 'evaluator-settings.json').read_text())
r = json.loads((D / 'test-evaluation-r1/result.json').read_text())
stop = json.loads((D / 'science-stop.json').read_text())
for p, h in stop['source_frozen'].items():
    assert sha(p) == h
buffer = io.BytesIO()
members = {}
with tarfile.open(fileobj=buffer, mode='w') as tar:
    for name, info in e['checkpoints'].items():
        p = Path(info['path'])
        assert sha(p) == info['checkpoint_SHA']
        b = p.read_bytes()
        header = tarfile.TarInfo(name + '.pt')
        header.size = len(b)
        header.mode = 0o644
        header.mtime = 0
        tar.addfile(header, io.BytesIO(b))
        members[name + '.pt'] = {'B': len(b), 'SHA': sha(p), 'original': str(p)}
archive = D / 'weights.tar.xz'
assert not archive.exists()
archive.write_bytes(lzma.compress(buffer.getvalue(), preset=1))
with tarfile.open(fileobj=io.BytesIO(lzma.decompress(archive.read_bytes())), mode='r') as tar:
    for name, info in members.items():
        b = tar.extractfile(name).read()
        assert len(b) == info['B'] and hashlib.sha256(b).hexdigest() == info['SHA']
history = [json.loads(x) for x in (D / 'runs/frame14-distance-residual-r1/history.jsonl').read_text().splitlines()]
jobs = [json.loads(p.read_text()) for p in (D / 'jobs').glob('*/process.json')]
assert all(j['exit'] == 0 and j['child_waited'] and not j['remaining'] and j['current_exact_identity_absent'] for j in jobs)
cost = {'science_samples': sum(j['samples_charged'] for j in jobs),
        'heavy_s': sum(j['wall_seconds'] for j in jobs if j['kind'] == 'heavy'),
        'managed_static_s': sum(j['wall_seconds'] for j in jobs if j['kind'] == 'static'),
        'standalone_pretest_Git_conservative_s': 30, 'other_short_metadata_and_reports_conservative_s': 60,
        'manual_source_edit_and_AST_conservative_CPU_s': 120,
        'management_cap_s': 600, 'heavy_cap_s': 300, 'science_sample_cap': 500000,
        'CPU_number': 2, 'logical_count': 1, 'GPU': 0, 'warm': 0,
        'peak_family_RSS_B': max(j['peak_family_RSS'] for j in jobs),
        '201_teacher_jobwall_s': 83.72390816896223, 'teacher_fee_owned_by': 'quoridor-4lc.201',
        'native_strength_timing_measured': False}
assert cost['science_samples'] == 383287 and cost['heavy_s'] < 300
assert cost['managed_static_s'] + 30 + 60 + 120 < 600
game_sign = {name: sum(g['primary']['z_sign_accuracy'] for g in m['games'].values()
                       if g['primary']['z_sign_rows']) / sum(bool(g['primary']['z_sign_rows']) for g in m['games'].values())
             for name, m in r['models'].items()}
final = {'UTC': datetime.datetime.now(datetime.UTC).isoformat(), 'issue': 'quoridor-4lc.200',
         'status': 'DISTANCE_BASELINE_SUPPORTED_RESIDUAL_LEARNING_NOT_SUPPORTED',
         'candidate_step': 0, 'candidate_is_train_fitted_distance_baseline': True,
         'trained_residual_adopted': False, 'test_result_SHA': sha(D / 'test-evaluation-r1/result.json'),
         'test_freeze_SHA': sha(D / 'test-freeze.json'), 'gameequal_z_sign': game_sign,
         'cost': cost, 'weights_archive': {'path': str(archive), 'B': archive.stat().st_size,
                                         'SHA': sha(archive), 'members': members, 'restored_in_memory': True},
         'full_training_curves_saved': len(history) == 21, 'newtest_openings': 1,
         'old_test_labels_read': False, 'new_condition_selected_after_test': False,
         'teacher_truth_or_strength_claim': False}
(D / 'final-result.json').write_text(json.dumps(final, indent=2) + '\n')
text = REPORT.read_text()
text = text.replace('独立fresh testは201引渡し・mask束縛後に一度評価する（現在未開封）。',
                    '独立fresh testを固定候補・maskで一度評価済み。距離基準の未露出game教師精度改善を支持し、学習済み残差は不採用。')
text = text.replace('## 判断の限界と未完了', '## 独立fresh test一巡')
text = text.replace('新fresh testと最終保存・backup・handoffは未完了。', '科学/source/子停止済み。最終Git復元・保存会計・backup receiptを後続metadataに束縛する。')
text += '\n新test24予定/24完走GOAL/24eligible game、1122行primary/secondary、除外0/eligible0game0。参照は旧train96+全val+開封済旧testのlabel-free署名だけ、state OR history OR実QF1入力でmaskをlabel前に固定。新testlabelsを最終freeze後一回だけ開き、旧labels/旧結果per-row再読0。source/schema v2のNN0修正と原成功科学は分離。\n\n'
text += '| frozen predictor | rootmean rowMSE | rootmean gameMSE | z gameMSE | sign row | sign game | saturation |\n|---|---:|---:|---:|---:|---:|---:|\n'
for name in ['candidate', 'last', 'distance_only', 'constant', 'random_QF1']:
    m = r['models'][name]['primary']
    values = [m['rootmean_mse'], m['rootmean_game_equal_mse'], m['z_game_equal_mse'],
              m['z_sign_accuracy'], game_sign[name], m['saturation_fraction']]
    text += '| ' + name + ' | ' + ' | '.join(f'{x:.9f}' for x in values) + ' |\n'
text += '\npaired game等重み差・percentile95（2000bootstrap/seed20080311、24family群単位）:\n\n'
for target in ['rootmean', 'z']:
    for name, entry in r['paired_intervals'][target].items():
        text += f"- {target} {name}: delta={entry['delta']:.9f}, 95%={entry['percentile95']}\n"
text += '\nrootmeanの候補−定数と候補−randomは負の区間、LAST−距離は正の区間。zのLAST−距離区間は0を跨ぐ。候補/BEST/距離初期のtensorは同一でprediction reuse、実uniqueNN3/3366test samples、距離only/定数は解析計算。距離初期NNと距離only maxabs0。game別/cohort/phase、全raw必要scalarはtest-evaluation-r1/result.jsonとper-row.jsonl.gzへ保存。24gameの条件付き有限精度であり、1122独立標本/一般棋力としない。testを再選定へ戻さず追加学習/forward/test/arena0。\n\n'
text += f"train+test科学383287sample/実heavy{cost['heavy_s']:.6f}s。testjob2.107264s、peak745603072B。201の生成83.723908sは201の別費で、本CPUのNNkernel速度やnative棋力倍率にしない。管理/static/source編集・報告は別ledger、全600s内。\n\n"
text += '''## 次の最大1判別案（未実許可・未起動）

同じ凍結LAST residualの出力振幅だけをλ=1→.1に固定して推論時縮小する、一つの安価な対照を提案する。新学習/LR/幅/target/seed sweepは不要。A=残差に有用な信号があるが振幅・飽和が過大、B=この特徴/履歴/教師対応では残差の未見gameへのalignmentが弱い、を部分的に区別する。λ=.1は今回閉じたtestへ当て直さず、結果前固定した一値として新issueで評価する。

まず既train/固定valのraw residualを一度取得し、距離only/λ1/λ.1の予測を同raw出力から解析導出する（NN5901sample、CPU2単1/hard30s/RAM2GiB）。val gameMSEがdistance初期より1e-4以上改善する場合だけ、別entropy/familyの未使用fresh test24を別配分し、今回のtestを再開しない。全条件/checkpoint/係数/clip/mask/候補をtest前freeze。新testはtrain/val/開封済testのlabel-free OR露出を除外して一度、raw residual NNを再使用して距離・λ1・λ.1のpaired game差/真z/符号/飽和を保存する。λ.1が新testでも距離を改善すれば振幅制約の有用性を支持、val gate不成立なら新生成0、newtest差が不確かなら有用なalignment未確認。いずれも教師noise/表現不足の原因確定ではない。

費用見積は新学習0、CPU trainval+test NN合計約7100sample（test規模は新生成で確定、上界12000）、各CPUjob30s/計60s以内。新teacher24は今回201の83.724sを参考としhard300s+回収30s/VRAM6GiBの別owner配分が必要。GPU生成とCPU評価を非重複にし、自然監督窓/実owner/CPU4/RAM8/保持予約を直前admit。新testが無ければ独立確認は未知のまま終了し、旧test補充/別checkpoint選定へ戻さない。αβ/棋力・量子化・T1全実装は自動開始しない。
'''
REPORT.write_text(text)
print(json.dumps({'status': final['status'], 'weights_archive_B': archive.stat().st_size,
                  'samples': cost['science_samples'], 'heavy_s': cost['heavy_s'], 'forward': 0}))
