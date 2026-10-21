# ブラウザ内Rust Othello AIの強化

2026-10-22 JSTの人間の直接依頼「最強オセロAIを作成して。」を採用する。[添付要求仕様](strong-ai-requirements-ja.txt)を原文のまま保存した（15,857B、SHA256 `e1a866a06ce3feee0078e91e11254c4ef2bd7f71aa3a3b092425dc657e9b2fb1`）。本書はOthello強化の設計正本で、担当・状態・依存はBeads `quoridor-n96` / `quoridor-n96.1` に置く。研究観測は `research-data/othello/` へ保存する。既存Quoridor研究の再開・予算転用・モデル採用を含まない。

## 目標と判定

主評価はdesktop browser内の自作Rust/Wasm、探索1thread、1秒/手、book OFF、ponder OFF。同じ実時間と事前に固定したメモリ上限で終局まで対局する。native対native、Wasm対外部native、利用可能な公式browser版との比較を区別する。初期配布目安はエンジンと重み合計16MiB以内、TT32MiB、探索Worker全体256MiB以内とし、実測と実機の制約から変更理由を残す。初期source作業はGPU0、各実装family2GiB（controller64MiBを含む）、host reserve4GiB。実CPU/RAM/VRAMは各入場で既存制御が確認する。

正しく動くこと、強豪と比較可能なこと、事前同等幅で同等と判定されたこと、優位性が支持されたことを別に報告する。優位の主指標は相手ごとの得点率と開始family単位の95%区間。両相手それぞれで下端>.5を必要とし、片方のみ・区間が.5を含む・不完全を隠さない。同等幅は本評価前に別に定める。現在の簡易policyや実装完了を優位の根拠にはしない。

## 共通コアと境界

現GameStateの64要素board、version1、黒1/白2、row-major index、合法手・パス・終局・保存JSONを維持する。Vec/ray参照とcorner/flip/ID簡易policyを独立参照・初期対照として使う。新しいu64盤面、PVS/Negamax、TT、反復深化、時計、厳密終盤は同じRustコアをnative/Wasmから使う。TTは深さ・bound・探索modeを区別し、未完了結果を厳密値として保存しない。パスは着手深さを消費せず、双方着手不能なら空きが残っても終局。原規約の実石差と、外部engineの評価値・空き割当規約は別に対応付ける。厳密終盤に確率pruningを使わない。

最初にbitboard/ray照合、軽いperft、小終盤の独立全探索、native/Wasmと時計・中断を確認する。中断時は最後の完了反復の合法手へ戻す。同期WasmへpostMessageするだけで取消できるとは扱わず、内部時計とWorker終了・再生成で遅延結果を無効化する。Quoridorと共通chooserは維持し、OthelloのUI・対局制御をRust主体へ移す。JS/TSはWasm起動とブラウザAPIの最小接続に限る。

## 最初のnative接続仕様

CLIは1行1JSON要求/応答、stdoutはJSONのみ、diagnosticsはstderr。`op` は `new`, `status`, `play`, `pass`, `simple`, `search`。new以外は既存GameStateの `state`、playは `move`。応答は `ok` と `state` / `status` / `move`、失敗は `ok:false,error`。search要求は `timeMs`（暫定1000）、`ttMiB`（32）、`maxDepth`（64）、`exactEmpties`（12）。search応答はmoveに加えて `score`, `scoreKind`, `completedDepth`, `nodes`, `elapsedMs`, `timedOut`, `proven` を返す。heuristic値と証明済み最終石差を明示的に分ける。native専用I/O・時計とWasmブラウザ時計は外側、探索と評価は共通Rust。実装時の必要な追加fieldはcallerと同時に記録する。

## baselineと小評価

一次資料は[Edax](https://github.com/abulmo/edax-reversi)、[Egaroucid](https://github.com/Nyanyan/Egaroucid)、[技術解説](https://www.egaroucid.nyanyan.dev/ja/technology/explanation/)、[公開学習データ](https://www.egaroucid.nyanyan.dev/ja/technology/train-data/)。取得済release metadataはEdax v4.7、Egaroucid GUI v7.8.3。console案内7.8.1と混同せず、最初に起動できる公式Console7.8.1または固定source buildを選び、実commit・source/weight/book/dataそれぞれの条件、hash、起動args、1thread/時計/無book/無ponderを実確認する。公開dataは再配布禁止で本文をGitへ入れない。原C/C++engineを自作Rust runtimeへ隠して配布しない。

初期smokeは各相手4開始family×両色=8局。目的はprotocol・合法終局・費用の確認で、優位性判定には使わない。Rustルールを対戦制御の正本とし、違法手・timeout・crashも結果へ残す。時間対局に恣意的aggregate node capを足して未完了にしない。学習/調整familyと最終判定familyを分け、最終局数・停止・判定はpilot費用と分散から結果前に固定する。fair timing中は重いbuild/学習/対局/IO競合を調整する。

## 少量学習と改善

最初の学習方式は対称性を共有するphase別pattern table。小さな合法到達系列と固定外部教師/厳密小終盤からPython学習・export・共通Rust利用を一巡させる。教師推定値、対局結果、厳密値を区別し、STM・board向き・色反転・phase・石差規約を固定する。game/opening系列単位split、対称局面の重複を把握し、random row splitだけで独立と呼ばない。既存重みも条件・format・phase・視点の対応確認後に利用できるが、少量自前学習とPython/native/Wasm parityを省略しない。

量・時間・容量・checkpoint寿命・plateau/非有限STOPを小pilotのconfigへ結果前に固定する。大型data、NNUE、並列探索、選択pruningを初回に同時投入しない。改善候補は仮説→最小変更→開発集合比較→未使用familyで最終判断。NPS/depth/lossだけで棋力採用しない。各段階で動く最良版、失敗・費・未検証を保持し、最強目標の未達を明記する。

既存のmanaged Worktree・Beads・CPUPlan/CycleResources・job取消/回収/完了通知を再用し、専用manager・常駐監督・全員ACKを増やさない。50GB decimalは共通基盤と両ゲームの合計。Quoridor USERPAUSE323/342.17、seals/newE/oldfits96、models/defaults、原RAW/FAILED/NULL/UNKNOWN費を維持する。
