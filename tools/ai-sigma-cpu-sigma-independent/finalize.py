from pathlib import Path
import json,hashlib,datetime,os,tarfile,shutil,time
R=Path(__file__).resolve().parents[2];T=R/'tools/ai-sigma-cpu-sigma-independent';O=R/'.artifacts/ai-sigma/resume-20261002/CPU-SIGMA-INDEPENDENT';D=R/'research-data/ai-sigma/118-cpu-sigma-independent';D.mkdir(parents=True,exist_ok=True)
def h(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def current(pid,tick):
 try:return int(Path(f'/proc/{pid}/stat').read_text().rsplit(')',1)[1].split()[19])==int(tick)
 except FileNotFoundError:return False
processes=[];ids={};duration=0;peak=0;storagepeak=0
for p in sorted((O/'runs').glob('p118-*.process.json')):
 j=json.loads(p.read_text());assert j['remaining']==[] and j['unknown_adopted']==[]
 duration+=(datetime.datetime.fromisoformat(j['end'])-datetime.datetime.fromisoformat(j['start'])).total_seconds() if j['assigned_CPU']==2 else 0;peak=max(peak,j['peak_group_plus_runner_RSS']);storagepeak=max(storagepeak,j['peak_allocated_bytes'])
 for x in j['tracked']:ids[(x['pid'],x['start_ticks'])]=x
 ids[(j['runner_pid'],j['runner_starttick'])]={'pid':j['runner_pid'],'start_ticks':j['runner_starttick']}
 processes.append({k:j[k] for k in ['name','start','end','exit','stop_reason','peak_group_plus_runner_RSS','peak_allocated_bytes','kernel_identity_count','ledger_registered_count','all_observed_TIDs_at_assigned_CPU']})
live=[{'pid':pid,'starttick':tick} for pid,tick in ids if current(pid,tick)];assert not live and duration<360 and storagepeak<29360128
before=json.loads((O/'input-before.json').read_text());archive_after={p:h(R/p) for p in before['checks'] if ':' not in p};assert all(before['checks'][p]==v for p,v in archive_after.items())
owner=json.loads((R/'research-data/ai-sigma/117-cpu-sigma-comparison/runtime-source-stopped-before-report.json').read_text());ownerlive=[x for x in owner['identities'] if current(x['pid'],x.get('starttick',x.get('start_ticks')))];assert not ownerlive
source={str(p.relative_to(R)):h(p) for p in T.iterdir() if p.is_file()};allocated=sum(p.stat().st_blocks*512 for root in [T,O,D] for p in root.rglob('*') if p.is_file());assert allocated<29360128
# Exact r2 checker before the later supplemental functions.
b=(O/'checker-r3.js').read_text();(O/'checker-r2.js').write_text(b[:b.index('async function seed118')]);expected=json.loads((O/'runs/p118-saved-r2.inputs.json').read_text())['source'];assert h(O/'checker-r2.js')==expected[str(T/'checker.js')]
stop={'issue':'quoridor-4lc.118','UTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'monotonic':time.monotonic(),'boot':Path('/proc/sys/kernel/random/boot_id').read_text().strip(),'self_browser_runs':processes,'browser_wall_total_s':duration,'source_after':source,'input_archive_preregister_stop_after':archive_after,'self_identity_count':len(ids),'self_same_identity_current':live,'owner_identity_count':len(owner['identities']),'owner_same_identity_current':ownerlive,'remaining_unknown':0,'observed_peak_group_plus_runner_RSS_B':peak,'observed_peak_allocated_B':storagepeak,'current_scope_allocated_B':allocated,'guardStorage_B':29360128,'combined_artifact_headroom_reference':'headroom-heavy.json','NN_model_load_games_build_download':0,'Modeldrop_not_applicable_to_self_no_sessions_loaded':True,'main_timers_and_workers_not_started_by_checker':True,'owned_monitor_callback_wait_saved_per_run':True,'currentabsence_not_natural_all_period':True,'static_setup_read_commands_CPU0_but_PID_RSS_instantpeak_not_fully_monitored':True,'formal_go':False}
(O/'source-runtime-stop-before-report.json').write_text(json.dumps(stop,indent=2)+'\n')
rep='''# SIGMA-CPU-SIGMA-INDEPENDENT / quoridor-4lc.118 / 契約1・枠8

**12保存棋譜の合法goal終局・W6D0L6、644期限内公開と専用2Workerの時計/世代境界を有限支持。正式公平性/NI/Sigma同等/actual_goは認定しない。** 受領11:20:58UTC、全文/親枠8/common/critic/規約・ready/show goal/self/pauseなし本人担当確認後118のみclaimし開始報告accepted。処理11:55:58/newrun11:50:58/提出12:05:58。新NN/model-load/対局/holdout/build/取得0。

6archiveのSHAと必要memberを照合し、独自checkerを実Chromium mainで実行した。Nodeは起動・所有監視/回収・終了後JSON保存のみ。原117集計関数は呼ばず、RuleAの共有実装を使う独立性限界を保持する。prefix/history/key/手番/候補色1→2/seed/公開Action/選定SAB完成sequence/不変bodyを全手で照合し、全12局goal・未完了/late/初回CP無し0。新手数はpair別134/114/74/134/118/70、prefix既ply0/3/7とtotal plyを分離。6pairすべてXi=.5だが3局面×2seedはIID母集団でなく、644手も644独立WDLではない。旧成績へ統合しない。

[ブラウザreplay・時計結果](../../research-data/ai-sigma/118-cpu-sigma-independent/independent-saved.json)で対局手NN7020/startup36、接続保存別の2公開/手NN18/startup6を確認し、全手7038/startup42/総7080とした。旧接続r1 PREFIX_ILLEGAL・公開0/NN0を成功へ置換しない。相手t0<旧ACK386、旧返却discard258、旧API spanと相手入力の可能な重なり252、自己旧ACK後t0違反0。Worker停止区間は候補upper<=D322、参照upper<=D320/lower>D2。ACKwall>500は参照2、max候補471.935/参照517.870ms。内部API開始の402後/公開後は保存開始clock区間で確実/可能とも0、全7020イベントの有限範囲。途中driftとkernel命令時刻は未測定。

初回完成publication中央値候補81.474/参照49.272ms、初回API await31.867/34.865msをbrowserで再算した。異なる局面分布で、root/input/schedulingを分離した純NN比や棋力原因ではない。採用後のAction不変・棄却と残CPU競合は別。自待ち後のt0という現在仕様を維持し、その外の費用/実効cycle等値を正式同資源として保証しない。

[cache時刻の具体例](../../research-data/ai-sigma/118-cpu-sigma-independent/cache-clock-independent.json): pair5参照request3/sequence9はcache検証398.805ms、publication終端marker406.505–406.715ms、timer428.485→最終stamp428.625ms。検証/コピー完了は402前で、markerをcache採用時刻へ置換しない。exact Atomic storeは保存なし。この手は合法期限内だが「全SAB書込402前」の保証はしない。必要なら後続でAtomic publish近傍の軽い時刻を採る案であり、原採用方式/結果は変更0。

結果前のsample規則は各pair最初の両engine計12root。648bits×12/137NN×12、shape/finite/strict[-1,1]/engine固有順/Action-P2/softmax、候補edge=sim−1と参照edge=sim/root=sim+1を確認。固定参照8rootと動的自己整合4rootを分け、最大NN差3.576279e−6/prior差1.620061e−6。候補sampleはP1、参照sampleはP2であり、候補P2の新数値gate/全644root/全深部の一般一致は未確認。rootNN対rootQはsource規約を区別し、rootQ直接raw値を捏造しない。

seed1979/2098をmain→producer→runOwned/ABI/owned/cacheへ渡す同停止sourceを確認し、browser NN0 stubで両seed正常cacheとforeign seed拒否を独立実行した。固定Sigma first tie/探索kernelの意味変更なし。pair1 Git9eb3510、pair2〜6 db3bdc0、postrun集計8883864を分ける。9eb→db3の差はpostrun summarize.py追加のみ、実runtimeの5script bindingは全pairと一致。handoff ba5515c4/data ee3c3d10のblob/hashを明示bindした。同時共有fault優先/参照NN invalid/候補NN loss/共通identity unfinishedも少数browser mockで確認し、mockを実NN障害にしない。

117保存Modeldrop両zero/main timer-message0/monitor callbacks/inner controlled remaining0/outer owned waitを必要48memberから確認、原1231identity現在不在。現在不在とforced回収を自然終了/全期間保証へ格上げしない。pair4事前heavy admission helper falsepositive・起動列継続/未保存gate、原prefix/集計helper失敗は保持し、runtime guard観測から起動前gate成立を補完しない。

自己browser NN0は7run、r1空配列を数値0と誤比較、r6接続startupが別fileにある取込不足の2検査器失敗を保存・修正した。元棋力/NN negativeではない。残5browser run exit0、加えて静的pack r8のcwd誤認とr9の生きた自己monitorをarchiveへ含めた復元不一致を保存修正（最終pack自身は除外し終了後processを別保存）、全run外側remainingunknown0、Chrome/monitor子終了を本文前[停止証拠](../../research-data/ai-sigma/118-cpu-sigma-independent/source-runtime-stop-before-report.json)へ保存。Chrome全RSS/currentguard5.5GiB/RAM6・全観測TID CPU[2]、NN0を低RAMに分類しない。監視wall/観測RSS/量は停止JSONに記載し、短静的command/PID/RSS/瞬間peak・終了子CPU・全ホスト資源保証の欠測を保持。既critic予約内、追加0。

必要Git/小archiveと全member復元を保存し、Beads notes/backup/report後write停止・idle。有限受入れ担当coordinator、goal/他者close0。共有CPU競合・未知training来歴/native・正式NI/Sigma未達は残る。
'''
(R/'docs/reports/ai-sigma-critic-cpu-sigma-frame8.md').write_text(rep)
files={'independent-saved.json':O/'runs/p118-saved-r2/independent-saved.json','aggregate-independent.json':O/'runs/p118-supplement-r3/aggregate-independent.json','seed-independent.json':O/'runs/p118-supplement-r3/seed-independent.json','cache-clock-independent.json':O/'runs/p118-marker-r5/cache-clock-independent.json','connect-account-independent.json':O/'runs/p118-connect-r7/connect-account-independent.json','source-runtime-stop-before-report.json':O/'source-runtime-stop-before-report.json','owner-stop-compact.json':O/'owner-stop-compact.json','input-before.json':O/'input-before.json','final-input-binding.json':O/'final-input-binding.json','selection-preregister.json':O/'selection-preregister.json','debug-history.json':O/'debug-history.json'}
for n,p in files.items():shutil.copyfile(p,D/n)
archive=D/'evidence.tar.gz';members=[]
with tarfile.open(archive,'w:gz',compresslevel=4) as tf:
 for p in sorted(O.rglob('*')):
  if p.name.startswith(os.environ.get('SIGMA_DUMMY_RUN_ID','NO_ACTIVE_JOB')):continue
  if not p.is_file() or '/t/' in str(p) or '/xdg-' in str(p) or p.name.endswith('.index') or p.name.endswith('.lock'):continue
  tf.add(p,arcname=str(p.relative_to(O)),recursive=False)
with tarfile.open(archive) as tf:
 for x in tf.getmembers():
  b=tf.extractfile(x).read();assert hashlib.sha256(b).hexdigest()==h(O/x.name);members.append({'path':x.name,'bytes':len(b),'SHA256':hashlib.sha256(b).hexdigest()})
(D/'archive-manifest.json').write_text(json.dumps({'SHA256':h(archive),'bytes':archive.stat().st_size,'members':members,'restore_stream_checked':True,'excluded_live_closure_job':os.environ.get('SIGMA_DUMMY_RUN_ID')},indent=2)+'\n')
manifest={str(p.relative_to(R)):h(p) for p in D.iterdir() if p.is_file()};manifest.update(source);manifest['docs/reports/ai-sigma-critic-cpu-sigma-frame8.md']=h(R/'docs/reports/ai-sigma-critic-cpu-sigma-frame8.md');(D/'manifest.json').write_text(json.dumps({'UTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'SHA256':manifest,'actual_go':False},indent=2)+'\n')
print(json.dumps({'stopSHA':h(O/'source-runtime-stop-before-report.json'),'self_identity_count':len(ids),'current0':True,'browser_seconds':duration,'RSSpeak':peak,'observed_storagepeak':storagepeak,'archive_bytes':archive.stat().st_size,'archive_members':len(members),'NN_games':0}))
