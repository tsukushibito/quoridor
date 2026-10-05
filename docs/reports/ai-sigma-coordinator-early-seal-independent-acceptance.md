# .64 有限early-seal検証の受入れと共通参照経路

2026-10-01 17:16UTC、quoridor-4lc.64を限定受入れ。完成snapshotの候補側配送・取消後の同時計/旧CPU停止を支持する。全体時計gate・参照接続・実対局・棋力・Sigma同等到達は未成立、actual_go=false。

報告SHA3d52108f2ef0a9b5e51cf8898012e639589b1a6253d1edfc779707b0a1f78f25、manifest d367887e70ebe091f3c0f7c66832d2fbe086e59cffe055e1e3e3eba6ea9e9611を固定。1140原入力の現在hash一致・記録22 PID/starttick現在不在を統括確認し、正常9件の中央値412.462ms/max415.012msを再計算した。完全before1140詳細snapshotは688入力copyの上書きで未保存、当初stdoutとsource58/copy差分/688beforeを区別し、前後完全監査へ格上げしない。

最終revision3の一窓16要求は取消1・正常9（warm3/steady6）・境界6。正常9/9合法cp、NN0終端2、取消ACK後に次NN、次t0=前公開stamp、停止待ち31.027ms課金を支持する。6正常配送はsession.run API区間内でありexact kernel命令時刻ではない。busy518.708msはnull拒否、初回無し/cutoff跨ぎ/faultもnull、fault政策は受信順に限定。原任意treeの一般的検証ではなく、信頼した完成producer境界である。

元 .63の正常12/steady9/境界6/終端2、最初warm340210.191ms、原取消ACK欠測と未実行19のみ継続、forced回収・helper失敗・瞬間peak/背景欠測を保持する。独立成功で元失敗を救済しない。 .63と.64の担当は、今回の限定受入れと全no-go/未確認をnotesへ残して本人closeしてよい。目標/旧.60blocked/旧.56期限は変更しない。

次 .65 experimentは両AIへ同T500/reserve89/cutoff402/seal411のNode caller・完成通知・旧CPU残処理課金を接続する。参照C1/FPU.2/temp0/order/root展開sim外と候補PUCT1.5/Q0/seed/tie/finish/capsを維持、参照のroot訪問数を候補sim−1へ偽装しない。原固定work対照と両側少数単手の実検証を結果前登録する。新copyのみ、実対局/holdout/build/取得0、独立次gateと新結果前比較契約までactual_go=false。

詳細は `.artifacts/ai-sigma/continuation-20261001/FAIR-STREAMING-COORD-HANDOFF/independent64-review.json`。本書は新入力として固定し、worker動作中に追記しない。資源/Oct2 01:00UTCは不変、旧32局NI未立証/Sigma未達とA/B/C・H1〜H4を保持する。
