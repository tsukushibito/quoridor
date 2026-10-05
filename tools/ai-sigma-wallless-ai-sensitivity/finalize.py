from pathlib import Path
import json,hashlib,datetime,tarfile,io
R=Path(__file__).resolve().parents[2];T=R/'tools/ai-sigma-wallless-ai-sensitivity';D=R/'research-data/ai-sigma/144-wallless-ai-sensitivity';O=R/'.artifacts/ai-sigma/resume-20261002/WALLLESS-AI-SENSITIVITY';run=O/'runs/wallless144-ai-r2'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
x=json.loads((run/'browser-result.json').read_text());assert x['started_requests']==6 and x['completed_requests']==6 and not x['errors']
rows=[]
for a in x['rows']:
 assert not a.get('primary') and not a.get('main_gate_error') and a['classification']=='certifiedwin'
 assert a['rootN']==a['spec']['K'] and a['edge_sum']==a['spec']['K']-1 and a['control']['NN_started']==a['NN_calls']==a['control']['NN_returned']
 n=a['numeric'][0];assert len(n['features_bits'])==648 and len(n['policy_logits'])==136 and -1<=n['value']<=1
 assert a['SAB_completed']['action']==a['cp']['action'] and a['SAB_completed']['visits']==a['rootN']
 terminal=sum(z['visits'] for z in a['cp']['tree'] if z['terminal'] is not None) if a['engine']=='candidate' else None
 if terminal is not None:assert terminal==a['terminal_noNN_backups'] and not a['cp']['cap']
 rows.append({'request':a['id'],'spec':a['spec'],'Action':a['cp']['action'],'action':a['action_binding'],'certified_interval':a['certified_interval'],'winning_label_set':a['winning_set'],'classification':a['classification'],'payoff':a['score'],'K':a['completed_backups'],'rootN':a['rootN'],'raw_loop_or_sim':a['cp']['simulations'],'root_edge_sum':a['edge_sum'],'NN_started':a['control']['NN_started'],'NN_completed':a['control']['NN_returned'],'completed_without_NN':a['terminal_noNN_backups'],'terminal_count_source':'snapshot terminal visits' if terminal is not None else 'completed-minus-NN with unchanged uncapped reference branch; per-backup terminal state not saved','snapshot_terminal_visits':terminal,'max_depth':a['cp'].get('max_depth'),'cap':a['cp'].get('cap'),'numeric_gate':a['numeric_gate'],'SAB_completed':a['SAB_completed'],'wrapper_ms':a['wrapper_end_ms']-a['wrapper_start_ms'],'first_CP_ms':a['first_CP_ms'],'ACK_ms':a['ACK_ms'],'API_await_ms':[z['API_end_ms']-z['API_start_ms'] for z in a['spans']],'discard_explicit_counter':None})
assert all(c['features_exact'] and c['NN']['exact'] and c['candidate_root1_NN']['exact'] for c in x['comparisons'])
served=json.loads((run/'actual-served-source.json').read_text());assert served['/b.wasm']['SHA256']=='1f54d0b8f0c6d3d7d51935886ed506e44376a2052506be62ca7a726c85a78a01';assert served['/model.onnx']['SHA256']=='d790dac68389f7602ff8a887a2385417d3c925fe22da7164c86e9226f943908d'
# Reproduce actually served adapter script hashes after stop without NN/Chrome.
result={'issue':'quoridor-4lc.144','scientific_source_Git':'1d96dd5','all_attempts':{'planned':6,'started':6,'completed':6,'unstarted':0,'certifiedwin':6,'certifiedloss':0,'unscored':0,'fault':0,'unfinished':0},'prelaunch_failures':[{'run':'wallless144-ai-r1','Chrome_spawn':0,'reason':'static command parsed as config'}],'rows':rows,'comparisons':x['comparisons'],'completed_total':sum(z['K'] for z in rows),'hand_NN':sum(z['NN_completed'] for z in rows),'completed_without_NN':sum(z['completed_without_NN'] for z in rows),'startup_NN':6,'sessions':2,'games':0,'exit':'all conditions certifiedwin bothcase: end same-format scale','policy_maintained':'candidate immutableQ0/C1.5 and originalfixedSigma','new_fixedgolden':False,'no_general_strength_smallfix_sensitivity_or_depth_sufficiency_claim':True}
(D/'finite-results.json').write_text(json.dumps(result,indent=2)+'\n')
process=[json.loads(p.read_text()) for p in (O/'runs').glob('*.process.json')];resource={'heavy_seconds':sum((datetime.datetime.fromisoformat(p['end'])-datetime.datetime.fromisoformat(p['start'])).total_seconds() for p in process if p['phase']=='ai'),'managed_static_seconds':sum((datetime.datetime.fromisoformat(p['end'])-datetime.datetime.fromisoformat(p['start'])).total_seconds() for p in process if p['phase']=='protocol'),'heavy_guard':5905580032,'heavy_peak_current_RSS':max(p['peak_group_plus_runner_RSS'] for p in process if p['phase']=='ai'),'heavy_CPU':[2],'ORT_threads':1,'static_CPU':[0],'source_Git':'1d96dd5','start':next(p['start'] for p in process if p['phase']=='ai'),'end':next(p['end'] for p in process if p['phase']=='ai'),'actual_served_source':served,'unmanaged_short_management_full_PID_RSS_cost_missing':True,'existing_entry_2GiB_old_unknown_conservative_unchanged':True,'new_parent_reservation':0,'API_await_not_kernel_CPU':True,'clock_start':json.loads((run/'startup.json').read_text())['worker_clocks'],'clock_end':json.loads((run/'clock-end.json').read_text()),'midrun_drift_exactAtomicstore_missing':True,'request_command':next(p['cmd'] for p in process if p['phase']=='ai')}
(D/'resources-and-bindings.json').write_text(json.dumps(resource,indent=2)+'\n')
proposal={'count':1,'proposal':'End this wallless scale; if coordinator continues, first design a different midgame move-quality measure in NN0, rather than generate more easy wallless cases.','condition':'current normal and root1 all choose highest-prior certifiedwin','next_judgement':'whether the new measure can identify useful decision differences before spending NN/game budget','falsifier':'measure accepts root-prior-only choices as sufficient or lacks meaningful finite discrimination','proposed_cost':'one static CPU0/RAM1 command <=60s, NN/game/input generation0; not an execution allocation','automatic_start':False,'model_value_cause_inferred':False}
(D/'next-proposal.json').write_text(json.dumps(proposal,indent=2)+'\n')
report=R/'docs/reports/ai-sigma-experiment-wallless-ai-sensitivity.md'
s='''# 144: 壁なし有限ラベルのAI感度診断

固定したP1-race/P2-corridorの両方で、候補通常K32・候補root1K1・固定Sigma通常K32はすべて認証winを選んだ。登録した全win出口に従い当尺度の同形式反復を終了し、candidate immutable Q0/C1.5と固定Sigmaを維持する。ラベルが合法手を区別できても、この2入力ではAI条件を区別しなかった。一般棋力、全depth十分、小改修への感度、正式NI/Sigma同等は未認定。

受領2026-10-02 19:46:03.934522 UTC。契約/選定b564b3f、初期登録51eb3e6、科学停止版1d96dd5。旧142の登録8466495/科学3866532/data9143e12/handoff63d46ddを区別し、必要generation2memberを実hashでbindした。143科学885eb8eの独自walk/別solverの全8区間・同input/Actionとheavy停止SHA e04c01113ca4556f32d35acd0fd47caf88e4708a50b12bbd882fcdca323aa5ebを参照した。元env candidate-r2をGitIDにしていない。143最終本文を追加gateにしなかった。

| case | 条件 | K/rootN | edge和 | NN | NNなし完成 | Rust Action / label | 認証区間 |
|---|---|---:|---:|---:|---:|---|---|
'''
for z in rows:s+=f"| {z['spec']['fixture_id']} | {z['spec']['engine']} {z['spec']['condition']} | {z['K']} | {z['root_edge_sum']} | {z['NN_completed']} | {z['completed_without_NN']} | {z['Action']} / {z['action']['label_index']} | [1,1] |\n"
s+='''
P1の実手は(4,6)→(4,7)、P2は(4,2)→(4,1)。小label index0/1とRust67/13は実legal action objectを介して対応した。P2ではlabel1がcanonical NN index0に回転する。root1は根展開1/edge0/NN1、通常候補は32sim、参照は根展開loop外+31loopでrootN32。完成130、手NN26、NNなし完成104、startup6/session2は別。候補53のterminal回数はsnapshot terminal node visits和を確認した。参照51は未変更uncapped経路とcompleted−NNからの分母であり、各backupのterminal stateは保存していない。KをNN/CPU/wallへ換算しない。

通常/root1とも最大priorの同手を選んだ。P1候補prior約.849862、P2約.885217。通常の訪問分布は異なり、P1参照は別手にも2訪問あるが最終手/有限payoffは同じ。したがってこの測定から係数修正・model/value原因を選べず、同形式の追加入力/反復を自動開始しない。次案は1つだけ、別の中盤局所手品質尺度をまずNN0で設計し、改善差を識別できる条件と不足を整理すること。静的≤60秒/CPU0/RAM1、NN/game/入力生成0を将来の見積とし、今回の実行許可にしない。

保存prefix32/33・history/key/side/pawns/壁0・648feature bits・全root合法集合をmain RuleAで再現。全6のfeatures exact、NN137 shape/finite/value strict[-1,1]、Action別prior/order/P2対応をbrowser内で確認した。同入力の候補/参照/root1の根NNはbit一致で、登録abs1e-4+rtol1e-4も満たす。新入力golden参照はない。共有RuleA、生成された壁なし2状態、有限depth6/minmaxラベルでありIID/holdout/WDL/game-theoretic oracleではない。深部一般数値一致は調べていない。

実装は元132のread-only count入口と自域薄いmain/worker adapter。元immutableWasm/固定Sigma coreを実serve hashでbindし、共有source/build/model変更0。2Worker/model session/control/generationを分離し、fresh tree/history要求を両旧zero後に直列開始。完成Actionは専用SABへ公開してmain bounded読取で照合した。count結果/zero通知後に採点する孤立診断で、通常500msの採用/相手t0経路は変更していない。API awaitはkernelCPUではなく、参照深さ・各旧discardイベント等の未保存欄は欠測とした。

全科学attempt6成功、unfinished/fault/unscored/未実施0。接続/warm/追加科学要求0。prelaunch設定key違いとadmission r1の静的command誤読はNN/Chrome0として保存し、admission例外後spawn0を維持した。修正は自域helperだけで、成功科学検索を再試行していない。`summary.Git`の原placeholderは不正確なのでGit版として採用せず、before/after sourcehashと1d96dd5の実source一致を正本にした。

'''
s+=f"全Chrome/init/startup/monitor heavy {resource['heavy_seconds']:.6f}秒（上限120、job90）、CPU[2]/ORT各1thread、observed currentRSS peak {resource['heavy_peak_current_RSS']/1024**2:.3f}MiB（guard5632）。managed static {resource['managed_static_seconds']:.6f}秒。短い編集/管理commandの全PID/RSS/瞬間peak/費用は欠測。API/whole wrapperやmonitor負荷から性能改善・正式公平cycleは主張しない。開始/終了Workerclockを保存、途中drift/exactAtomicstoreは未測定。\n\n"
s+='''科学source/NN/Model2/search/main timers-message/monitorcallbacksは本文前に停止・速報した。innercontrolled forced/waitとoutersole-root ownedwait/remainingunknown空を区別し、46 exact identity現在不在を確認した。現在不在を自然終了/全期間/全host保証にしない。最終保存helper停止は後述のhandoff正本へbindする。processing20:30/newheavy20:25/submission20:45、親枠9の期限と資源を維持した。

再現入口・設定・全要求・失敗・actual served hash・時計・資源・停止は `research-data/ai-sigma/144-wallless-ai-sensitivity/` と同課題archive manifestを参照。共有model/ORT/Wasmは参照しコピーしない。archiveを停止rawから生成して全member SHA/bytesを復元確認し、研究Git/Beads backup後coordinatorへ引渡す。goal/他者close、actual_go、政策採用0。
'''
report.write_text(s)
# minimal necessary raw: all typedattempts, config/source, process/ownership/clock/stop; exclude regenerable Chrome temp/cache
files=sorted(p for p in (O/'runs').rglob('*') if p.is_file() and not any(a in ['t','xdg-cache','xdg-config','__pycache__'] for a in p.relative_to(O/'runs').parts))
manifest=[]
with tarfile.open(D/'runs.tar.gz','w:gz') as tar:
 for p in files:
  name=str(p.relative_to(O/'runs'));tar.add(p,arcname=name);manifest.append({'member':name,'bytes':p.stat().st_size,'SHA256':sha(p)})
with tarfile.open(D/'runs.tar.gz') as tar:
 for z in manifest:
  raw=tar.extractfile(z['member']).read();assert len(raw)==z['bytes'] and hashlib.sha256(raw).hexdigest()==z['SHA256']
archive={'archive':'runs.tar.gz','SHA256':sha(D/'runs.tar.gz'),'members':manifest,'restore_all_members':True,'source_version':'1d96dd5','expand_to':str(O/'runs'),'shared_models_dependencies_copied':False}
(D/'archive-manifest.json').write_text(json.dumps(archive,indent=2)+'\n')
print(json.dumps({'results':6,'heavy':resource['heavy_seconds'],'archive':archive['SHA256'],'members':len(manifest),'report':str(report)}))
