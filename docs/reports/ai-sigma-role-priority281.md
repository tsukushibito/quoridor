# 汎用的な候補比較・推奨順位の役割適用（281.1）

2026-10-05。Root281がhypothesis/coordinator/supervisorのmain役定義3pathを更新し、既92運用ownerが現commonとの全文・保存session・registry・監督運用へ実適用した。今回の改定は候補の比較、推奨順位と選択/保留理由、必要な観測規模、適用後の効果を研究判断へつなぐ。特定方式・候補数・数値採点・全run比較を必須にせず、科学条件と許可枠は変更しない。

## 3役への適用

| 役          | 公式適用                                                       | 恒久developer適用                | 現combined digest                                                  |
| ----------- | -------------------------------------------------------------- | -------------------------------- | ------------------------------------------------------------------ |
| hypothesis  | 正active `01a10c49-9947-7dd3-a580-b98fb13287e2`へ全文steer受理 | pending、既92所有                | `591b3c22b5a703abb34b8c11d579dfd79048a8577d82a215807b97b0398c230b` |
| coordinator | 13:52:08 UTC自然idle、同settings公式refresh受理                | 完了、276のpendingも最新版で解消 | `bdfa28ce0dbf9557a1e42c8cdf9ced9b60e7cbe1bcfb6e60b4d47fa20be0c472` |
| supervisor  | 13:52:09 UTC自然idle、同settings公式refresh受理                | 完了                             | `09ecbd31b62579b05c362528c581c51415570659a768c2915e62be4a3cb3b050` |

[session適用receipt](../../research-data/ai-sigma/281-role-priority/session-application.json)に3role sourceSHA・保存全文SHA・prior/afterの同saved/model/effort/cwdを保存した。developerInstructionsの直接readback getterはないため、公式RPC受理と保存した全文hashを根拠とし、実判断の改善とは区別する。Hypothesisの恒久適用は同役の自然idle時に既92が公式refreshする。新turnやinterruptでidleを作らず、科学taskの開始・継続をpending待ちにしない。旧276証拠は変更せず、Coordinatorの最新本文に276責務を含めて解消した。

## 安全窓・現在binding

13:41:34開始のSupervisor自然turn `01a10c4c-5f64-7622-b581-d31ac6edcfe8`が13:47:43にcompletedとなり、公式idle/ownedなしを再確認して13:49:40 UTCに安全窓を成立させた。自己旧scheduler `1233793/tick45593355`、monitor `1235182/tick45599721`を秩序停止し正確不在を確認、旧state/registry/monitor終端/config/prompt/期待はbeforeへ保持し、旧3roleと監督契約のsource本文はGit `3750a9960072912a427807c47f3f9bf82be44480` の正本path/SHAを復元元にする。旧/提案role全文の重複7コピーは保存対象から除去し、新3roleはmain正本と今回の保存commitを参照する。[Git参照と分類](../../research-data/ai-sigma/281-role-priority/source-git-references.json)に7pathの一致/未追跡確認と削減量を保存した。実配送したcommon＋role全文・RPC受理・runtime証拠は保護した。safe-window記録のlast_resultはprocess_stoppedを指す。自然完了の根拠はbefore/state.jsonのowned_turn_finishedであり、両者を区別する。Rootへ指定3pathだけの編集可能を通知し、Root source-stop/new3SHA受領後にのみ更新した。

現監督契約本文とpromptの選定点検を新roleへ整合し、有界読取・保存・終了条件は維持した。registry変更は3role digestのみ、24期待input集合は増やさず、hypothesis/coordinator source・registry・契約本文・promptの5hashを訂正した。Supervisor sourceは保存全文SHAとregistryの現digest照合で確認した。役定義へのSteward書込、common・他role・親本文・科学source変更はない。JSON運用contractとconfigの数値/構造も変更していない。

通常validate/startは一回。13:55:30 UTC、新scheduler `1351785/tick46157199`とmonitor `1351801/tick46157223`、同boot `ab5e66ac-12ce-49b0-ac55-afe05e3f5216`を現在確認。running/loaded config-contract SHA/current24hash/6digest・正2identity・旧2不在・period1200/max_turn_seconds null・end15:31:03の14項目が成立した。[現在照合](../../research-data/ai-sigma/281-role-priority/runtime-applied.json)参照。期待identityはstart receipt/current stateとexact照合してからbindし、二度目のstart/強制tickはしない。gapを保存し新自然点検の効果や未来成功へ読み替えない。

先に統括へgapを送る操作は共有dispatch lock取得で送信前拒否された。RPCは未送信、拒否receiptを保存し、後続の正式全文適用と今回の引渡しへまとめた。応答不明の盲目再送ではない。科学owner processへの停止/介入はない。

## 費用・確認・引渡し

CPU0 single/RAM512MiBの短管理で、科学NN/学習/GPU/game/build/取得0。既keeper currentと276/281新scope現量、既3MiB forecast、新2MiB保存上界を保守加算して既112MiB内を再確認。unknown減額・親予約追加・旧cap resetをしない。新コード/helper/試験はない。変更した契約本文/prompt/registry/期待JSONをproject Prettierで整形/確認し、scope diffcheck・通常validate・実binding14項目を確認した。

Rootへ本文/適用/現在実運用の必要証拠を引き渡し、統括一人が明示pathを通常Gitへ保存する。sourceと短期子は停止、意図した長期scheduler/monitorのみ継続。保存byte/SHA確認後に本人281.1をclose/backupし、92・goalは継続。15:26:03新heavy通知、15:31:03正owned scheduler、15:34:03monitor回収、15:36:03必要保存の92責任は不変更。役適用の受理と、候補比較・配分・自然監督の実判断改善は別に後続観測へ引き渡す。
