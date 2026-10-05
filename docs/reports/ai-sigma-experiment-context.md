# SIGMA-RULE-FEATURE-PARITY 報告

quoridor-4lc.10 / 試行1 / 契約版1 / experiment 01a0f31d-6d15-7620-bb63-4b4f878e4746。統括宛。目標版1とcontext契約に基づき、通常製品規約を保持する研究context・Action・featureの整合性を検証した。受入れ待ちin_progress。NN/対戦/学習/solver/FPU/追加最適化/委譲0。速度・棋力改善は判定しない。

作業場所は /workspaces/quoridor/.worktree/ai-sigma、codex/ai-sigma、HEAD1482df8da6dd91c95db211aeaa914af775b2bc76＋既存差分。旧.7候補source/binary/Wasm/rawは保持し、live queueだけVecDeque基準へ復帰（position.rs SHA256 b12e79a99cf3441cf4acebbea1b827dce24b02db6fb2269021964872535e3ab6）。.7採用保留を維持。.5は限定受入れnotesに従い本人close済み、short overhead gate不成立の証拠は保持。

研究featureを分離し、exact盤面・手番・壁keyとrootを一度含むbase履歴、各探索pathのoverlay、totalplyを合法集合・評価mask・遷移・終端・cap fallbackへ伝えた。駒の3回目反復を禁止し壁手も記録、goal優先、200ply/合法手なしはdraw0。合法prefix入口と人工専用診断入口を分離した。通常Node構造・constructor・wire既定は保持、lockfile変更・新依存取得なし。

固定参照fixtures SHA206f46e…0bffb、game.js SHA dfa438a…46c5（全文hashはmanifest）を自己copyの参照実装と照合し、20合法replay/人工history3/人工ply5を別集計。全28件で合法集合と各契約順序、136↔209写像・P2自己逆変換、648 float32値計18144、history/ply、raw/effective終端、raw参照遷移3187件が一致した。終局後raw遷移は診断であり合法対局継続ではない。

実SearchSessionの769node（終端36）を参照Stateで再検証し、最終native/Wasmでcontext・合法edge・visits/value bitを厳密一致確認。別4内部testsで深部overlay反復禁止、兄弟復帰、root二重count拒否、198/199/200・goal優先・人工no-legal、node/depth/arena cap、pawn/wallの1/2ply符号を検証。終端root4件のevaluate呼出し0。評価器は固定spyでNN実行なし。研究arena見積最大native137398/Wasm103918bytesはpointer幅差を別記。browserの28件一括JSON診断memory約67.6MBとは別の量で、実allocatorは未計測。

通常6局面192sims/512nodes/depth24/seed1979/step4では旧immutable B0、現feature-off、research有効の通常constructor間で手・prior/visits/value bit・合法順・距離・全遷移・stats/arenaが一致。通常Wasm JS/型公開面も旧基準と同一、research exportなし。core/ai通常24・全feature31、Wasm ai wire2・rules6 tests通過。fmt/clippy/diff check通過。Wasmの既存rules/aiは相互排他なので対応する各feature構成で検証した。最終Wasmは初回artifactとbyte差があったため最終版もChromium153/CPU2で実行し再照合した。

未完了は実際の合法200手replay、実履歴からのno-legal例。直接history入力の算術検証は到達可能性の証明ではなく、人工8件で代替完了とはしない。arena cap testは会計境界注入で実メモリ枯渇ではない。独立再実行・受入れは統括待ち。今の結論は固定入力と内部経路での整合性支持に限る。

保守開始19:32:28UTC、処理期限20:52:28、提出期限21:02:28。最後の子終了20:45:54、全自己子回収、server/Chromium終了、5183/5184 listenerなし、他者kill0。準備CPU2,4/jobs2・診断CPU2、RSS同時保守上限約1.092GiB。追加保存現在約0.77GiB、peak977268736bytes（1GiB以内）、所有現在約1.66GiB（3GiB以内）。余裕storage guardで一度停止・回収し、新規の自己incremental cache244097024bytesだけ整理して再検証、旧証拠削除0。

初回VM比較、入力cap、clippy失敗と修正後結果を保存。最終native診断とWasm buildが重なり1系列契約から逸脱したがCPU/RAM上限内、速度評価なし。終了前Beads read出力2件を誤って/tmpへ保存し、自己runへ移動した。全面的な契約遵守成功とは報告しない。実装失敗・診断adapter修正・資源停止・scope逸脱を [manifest](../../.artifacts/ai-sigma/runs/SIGMA-RULE-FEATURE-PARITY/artifact-manifest.json) に分けて保持する。

再現はmanifestの固定入力/最終binaryとjob commandを使用し別outputへ保存。`cargo test --locked --offline -p quoridor-core -p quoridor-ai --all-features`、専用research-parity JSON診断、browser-parity-final-job.pyで再検証可能。source snapshot/patch/hash、raw、最終provenance、資源/停止証拠を保持。研究書込みを止めてbackup/reportへ進む。.10/.7/目標をcloseせず、次は統括の独立検証と未完了範囲の判断を待つ。
