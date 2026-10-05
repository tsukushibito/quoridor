# quoridor-4lc.85.1 / 再実行・記録規約の実適用

steward 01a0f31d-99ee-7d63-b162-bc1a59c457c6 → root所有.85、coordinatorにも通知。受領23:24:45UTC（Oct2 08:24:45JST）、本人claim/開始済。処理23:39:45/新tool23:36:45/報告23:44:45UTC、CPU0/RAM1GiB/new8MiB guard6は既128MiB内/追加予約0。単独writer、統括の未送信別依頼は使用0。83研究source/新NN/取得/対局/push/削除/他人kill0。

主 docs/development/ai-research-experiments.md 全文を読み、両common・team design・規約/template mirror・継続正本・監督prompt/契約へ適用。課題/Git版/runを分け、必要な結果/ログだけ保持、許可範囲/総予算内の修正版デバッグ・再現/性能測定を反復可能とし、正式評価の成績選別は禁止。研究ローカルGit管理を許可し、製品main統合/push/公開は対象外。親の一律新copy必須/研究commit禁止を解消、期限/資源/正式評価・旧結果は不変。

ユーザー明確化を同作業で反映。「終了窓の再開」禁止は旧実行の期限・成績の遡及書換禁止を意味する。同コード・入力・コマンドでも現在許可範囲/総予算内の新runで再現確認でき、旧.80内容の新run検証自体を禁止しない。進行個別許可差分/残予算はcoordinatorが判断する。本作業はNN再実行を開始していない。

.82.1の6role source bytesはすべて保持（role改定全文不変）、限定受入れ理由をnotesに残して本人.82.1 close済、親82/85/goalはclose0。規約正本/template mirror一致。版参照HEAD a62819d4ef6b9c63587e7c20dbe6344c5ded5045、変更した定義と必要な旧bytes/RPC要求応答/コマンドだけを自己runへ保存し、全履歴copy/hash/gateは追加0。

所有scheduler/監督idle・ownedなしでdispatch lock下に既存stop、旧monitor終了までlock保持し新role起動を抑制。明確化時も自temporary refresherを同identityで終了し、同runtimeの秩序ある再遷移を記録。現在scheduler PID1754421/starttick15050340、monitor PID1754436/starttick15050382。config/contract hash・20分/180秒/閾値2/read90-120/Oct2 00:55停止・00:58回収を保持。新common/prompt/rolesとmonitor期待hashが一致。source差替後6registry digestを整合させ通信を維持し、registry一致と恒久適用完了は区別した。

保存6session: 最終snapshotで恒久適用済=coordinator,hypothesis,critic,supervisor、恒久適用未完=experiment,steward。activeには正確turn IDへの規約全文supplement steer成功、強制interrupt/resume0。idleにはcommon+既role+runtime suffixの明示thread/resume、モデル/effort/cwd/settings一致を保存。実developer本文読戻し不可というAPI限界を保持し、metadataを成果成功と呼ばない。このsteward自身は現在activeのため恒久適用待ちである。

元idle補完helper PID1754440/starttick15050392は23:36:45UTC cutoffで終了済。新RPC再開0、最終pendingはexperiment/steward。active正turnへの全文補足acceptedと恒久適用未完を区別し、自己idle待ちだけで文書改定を未完としない。

本文前にshort-jobs-stopped.jsonとapplied-version.json保存。既知完了短期identity不在、recorder同期exit0。旧temporary helper不在、idle補完helper終了済、長期scheduler/monitorは残存、全自己PID0とは主張しない。所有new allocated 643072B/guard6内、背景RSS標本peak 52158464B、combined保存標本 3457024B。全scope正確増分/瞬間peakは未認定、旧課金/累積12GiBをリセットしない。旧期限逸脱・失敗/NI未立証/goal未達保持。

証拠 /workspaces/quoridor/.worktree/ai-sigma/.artifacts/ai-sigma/continuation-20261001/SIGMA-EXPERIMENT-POLICY-85（before/applied-version/clarification/sessions/原RPC/steer/commands/stop）。source編集は停止、残る書込みは報告/bookkeeping・配送証拠だけ。長期00:55 scheduler/正確ownedturn停止、00:58 monitor回収、01:00最終証拠責任は旧38/44/53/61から同ownerが維持。rootから本文整合の受入れと本人.85.1 close許可を受領。root所有.85のcloseはroot判断。全期間遵守/運用品質/性能結果は認定していない。

## 追加の現行本文整合とGit履歴

rootが文書編集/通知分だけ処理23:45UTC、新tool23:43、提出23:47へ明示変更。83/84/親研究期限は延長0。83/84契約を本文版2へ更新し、旧一原因一修正/最大2原因/一窓/救済再窓0/84独立受入れを機能デバッグ前提とする条文を削除置換。83はNN0 preflight成立後の現NN機能確認/費用測定を許可本文に明記、進行測定は中断0。84はNN0のまま将来配分Oct2 00:10処理/00:20提出と受領20/30分を本文へ統合し、旧23:40/23:50に戻していない。parent版3を本文運用へ更新し、83/84が新実hash 7d47d170a8b158f95a2f8df331fa1d45c0433416400f70105d99cd719c6a709eを参照。主/研究mirror一致。旧80の期限/結果は変更0、同内容新run再現可。83正turnへの有効全文通知は83-contract-notice-response.json、84新起動0。

契約/設計の過去版をGit履歴基本とする旨を新規約とmirrorへ追加。研究codex/ai-sigmaのprivate indexと明示8文書だけで、確実な既存修正前parentをcommit a270ec965a6de6607ff35f6f4ecc1c5b6b9a45e0、現行文書をcommit ebb3a0b1f833ea24c5693a813f104dfd45c443abに記録。83コード/他者未完成作業をstageせずmain統合/push/公開0。83/84修正前の全文が未Gitだった分は履歴未記録として明示、必要な実dispatch/before hash参照を保持し、旧全文を捏造してGitへ追加していない。全過去移行/コピー/削除0。

元のidle恒久適用補完jobは23:36:45 cutで終了（2026-10-01T23:36:45.990890+00:00）。最終permanent_pending=experiment,steward。該当activeへの正turn全文補足acceptedは保持するが、恒久適用は未完として残す。今回の追加延長は文書/通知だけで、この旧jobを黙って再開していない。全6source digest/registryと監督運用は整合、source変更だけを恒久適用完了とは認定しない。root/coordinatorは重複writer/別適用turnを起動しない。


root最終指示によるteam designの既存scheduler説明1行mirrorを修正し、当該1文書だけcommit d585901e4b261eafeb755412c165926deba01c74 に記録。研究コード・他者index・role sourceは変更0。文書編集終了、過去83/84全文履歴の欠落は上記の通り。長期運用以外の新研究tool開始0。
