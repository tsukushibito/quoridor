# Sigma研究context・特徴・Action変換の実装と検証

quoridor-4lc.10 / SIGMA-RULE-FEATURE-PARITY / 試行1 / 版1。目標契約 [版1](ai-sigma-research-goal.md)と [比較方式](ai-sigma-comparison-protocol.md)を継承。担当experiment 01a0f31d-6d15-7620-bb63-4b4f878e4746、報告先coordinator 01a0f31b-3409-75f2-a30e-453a50484f94。追加委譲0。

## 問い・競合仮説・判断

PV情報不足仮説H2の小さな前提試験として、固定Sigmaの規約/136Action/648featuresをRust共通コードと探索内部へ正しく伝えられるかを判別する。B0速度が不足する説明と評価情報が不足する説明を保持し、この試験だけで棋力差を説明しない。正しい変換の成立前にNN移植や低成績を仮説不支持扱いしない。

SIGMA-FIXED-QUEUEは原3nativegain1.47/3.42/2.23%、P2/jump負、many-walls局面/round依存で採用保留。今回開始時、旧source/binary/Wasm/logはimmutableで保ち、live position.rsだけを.7 baseline-sourceのprofiling付きVecDeque版へ戻してhash確認（.5変更や他者文書は戻さない）。queue差分tests/binsは証拠として保持しても候補を既定対照に混ぜない。新source差分・復帰hashを今回manifestへ残す。

## 入力・操作要因・対照

研究worktree /workspaces/quoridor/.worktree/ai-sigma、codex/ai-sigma、HEAD1482df8da6dd91c95db211aeaa914af775b2bc76＋launch移入＋.5/.7未commit差分をsnapshot/hashで識別。基準は.7 baseline-sourceとbaseline-native SHA7ab2253c8f9556b2ff7f8feb187457277b01e3f4521d594c6a6e0486fa7d0166。旧rawの上書きなし。

参照 .artifacts/ai-sigma/reference-fixtures/SIGMA-PARITY-PLAN/fixtures.json SHA206f46e0763177f138317ba49dc82875fd49a4d2c4ac2844d7fc06911e30bffb、固定game.js SHA dfa438a500d6808e21bf8fef72a299cd762ac5e8be25251dd38607abb2d046c5、同conversion-contract/schema/input/manifestを読取。critic独立summaryは verification/CRITIC-PROFILE-PARITY/summary.json。参照generatorを原pathで実行しない。必要な再生成は自己copyへ。20合法replay/人工history3/人工totalply5を別集計。

対照は通常standard-2p-v1のB0、192sims/512nodes/depth24/seed1979/step4、既存6局面の決定的結果。研究規約Aだけを明示的に選択し、製品通常constructor/wire/Workerの既定は保持。通常動作のaction/rootprior/value/visitとstatsを確認、構造size変更でarena accountingが変わるなら実bytes/上限検査の差を別記し黙って同一扱いしない。可能なら研究型/featureを分離し通常Node構造も保持する。

## 実装範囲・内部規約

許可書込みは crates/quoridor-core/src/{position.rs,lib.rs,新research context/feature module} と対応tests、crates/quoridor-ai/src/{lib.rs,新research module,bin/研究診断bin} とtests、crates/quoridor-wasmの明示的research feature/exportと対応tests、これら最小Cargo.toml/Cargo.lock（新依存は既存cacheにあるもののみ、変更根拠/lockhash保存）、scripts/dev/新研究run/parity scripts、.artifacts/ai-sigma/runs/SIGMA-RULE-FEATURE-PARITY/、docs/reports/ai-sigma-experiment-context.md。position.rsはqueue復帰とcontextが必要な最小変更のみ。書込み担当experimentのみ。主checkout/他worktree/bridge/製品Worker/UI/render/M2/public models/チーム入口/他者契約報告は対象外。

研究規約Aは全nodeの合法集合、policy mask、transition、終端、cap fallbackへ伝達する。rootだけ不正手を除外する方式は禁止。履歴keyはP1/P2位置、side-to-move、H/V anchor集合のexact値で、hash衝突を唯一の根拠にしない。rootをbaseへ1回のみ含め、root後path overlayをchildごと追加し、兄弟復帰で漏らさない。壁手も履歴へ記録。駒手の次key既count>=2なら除外。goal優先、次に200 total plies/合法手なしはdraw0。開始prefixを200へ含める。sameboardでも履歴/残plyで合法性が異なり、TT/reuseを導入しない。

通常入力は合法prefixからcontextを構築し、checked盤面/手番/totalply/currentcount>=1等の整合を検証。contextを直接受け取る場合は検証の限界も明記。人工context専用診断入口だけでsynthetic欠落を扱い、製品/対局通常入力へ抜け道を混入しない。終局raw参照maskは非空の場合あり、raw診断とeffective終端mask空・展開0を分離する。goalat200 rawDraw=trueでもwinner優先。

136↔209は合法pawn方向を着地cellへ、jumpは方向のまま2cell、H8+a→81+a、V72+a→145+a。P2 canonical cell y8-y、anchor/Hsegment y7-y、Vsegment y8-y。8x9x9 float32planesは自/相駒、H/Vの2segment、残壁/10、両goal壁のみBFSmap/80。source Float32丸め・channel順を一致確認。壁anchorをplaneに置かない。全合法mask写像のinjectivity/roundtrip、P2permutation自己逆を実装・検証。NN実行なし、logits/valueの数値parityは次契約。

## 必須検証・受入れ

1. 28goldenを逐caseで全合法集合/order（参照方向orderとRust ascendingIDは別契約にして集合変換と順序目的を区別）、合法遷移、histories、終端raw/effective、136mapping/136perm/648float32featureを比較。合法replayと人工を分離。完全合法200手実replayと実history nolegal例は旧未完成であり、人工対応で完成扱いしない。
2. 独立に内部SearchSessionを動かし、深部overlayだけで3回目禁止、兄弟path復帰、root二重count拒否、totalply198/199/200、200でgoal優先、no-legal draw、depth/node/arena cap前後のterminal優先、pawn/wall1ply/2ply value符号を検証。評価spyで終端でNN相当evaluateを呼ばないこと、深部legal違反edgeが生成されないことを確認。診断全node/context snapshotまたは直接assertを保存し、rootfixtureだけで内部parity成立としない。
3. 通常規約B0の既存tests/6局面決定性を維持。locked/offline build、fmt、clippy対象crate/allfeatures、差分check。current計測器5%gateを再試験せず、速度結論を付けない。
4. nativeとWasmの同じ研究moduleでfixture出力を比較する小さなCPU browser診断を実行（明示research/testfeature、read-only既存Chromium、専用port、製品UI操作なし）。Wasm未実行なら未完了を明記しnativeだけで通過としない。20合法と人工8は別列。通常Wasm/publicwire APIの既定を壊さない。

## 予算・固定環境・停止

send/turn開始から90分以内、処理80分、最後10分は短報告/終了/Beads/report。全体deadline2026-10-01T01:17:58.145139Z以内。開始時に暫定短報告を作り、処理timeoutをdeadlineから算出し、時間が足りなければ未完成を提出して止める。報告日本語2000字程度、raw/detailはJSON/manifestへ。

準備CPU2,4の2論理/jobs2まで、診断はCPU2単一。RAM4GiB、GPU0、追加新規1GiB、experiment所有累積3GiB（.5/.7約0.885GiBを含む）。steward .9はCPU0/RAM1GiB/128MiBで固定ONNX約12MB取得と静的解析、統括を含むLLM3役以内。全体CPU4/RAM8/新規12GiB。モデル/NPM新取得なし、既存専用target/cache/npmとread-onlybrowserを再利用、共有toolchain/学習envを更新しない。Python standardのみ、UV_NO_SYNC/OFFLINE/PYTHONDONTWRITEBYTECODE。監視自己PID/child affinity/RSS/保存量/exitを記録、余裕guard3.5GiB/追加0.875GiB/所有2.75GiBで超過前停止。各job timeoutは処理deadline以内。

NN/backend追加、持ち時間adapter、対戦、学習、PV/FPU/solver/TT/別BFS最適化なし。今回のparity実装を一括棋力改善として採用しない。pause/異常で自己PGIDだけ停止・waitしlog保持、共有/他者kill0。全child/server/Chrome/port終了確認を提出。旧失敗/未知owner/DB/必要evidence削除0。

開始ready/show目標/.10後に.10claim。自.5は統括限定受入れnotesを根拠に本人close可（原runH1のみ、shortgate不成立保持）。.7は候補採用保留で独立正しさ検証待ちin_progress、closeしない。目標/.1/他者issue変更禁止。終了は書込み停止・process回収、pause確認/backup後report --to coordinator --issue quoridor-4lc、.10受入れ待ち。重大な未完了やgate不一致を成功に置換しない。
