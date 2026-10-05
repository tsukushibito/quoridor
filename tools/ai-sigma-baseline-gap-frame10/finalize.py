"""NN0 stopped-data preservation after an explicit research-direction change."""
import json,hashlib,tarfile,datetime,collections,os,time,subprocess,resource
from pathlib import Path
os.sched_setaffinity(0,{0});started=time.monotonic();root=Path(__file__).resolve().parents[2];os.chdir(root)
out=root/'.artifacts/ai-sigma/resume-20261003/BASELINE-GAP';data=root/'research-data/ai-sigma/frame10-baseline-gap'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(name,x):p=data/name;p.write_text(json.dumps(x,indent=2,ensure_ascii=False)+'\n');return p
agg=json.loads((data/'aggregate.json').read_text());direction=json.loads((data/'user-direction-science-stop.json').read_text());games={};restored=[]
for mp in sorted(data.glob('gap149-group*.manifest.json')):
 m=json.loads(mp.read_text());p=Path(m['archive']);assert sha(p)==m['archive_SHA256']
 with tarfile.open(p) as t:
  checked=0
  for x in m['members']:
   name=x.get('member',x.get('path',x.get('name')));content=t.extractfile(name).read();assert len(content)==x['bytes'] if 'bytes' in x else len(content)==x['size'];assert hashlib.sha256(content).hexdigest()==x.get('SHA256',x.get('sha256'));checked+=1
  for n in t.getnames():
   if '/completed-game-' not in n or not n.endswith('.json'):continue
   d=json.loads(t.extractfile(n).read());g=d['game'];assert g['id'] not in games;assert g['status']=='terminal' and g['winner'] in [1,2];games[g['id']]=g
 restored.append({'archive':str(p.relative_to(root)),'SHA256':sha(p),'members_stream_restored':checked})
known=[x for x in agg['games'] if x['category']=='goal'];assert len(games)==len(known)==20
scores=[]
for a in known:
 g=games[a['id']];s=int(g['winner']==a['candidate_color']);assert a['normal_terminal_score']==s and a['new_public_plies']==len(g['actions']);scores.append(s)
assert sum(scores)==3 and agg['operational_mean_interval']==[3/64,47/64] and agg['terminal_quality_all64_interval']==[3/64,47/64]
assert agg['categories']=={'goal':20,'outer_OOM_unknown_start_and_result':4,'user_direction_change_unstarted':40}
assert len({a['id'] for a in agg['games']})==64
verification={'issue':'quoridor-4lc.149','UTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'independent_of_aggregate_score_recompute':True,'not_independent_rules_or_formal_verdict':True,'raw_normal_goals':20,'candidate_wins':3,'candidate_losses':17,'draws':0,'OOM_unknown':4,'direction_unstarted':40,'full64_operational_and_terminal_quality':[3/64,47/64],'archive_stream_restore':restored,'per_color':{str(c):dict(collections.Counter(str(a['normal_terminal_score']) for a in known if a['candidate_color']==c)) for c in [1,2]},'pair_patterns':dict(collections.Counter(a['pattern'] for a in agg['pairs'])),'root_paired_support':sum(a['same_input_NN_supported'] for a in agg['first_roots_sameinput']),'root_missing_OOM_pairs':[1,2],'root_unstarted_pairs':list(range(13,33))}
write('stopped-data-verification.json',verification)
processes=[];identities={};heavy=static=0
for p in sorted((out/'runs').glob('*.process.json')):
 d=json.loads(p.read_text());assert not d['remaining'] and not d['unknown_adopted'];duration=(datetime.datetime.fromisoformat(d['end'])-datetime.datetime.fromisoformat(d['start'])).total_seconds();isheavy='generation' in p.name or 'group' in p.name
 heavy+=duration if isheavy else 0;static+=0 if isheavy else duration
 processes.append({'run':p.name.removesuffix('.process.json'),'start':d['start'],'end':d['end'],'wall_seconds':duration,'exit':d['exit'],'charged_heavy':isheavy,'peak_current_RSS_sample':d['peak_group_plus_runner_RSS'],'peak_allocated_bytes':d['peak_allocated_bytes'],'assigned_CPU':d['assigned_CPU'],'all_observed_TIDs_at_assigned_CPU':d['all_observed_TIDs_at_assigned_CPU'],'affinity_violations':d['affinity_violations']})
 for x in d['tracked']+[{'pid':d['runner_pid'],'start_ticks':d['runner_starttick']}]:identities[(x['pid'],x['start_ticks'])]={'pid':x['pid'],'start_ticks':x['start_ticks']}
for x in direction['current_identities']:identities[(x['pid'],x['start_ticks'])]=x
finish_wall=0
for p in out.glob('*-finish-record.json'):
 d=json.loads(p.read_text());identities[(d['helper_pid'],d['helper_starttick'])]={'pid':d['helper_pid'],'start_ticks':d['helper_starttick']};finish_wall+=d['wall_seconds']
same=[];errors=[]
for x in identities.values():
 try:d=Path('/proc/%s/stat'%x['pid']).read_text().rsplit(')',1)[1].split()
 except FileNotFoundError:continue
 except Exception as e:errors.append({'identity':x,'error':str(e)});continue
 if int(d[19])==x['start_ticks']:same.append(x)
assert not same and not errors
resource_record={'issue':'quoridor-4lc.149','UTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'process_jobs':processes,'heavy_seconds_including_NN0_generation_init_failure_monitor':heavy,'heavy_budget_seconds':7200,'guarded_static_seconds':static,'finish_helpers_seconds':finish_wall,'finalization_helpers_separate':True,'misc_interactive_read_static_cost_unrecorded_not_zero':True,'team_total_cost_unknown':True,'peak_sample_current_RSS_bytes':max(p['peak_current_RSS_sample'] for p in processes),'past_allocated_peak_bytes':max(p['peak_allocated_bytes'] for p in processes),'current_own_retained_allocated_bytes':sum(p.stat().st_blocks*512 for directory in [out,data,root/'tools/ai-sigma-baseline-gap-frame10'] for p in directory.rglob('*') if p.is_file()),'forecast_final_extra_bytes':8*1024*1024,'scope_guard_bytes':224*1024*1024,'scope_reservation_bytes':256*1024*1024,'existing_experiment_entry_bytes':2*1024**3,'parent_extra_reservation':0,'old_unknown_not_reduced':True,'current_identities':list(identities.values()),'current_same_identity':same,'current_read_errors':errors,'boot':Path('/proc/sys/kernel/random/boot_id').read_text().strip(),'current_absence_not_natural_fullperiod_allhost':True,'Node_heap_MB_group01':192,'Node_heap_MB_group02_onward':768,'sampling_interval_ms':40,'instant_peak_fullCPU_faircycle_not_guaranteed':True}
assert resource_record['current_own_retained_allocated_bytes']+resource_record['forecast_final_extra_bytes']<resource_record['scope_guard_bytes'];write('final-cost-ownership.json',resource_record)
# Preserve needed generation/static/control records, without duplicate group full raw or source copies.
paths=[]
for p in out.iterdir():
 if p.is_file() and (p.suffix in ['.json','.jsonl','.md']) and '-current.json' not in p.name and p.name not in ['goal.json','self.json','claim.json']:paths.append(p)
paths+=list((out/'configs').glob('*.json'))
for p in (out/'runs').rglob('*'):
 if not p.is_file():continue
 if 'gap149-group' in p.name or 'gap149-group' in str(p.parent):continue
 if p.name=='payload-mock-result.json' or 'payload-mock' not in str(p):paths.append(p)
paths=sorted(set(paths));archive=data/'stopped-preparation-control.tar.gz';members=[]
with tarfile.open(archive,'w:gz',compresslevel=6) as t:
 for p in paths:
  name=str(p.relative_to(out));t.add(p,arcname=name,recursive=False);members.append({'member':name,'size':p.stat().st_size,'SHA256':sha(p)})
with tarfile.open(archive) as t:
 for m in members:
  b=t.extractfile(m['member']).read();assert len(b)==m['size'] and hashlib.sha256(b).hexdigest()==m['SHA256']
write('stopped-preparation-control.manifest.json',{'issue':'quoridor-4lc.149','archive':str(archive.relative_to(root)),'SHA256':sha(archive),'size':archive.stat().st_size,'members':members,'all_stream_restored':True,'source_copied':False,'group_full_raw_ref':'gap149-group01..06-r1.tar.gz','commands_in_configs_and_process_records':True})
report=root/'docs/reports/ai-sigma-experiment-baseline-gap-frame10.md'
report.write_text(f'''# 枠10 baseline対固定Sigma：ユーザー方向変更による停止

ユーザーの研究方向変更に従いgroup6の安全な終了・回収・保存後に停止した。group7〜16は未開始。途中成績を停止理由に使っていない。忠実Sigma-Web Rust/Wasm基準候補を優先する次課題は別契約であり、本課題では新kernel/build/NNを開始していない。

## 全予定64枠の結果

| 分類 | 枠数 | score扱い |
| --- | ---: | --- |
| 正常goal：候補勝 | 3 | 1 |
| 正常goal：候補敗 | 17 | 0 |
| 正常draw | 0 | .5 |
| group1 Node OOM・実開始/結果欠測 | 4 | [0,1]未知 |
| ユーザー方向変更による中止・未開始 | 40 | [0,1]未知 |

運用主scoreとterminal手品質の**全64識別区間は共に[0.046875, 0.734375]**。正常終局のみの補助平均は3/20=.15（選別された20枠、主分母への置換なし）。候補色1は2勝8敗、色2は1勝9敗。完了10pairは両色候補敗7pair、同盤面side勝者・両AI一勝ずつ3pair。未知22pairを落とさない。

事前固定の独立bounded32pair追加仮定のHoeffding eps={agg['reference_Hoeffding_eps']:.12f}を外側に加えた参考区間は[0, {agg['operational_assumption_only_95_interval'][1]:.12f}]。独立性・被覆は立証しておらず、.5を跨ぐ。固定集合全体の棋力差は未確定。20正常局の偏りを一般棋力・NI・Sigma同等・119敗因・係数因果へ換算しない。

## 入力・政策・時計

32prefix/64slotをAI前に固定した。4/5/12/13ply各8slot、seed正本SHA a82f2d01875180aa6a4a53be6e62d1ae11b9ab01ef2b3d37e5a1b40a7ede5c04、全8attempt規則。旧119のkey＋正規化history_counts＋side完全signatureを全8一律除外。32/32初attempt合法非終端、旧一致0、新重複0。原preregister・入力SHA71505c5d56aa775938d00aec4e1fc10f10bac6bed5921411a8649936d95445b2・層/色/順を保持し、補充/再試行/置換0。

candidate immutable Q0/C1.5と原fixedSigma C1/FPU.2/temp0、同ONNX/ORT1.21 CPU各1thread/探索seed1979、CPU[2]単logical。T500/cutoff402/adopt411/bounded2sample。2専用Worker/session/SAB/control/generation、main RuleA審判・時計、Node外起動監視と局終了後保存のみ。相手t0を旧ACKの前提にせず自次手前だけ自旧zero、確定後旧返却discard。製品政策変更0。

完了pair3〜12の10初根対応は保存key/history/prefix/model/feature bits一致、137保存数値完全一致（新golden無し）。pair1/2はOOM欠測、pair13〜32は未開始。深部一般一致や独立ルール証明ではない。

## 分母と費用

| 完了20局の保存分母 | candidate | fixedSigma |
| --- | ---: | ---: |
| 手要求 | 600 | 607 |
| 手API開始/返却 | 5397/5397 | 6364/6364 |
| 採用CP completed backup合計 | 5382 | 7525 |
| 採用CP completed NN合計 | 4897 | 5872 |
| 旧返却discard | 323 | 321 |

startup36/session12は6job分として手分母と別。group1手費用/CP/通常NNzero receiptは欠測、0にしない。採用backup−NNの導出値は候補485/参照1653だが、terminal-noNNの直接分母・cap/pseudo leafの内訳は未記録。API awaitはkernelCPUではなく、異状態のNN総量比も同仕事量/同CPUの証明ではない。保存時計/旧ACK/自己待ち/残wallはaggregateに保持。clock中間drift/exact atomic store/純NNCPUは未測定。

生成・初期化・失敗・監視込み管理heavyは{heavy:.6f}秒/7200秒、各job600秒内。guarded static {static:.6f}秒と保存helper {finish_wall:.6f}秒を別記し、未記録の軽い読取費/全team費は未知。最大観測currentRSS {resource_record['peak_sample_current_RSS_bytes']}bytes、40ms標本は瞬間peakや全期間公平cycleを保証しない。Node heap192MiBから768MiBへ局終了後保存を修復したがRAM6GiB/guard5.5GiB内、探索/入力/時計規則変更0。

## 失敗・停止・保存

group1版44d37c7はNode OOM/exit-6。4予定枠の実開始/結果と通常Modeldrop/NNzero/mainreceiptは欠測、guardianのowned物理回収とは分離した。科学source c29c662a0ae53e0fce782a86abfbe1686eccb7d7以後は1局ごと終了時の全rawを保存し、4局最終収集はcompact化。保存payload NN0mockと旧失敗logを保持、成功game再実行0。

最後group06開始2026-10-03T01:06:27.631043UTC、終了01:08:34.928350UTC、exit0、保存Git8448e20316d96dffe623ab6a6e4cedd21fdd5f2d。controllerは01:08:43.898951に全自子wait後return、Beads paused-by-userによりgroup07前拒否、signal/interrupt0。各group正常Model2/search/main timer-message/monitorcallback/innercontrolledzeroとouterownedwait remaining/unknown空を停止正本に分けた。現在sameidentity不在は自然終了/全host/全期間保証ではない。

科学source/結果書込停止速報を本文より前に配送した。最小pack/Git/backupの記録helperは別。6archiveの全member SHA-size復元と元rawからscore再算を確認した（自己検査、独立科学受入れはcoordinator）。旧結果/期限を書換えていない。残る149 heavy開始は禁止、次案はユーザー指定の忠実Sigma-Web Rust/Wasm基準候補の別契約のみ。現独自政策の採用/係数変更・新実行を自動開始しない。

再現参照: `research-data/ai-sigma/frame10-baseline-gap/preregister.json`、`inputs.json`、`aggregate.json`、`stopped-data-verification.json`、`final-cost-ownership.json`、`user-direction-science-stop.json`。各group manifestに実source/servedhash/command/config/memberを保存。最終handoffのGit/stop/archive/backupにbindする。旧119/117のWDL混合0。
''')
write('finalization-helper.json',{'pid':os.getpid(),'starttick':int(Path('/proc/self/stat').read_text().rsplit(')',1)[1].split()[19]),'wall_seconds':time.monotonic()-started,'current_RSS_bytes':int(Path('/proc/self/stat').read_text().rsplit(')',1)[1].split()[21])*4096,'past_peak_RSS_bytes':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,'NN':0,'Chrome':0,'source_hashes':{str(p.relative_to(root)):sha(p) for p in sorted((root/'tools/ai-sigma-baseline-gap-frame10').glob('*')) if p.is_file()},'source_finalization_write_done':True,'archive_SHA256':sha(archive),'member_count':len(members)})
assert time.monotonic()-started<60
print(json.dumps({'heavy_seconds':heavy,'normal_goals':20,'bounds':[3/64,47/64],'control_archive_SHA':sha(archive),'control_members':len(members),'report':str(report)}))
