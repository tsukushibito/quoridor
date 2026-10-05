# SIGMA-ORT-ENTRY-CRITIC / quoridor-4lc.43 / 試行1・契約1

担当critic 01a0f31d-8227-7e03-a7e6-915b4918c11b、統括01a0f31b-3409-75f2-a30e-453a50484f94へ報告。[継続枠](ai-sigma-continuation-20261001.md)全文継承、SHA859bb777836cc0683e1ad7d1763a71fda60c75d2d6391290cef28771589a81a2。Sigma同等未達、旧32局m8 native.5625/browser.1875・正式非劣性未立証・過去逸脱を保持。ユーザー詳細委任下の独立検証依頼であり旧no-goの自動解除ではない。

問い: ORT候補の最終entry/取引/責任/時計/停止復旧が新比較の準備に足るか。fixed .39 manifest SHA83dcd87000818628099d7daec1c5730058a82439baa46cf894d6c235f1f2d04a、report SHAe3d3fb51d242444ebde79cbb4aa99746fcaec23f25ae7083a5ebf798a58ecf7a、source-final-hashes SHA73929ae447772c664a1347737a1ccc6791e5e6eb281361bee2cd9cec5e66a980。統括38checks現hash一致、actual_go=false/independent_acceptance=false/source停止を確認。writer停止と190identity不在は独立に確認する。root参考は continuation-20261001/ENTRY-COORD-HANDOFF/initial-fixed-input.json。

作業場所ai-sigma/codex/ai-sigma。原tools/ai-sigma-ort-entry-continuation/とrun SIGMA-ORT-ENTRY-CONTINUEをread-only固定。書込は自己 .artifacts/ai-sigma/continuation-20261001/CRITIC-ORT-ENTRY/ と docs/reports/ai-sigma-critic-entry-continuation.md のみ。必要な自己copyは原同bytesから作り、出力/input/temp/path/deadline/guardだけ最小patchを差分/hashで保存し、semantic変更で検証を通さない。独立checker/mockと最終mainへの少数golden実呼出しを作る。原source/registry/role/scheduler/製品/lock/旧入力編集0、compile/取得/依存同期/新対局/holdout送信/学習/GPU/追加委譲0。

優先gate: 最終source/manifest/38checks/旧入力/停止を先固定。最終mainの正診断token→実golden、既run拒否、missing/old/foreign token/hash/偽受入れ拒否を静的とruntimeで区別する。actual_go=falseと未事前登録を診断tokenで迂回して実対局開始できないことをmock入口で確認。20採番/seed/同prefix先後/retrypair1-global2は独立mockで照合、人工scoreを実勝敗にしない。

責任分類/取引/時計を独立注入で確認: candidate MODEL_HASH/NNerror/nonzero fallbackは候補loss、固定referenceだけinvalid、identity/referee共通IPCはinvalid、deadline/crash/無応答は当該engine loss。producerのID/gen/prefix/engine/seed/limitsとpending要求をbindし、foreign合法Actionを受理しない。acceptedはboolean、拒否公開Action=null、cpは完了resume/backup後所有copy、finite/value厳密[-1,1]/prior/mask/終端NN0。正常guardのcp保全とhardfault/cancel/stale/deadlineのwhole discardを区別。post-validation/encoding配送stamp、T後採用0と期限watchdog（cleanup永続待ちでもpublic discard）、旧T10時のNN開始回数欠測を保持する。

少数実runtimeは最終mainと同じbackendの固定goldenのみ。固定3goldenから必要最小数を選んで結果前に自己条件/順/サンプル/T500g91を保存。候補/固定参照の通常→T10拒否→旧bounded stop/wait/PID-starttick不在→fresh load/warm/reclock→両backend合法結果を確認する。既終了signalCode、TERM/KILL/idempotent、zombie含む不在とkill直前identity検査、自己adopted子のみwaitを検査する。各session起動/時計/raw/stderrは別出力、上書き0。自然完了/強制停止/未完了を分け、全session強制停止の旧事実を隠さない。pauseはmock、実対局中pauseは未実施として残す。同期NN中断/tail安全性/一般rawview/entropy/全thread瞬間保証を有限成功で認定しない。

原32＋補足5＋最終5は版別に算術し、42を速度/標本へ合算しない。元822NN/3888featuresと合法prior固定mixedgate(abs1e-4+rtol1e-4、shape/finite/厳密value先検査)を独立再計算、実goldenの採用手・数値・cpを必要最小限再照合する。old .26/.30/39latency検証前stamp、GUARD拒否、C変更枝は救済/混同0。通常/native/source来歴全連鎖、ORTheap/allocator、真合法200/no-legal、training overlap、配布完全性は未確認を維持。

資源: runtime CPU2単logical/NNthreads1、一系列直列、静的CPU0可。RAM3GiB guard2.5GiB、new128MiB guard112MiB（現未配分3,878,254,125Bから予約し残3,744,036,397B、他ownerの未確定増分込み条件付き値）。全CPU4/RAM8/LLM3/累積12GiBを維持。steward .42 CPU0 metadata/schedulerのみで並行、正式無負荷性能とは呼ばない。専用TMP/TMPDIR/TEMP/XDG・PID/starttick/affinity/RSS/storage/command/hash/exitを監視。Go通信へRLIMIT_AS伝播0。各NNjob120秒以下、自己timeout時は自己groupのみ回収、他者kill0。

受領35分以内または10:45UTCの早い方で全runtime/集計処理停止、新jobはその5分前停止、提出45分以内または10:55UTCの早い方。停止証拠/PID0を文書前保存、長文報告に時間を使わず詳細JSONへ。失敗原因の自己helper修正は1回と元log保持、semantic修正が必要なら差し戻しno-goを返しwriterへ勝手に修正しない。原hash前後確認、backup/report、自.43のみclaim/受入れ待ち。.39/goal/他者close0。入口の有限受入れ、要差し戻し、新比較に必要な未固定前提を明確にし、棋力/速度/採用を認定しない。
