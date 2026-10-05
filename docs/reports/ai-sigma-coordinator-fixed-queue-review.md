# SIGMA-FIXED-QUEUEの統括判断

quoridor-4lc.7 / SIGMA-FIXED-QUEUE / coordinator / 2026-09-30。報告SHA d0b39d9798995f5d38107ad6d00162c63ad588186f6e44d48b336a3fc1d77f00。統括はsource queue差分と停止台帳、native/browser全sampleからmedian/gainを独立再計算し、fixture hashとbaseline/candidate dump bytes一致を確認。新速度run/全Rust差分再実行は行っていない。根拠 .artifacts/ai-sigma/verification/QUEUE-COORD-STATIC/summary.json。

採用保留。原3native時間削減1.47/3.42/2.23%は目安5%未満。P2-1.83%、jump-3.46%、many-walls12.19%もround3は0.44%。Wasm初期0.05%、opening1.89%、壁中盤5.93%のn6探索的観測でtail/cancel非劣性は未立証。全面速度改善/同時間棋力を認定せず、候補source/binary/Wasm/rawと負sampleを保持。queueだけの低効果がLegal/BFS全union仮説の否定になるとはしない。正しさの全面独立受入れは未実施、.7は検証待ちを保持する。今回sourceを黙って採用せず、次課題開始時にqueue部分を保存済みbaselineへ戻す。

安価なqueue単独効果が十分でないため、同じ速度条件を無制限に反復せず、H2の前提であるSigma研究規約とAction/featuresへ移る。experiment .10へ内部history/totalply/terminal/cap/backupとnative-Wasm共通648feature/136mappingの実検証を配分。steward .9へ固定ONNX取得・静的graphのみ配分済み。モデル推論/正式棋力比較は未開始、parity前に低成績をH2negative扱いしない。

全体期限01:17:58UTC、19:34時点残約5時間44分。experiment追加1GiB/累積3GiB/RAM4、steward128MiB/RAM1、CPU準備計3（exp2/steward1）、GPU0/学習0。次の重大な判断はcontext/NN互換性gate、queue独立検証の優先度は低gainを踏まえて後続の空き枠で判断する。
