# ブラウザの外部ORT評価とRust探索の継続試作

quoridor-4lc.26 / SIGMA-ORT-SEARCH / 試行1 / 版1。experiment 01a0f31d-6d15-7620-bb63-4b4f878e4746 → coordinator 01a0f31b-3409-75f2-a30e-453a50484f94。

目標契約ai-sigma-research-goal.md版2全文とAGENTS/common/experiment/team/設計/storage/handoff/protocolを継承。全体終了04:00:00UTC/JST13:00、開始不変。過去期限/RSS/TMP/affinity逸脱は保持。作業ai-sigma/codex/ai-sigma、通常製品standard/M2/UI/描画/主checkout/他worktree/製品Worker・wire変更禁止。追加委譲/学習/GPU/モデル再取得/追加勝敗0。

判別する仮説: 同じモデル・特徴・Rust探索を維持し、ブラウザNNだけ固定ORT-Webへ移せば、同期tract-Wasmより同時間の有効探索量を増やせるか。32局はnative9W7L/browser3W13L、NN中央値native4.239/Wasm47.5/参照ORT13ms、sim66/9/22、browser2期限loss。観測は判別の根拠だが原因確定ではない。競合A共通Rust同期tract、B分離ORT＋待機継続、C B0を保持し、評価品質/PUCT/FPU/局面・先後/時間制御の別説明も残す。固定済み32局/m/T/成績を変更・正式認定へ格上げ0。

基準入力: .21実報告SHA5fb3486daa2e7596b9373851f30d25b5b863bf485fcc84121f9c3ae422a0c592、.15/.19最終sourceと immutable final.wasm SHA891cd5e402885afc234b6041eab682bf429506848c5be532028bbe32e3c2f328、.21native transport9a7e768af5e6fdc58c16b5cc1e7c42df16372ff1654fef3503f410b402635b68。Sigma751186344fc52ad0c29bc65922e62c6fa915f006、ONNX11663428B/d790dac68389f7602ff8a887a2385417d3c925fe22da7164c86e9226f943908d、fixture28/206f46e0763177f138317ba49dc82875fd49a4d2c4ac2844d7fc06911e30bffb、ORTCPU060ba1a3f7647adb7c0ac968eb2834d966665920f72eeee2b3798ce9864b382a。rootCargo.lock f1b7e28714344098c70588371a8869a128612c40e0762c4cd0fbc0677309f346不変。

最初に基準のlive source/hash/diffと過去immutable入力を凍結する。許可write: 新 tools/ai-sigma-ort-search/ 独立workspace・研究Worker/checkedhost、.artifacts/ai-sigma/runs/SIGMA-ORT-SEARCH/、専用cache/target/temp /home/vscode/.cache/inference/research/ai-sigma/ort-search/、docs/reports/ai-sigma-experiment-ort-search.md。共有Rust searchを最小修正する場合は crates/quoridor-ai の追加research feature/optional module/tests/Cargo.tomlのfeature配線のみ、通常constructor/API/アルゴリズム/ルール不変。旧.15/.21 source/kernel/raw/モデル/lock/tools原物へのwrite0。コピーで実装するなら同じkernelとの差分と維持対照を保存。手作りJS別MCTSへの置換は本問いを満たさない。

同期Evaluator契約にasync session.runを直接返せない。pending leaf/合法順・history/path・評価request token・世代を所有するexplicit begin/resume境界を設け、出力1回だけ検証してexpand/backupを完成させる。cap fallbackにもpending評価が必要なら同じ意味を保持。未完成evaluationでvisits/backupを進めず、cancel/error/late/stale/別token/二重replyは検索をdiscardし合法checkpointとして公開0。終局はNN0、兄弟pathへoverlay漏れ0、モデル失敗のB0成功fallback0。最初の設計判断と安価な同期spy出力一致を保存する。全面書換が必要/予算不足ならpending prototypeの限界を返して無制限拡張しない。キャッシュmissで探索をやり直す代案は重複仕事・乱数/backup同一性の検証が必要で、黙って同じコスト扱いしない。

Rust側648f32生成・136canonical→P2→209合法prior/softmax・value視点を維持。actual model bytes hashを読み込んだ同bytesで検証、shape/finite/value厳密[-1,1]/prior非負正規化を確認。既存ORT-Web1.21.0のlocal JS/Wasm/mjs/noticesをread-only再利用、wasm provider/numThreads1/proxyfalseをsession作成前に設定、GPU/WebGPU/複数session/ponderなし。ORT依存version/モデル演算/PUCT1.5/Q0/tie order/seed1979/caps/TT/tree reuse/solver/FPU/queue変更0。CPUref固定モデルの計算を弱めない。

結果前gate: (1)同じspy/事前記録NN出力で synchronous既存とpending/resumeの手・合法順・history/visits/valuebits・statsが一致。pawn/wall1/2ply符号、root/兄弟/反復、node/depth fallback、goal/200/no-legal、terminalNN0、invalid形状/NaN/範囲外/二重reply/旧generation/途中cancelを実試験。(2)全28case features18144bits exact、NN3836/prior3187を既存abs<=1e-4+1e-4|ref|固定gate、合法20/人工8とterminal raw診断を分離。(3)既存固定8case×1/8/32simの小検索とcap構成を可能な範囲でRust同期/ORT非同期・参照Stateに照合、実NNfloat差による分岐は記録して閾値緩和0。(4)通常6case192/512/24/seed1979/step4の元immutableB0出力と通常constructor/feature-off不変、通常Wasm公開面不変。fmt/clippy/必要test、元全artifact hash前後確認。

正しさgate後の探索的計測はgolden initial-p1/asym-hv-p2/straight-jump-p2固定、各backend warm3+10samples、A/B順はcaseごとAB/BA交互で結果前manifestへ。A既存tract-WasmとBORT-Wasmで同じCPU2・モデル・Rustlimits4096/512/depth24・seed1979・step1・T500/g91・prefix供給からvalidity/配送まで共通時計。各新pending leaf単位後macrotask yield、重い処理T-g後開始0、T後のNN/backup/checkpoint採用0。load/warm/compile/startupを別記、返却手/完了sim/NNcalls/各span/end-to-end/overshoot/p50/p95/max/OSthread/RSS/linear/容量を全sample保存。T/gはこの診断の固定値で正式な安全性凍結・新棋力条件ではない。先に少数NN時間のみ成立して全検索未完了ならそこまでの限定報告。60診断sampleからtail保証/棋力改善を主張しない。32局prefixを最適化選択のholdoutへ再利用せず、正式poolへ送信0。

準備CPU2,4/jobs2、診断CPU2単logical/全Chrome child/TID/monitor、RAM4GiB guard3.5、追加1.5GiB guard1.25、実験所有5GiB guard4.85（.21現在保守3,676,045,312Bを含む）、GPU0。critic .25 CPU0/RAM1でチームCPU<=4/RAM<=8/LLM統括込み3、新規全体12GiB枠維持。hyp約2.383GB・model約12MB・critic実物を二重計上しない。大きな取得前のsteward観測から物理空き/owner別保存を再確認、原固定runtime/既存cache読取再利用・clone/全cache複製なし。offline/locked初期、不足固定checksum packageだけ32MiB以内かつ追加枠内で取得可、version更新0。準備build/診断重なり0、他者kill0、正式無負荷とは呼ばない。

保守起点issue作成00:10:19Z、処理停止01:35:00Z/提出・書込停止01:45:00Z/global04:00以内。01:30以降新job0、stopJSON/PID0を報告生成前保存。各build timeout600秒/runtime120秒か残枠の小さい方、guardで自己PGID全descendant止めwait。修正再試行は原因別1回・元予算内。privateTMP/XDG/alive短aliasrealpath・PIDstarttick/全子/TID・50msRSS/保存/affinity/SMT/exit監視、欠測/超過/過去失敗を保持。整理は自己新incremental等再生成cacheのみ、原証拠/モデル/lock/失敗log削除0。

ready/show目標/.26/.21、pauseなしなら自.26claim。.21は成績独立受入れ待ちでclose0、.7queue保留保持。目標/他者close0。暫定短報告を先保存、最終<=2500字と詳細JSON。書込/実行停止→show/backup/report --to coordinator --issue quoridor-4lc。採用/新対局は独立critic gateと別事前契約後のみ。許可scope内は追加承認不要、実装困難時も競合A/B/Cと費用/反証を返す。
