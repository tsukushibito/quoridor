# frame24連続extension25の運用適用 / Steward92

ユーザー01:24:53Zの明示2時間追加を適用した。開始2026-10-06T00:08:46Zは固定、終了04:08:46Z、新heavy停止03:58:46Z、Supervisor正ownedとscheduler回収04:03:46Z、monitor回収04:06:46Z。終了点検の通常依頼は03:40頃までに扱う。period1200/max_turn_seconds=null、全saved model/effort/cwd、CPU4/RAM8GiB/VRAM6GiB/storage12GiB/UNKNOWN128MiB/keeper112MiBを維持した。

## 実適用と確認

Supervisor自然turn01a10ed7-e24d-7c92-9d50-6cbfa27192baのidle/ownedなしと、310の4ケース・記録済み科学子のexact不在を直前照合した。Bの2233899は完了通知専用とsource/owner receiptから分類し、他者のinterrupt/cancelをしなかった。旧正scheduler2169413/t50105376・monitor2169432/t50105414はownmonitor pidfd TERMと既stop_exactで秩序停止し、旧state/deadline/source・管理失敗を保持した。自然turn開始で安全条件が成立しなかったv1/v2も原観測として残す。

親版25とSupervisor運用本文、新namespaceのconfig/JSON契約/prompt、registry current_operationと24input期待SHAを整合した。target/settings/common/役定義は変更していない。config/contract pathが変わるため別state .artifacts/research-team/frame24-extension25/schedulerへvalidateと通常freshstartを行った。新正scheduler2269819/t50428490・monitor2271322/t50433272（boot ab5e66ac-12ce-49b0-ac55-afe05e3f5216）、running、loaded config57c17913/contract0e394a4b、24hash、6digest、旧2不在・開始/新期限/settings等18/18を確認した。詳細は extension25-running-loaded-v1.json、再照合は extension25-post-refusal-current-binding-v1.json。

最初のowned20b07d8b/turn01a10ee4-8909-7361-8545-b2249dc7df38は01:47:00.721225に通常dispatchされた。PIDを期待processへbindする前にstate_readを呼んだため管理確認が拒否され、そのgapで最初のobserveもexit2/commands空、観測・finish・backup未到達だった。起動のexit0と正identityを確認して既processをbindし、再start/同run再observe/再dispatch/force tickは行わなかった。原拒否はarchiveへ保存し、現在validなbindingと別の点証拠にした。次の自然observe/finish効果、全期間/未来停止、科学・棋力の成功は未認定。

## 累積と個別期限

GPUは同frame24-new-GPU-training-3600を継続する。new-GPU-all-attempt-accounting-v1.jsonの全費消費13.493288946秒・残3586.506711054秒を参照し、旧7200秒UNKNOWNと初raw部分観測を保持した。延長でGPU/NN/MAX/個別費をresetしない。310の原science01:40/source01:45/save01:50、313の原source01:30/save01:35・NOT_ADOPTEDは不変更。315のmain描画移行は別の明示phase/owner/source quietで扱う。延長から追加fit、新corpus取得、方法/教師/batch/特徴変更を推定しない。

## 小scopeの保存判断

315は旧313の128KiBを再用し、current86016+必要残24576=110592Bを確認した。313/315を二重予約せず、旧private archiveとNOT_ADOPTEDを保持する。

310最終v2のfiles-only pointだけではdirectoryを含む局所量と必要Git/tempで32394B不足だった。この不足と原v1/v2/v3は保持し、統括の確認unused64KiBとclosed ownerのstorage-only受入れで、coor7.5+3109MiB=coor7.4375+3109.0625MiBを保存した。fresh3108814592+必要Git634972+remaining32768=9482332B<9502720B（余20388B）。coor current2subtrees2568192+旧category4427776全保持+Git/temp524288+315cap131072+metadata32768=7684096B<7798784B。科学を再開せず、削除・未知減額・親増額・whole rescanをしなかった。

316は旧analysis.25MiBの同rootでcurrent135168+Git65536+temp32768=233472B<262144B。proposal16KiBはcurrent内で二重加算しない。提案のみ、モデル/取得/decode/NN/GPU/方法採用0。

317は既WT内TT namespaceを使い、parent current1089536内のtelemetry57344Bを二重計上しない。旧保全1126400/coor archives329210/main2source116122/新source-evidence98304/必要Git-temp262144のinclusive1932180B<同TT2MiBを確認した。新sharedtarget4MiBは旧31116/29432内、freshrelease537174016Bの低下からunusedを返却しない。旧311 compile120=retained60+31760はownerのallattempt34.886548/原Clippy/MAXを保持し、ONE NN0ソフト20秒をcompile内で別にadmitする。保管成立は科学/NNUE性能・棋力の許可や成功ではない。

## 保存と引渡し

旧runtime 12memberと新config inputs・初自然拒否のarchiveは全byte/SHAをstream復元した。役source mirror・raw/model/dataの大コピーを作らず、現在設定の実入力と失敗証拠だけを保存する。source停止の明示manifestを統括の単一通常Gitへ渡し、Beads notes/backupを行う。92/goalはin_progressのまま新4期限の回収責任を維持する。Coordinator恒久idle refreshとwholefinish信頼性は別pendingであり、このloaded成立で完了へ置換しない。
