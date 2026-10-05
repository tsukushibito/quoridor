# SIGMA-INFERENCE-RELEASE / quoridor-4lc.13

試行1・契約版1、hypothesis 01a0f31c-2e4b-7170-82c5-69e1428c2418 → coordinator、目標quoridor-4lc版1継承。保守起点20:39:42UTC、処理21:07:42/提出21:19:42。暫定報告を先に保存。.11はcritic .12と統括の固定28演算互換性限定受入れを確認し本人close、過去/tmp逸脱・RSS欠測は保持。

問い: 共通Rust NNをowned同期評価として接続可能か。新独立workspace tools/ai-sigma-inference-releaseでModel/planを所有しDrop、648f32長/finite、IO/output shape/finite/value[-1,1]を検査するError(code/detail)を実装。Wasmは再利用しないhandleとmodel/input/output/free、checked host viewを実装し、短いfeature・NaN・hash/schema不一致・壊れた短いmodel・stale handle・二重freeを拒否。SHAは実bytesをnative runner/browser cryptoで検証する責任分担で、Rust load_verified自体はdigest attestation比較。悪意あるattestationや生viewの寿命違反まで安全とは主張しない。entropy不足時error経路を保持、モデル実呼出し0でentropy分岐は未実証。

観測: native/Wasm releaseとも固定28件（合法20/人工8）×137要素で事前abs≤1e-4+1e-4×abs(reference)gate失敗0、maxabs9.77516e-6/1.04904e-5。出力bytesも旧debugと一致。固定ONNX d790…908d・fixture206f…bffb・ORT060b…382a、特徴順/演算/閾値変更0。tract0.22.3ほか130 registry packageは旧lockと一致、offline/locked・opt3/LTOなし/codegen16/debug0。新native22,827,184bytes、Wasm13,920,560bytes（旧debug76,401,984/36,970,550、API変更も含む比較）。native100推論/3load-drop、Wasm100推論はlinear37,814,272bytes一定/live1。drop後0、同instance3reload-dropは49,479,680bytesでplateau/live0。memory growは縮まらず、free減少を合格条件にしない。

探索的時間: 固定initial-p1/asym-hv-p2/straight-jump-p2、各1warmup+10samples。native NN p50=4.345/4.052/4.048ms、p95=8.276/7.330/4.560ms。Wasm p50=47.500/42.800/39.950ms、p95=69.200/76.500/64.100ms。初回plan loadはnative88.102/Wasm262.800ms、Worker load61.700/compile28.700ms別記。後続case先頭はプロセスcoldではない。.10と並行なので正式速度・製品着手時間・持ち時間・棋力へ転用しない。

Worker診断4経路: idle取消は計算0、単位間取消は1NN後停止。取消timestampが1NN span内にあり、意図的な非yield20連続NNではcancel ackが915.900ms遅れ、取消後20NNの完了を待った。旧generation3のresponseを呼出元が拒否、新generation4のみ受理。drop/live0→terminateを確認。同期NN中messageが割込めない制約を支持するが、この20NN悪い診断ループを製品の取消遅延としない。SearchSession/製品Worker/強制取消の再load費用は未試験。

資源・停止: CPU0/jobs1/GPU0、RSS観測最大1,542,123,520bytes、200ms監視の瞬間peak限界を保持。初回Wasm compileはstorage guardでSIGTERM/残存0、944,406,028bytes（guard約4.9MB超、1GiB配分内）。新規重複source/archive約85.4MBだけ整理し旧cache読取参照へ替えて1回再開、上限追加なし。最終追加unique inode約921MB、path論理約1,005MB、累積保守約2.336GB/3GiB、追加残約153MB。観測計算CPU下限482.405秒。旧cache・モデル・原artifact等6,314hash前後一致、新package取得/共有更新0。失敗証拠/旧cache/他者削除0、製品core/ai/wasm/bridge/Worker/rootlock編集0、対戦/学習/委譲0。

詳細: runs/SIGMA-INFERENCE-RELEASEのstart/cache-reuse/resources/diagnostic-summary/{native,wasm}.gate各JSON、stage log/process、manifestと独立Cargo.lock。再現はtool README。全自己PID/starttick残存0、port開設0、専用t残存ファイル0。最終保存後に書込み停止、pause確認/backup/report。.13は受入れ待ち、独立release再検証は未実施。A共通Rust案は互換と所有境界を支持、B分離ORTは非同期橋渡し費用を残す代替、C B0維持はNN非分割時間を避ける対照。次は独立境界検証と.10研究Evaluatorへの最小接続・1NN前後の予算/世代/yield確認を別契約で提案。製品採用や棋力達成は認定しない。
