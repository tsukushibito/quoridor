# Rust探索高速化の初回依頼

Beads: `quoridor-4lc.318`。2026-10-06のユーザー指示による新しいタスク許可。固定チーム・過去frame・残予算を再開しない。

## 目的と初回の区切り

代表的な実NNUE探索の支配費を特定し、永続TTと既存orderingの実効性を確認する。そこから探索の意味を変えない処理最適化を最大1件実装・比較して、結果と次の選択をRootへ渡す。小規模測定の不支持を探索高速化全体の否定にしない。

最初に必要な正本を参照する: mainの `docs/research-findings.md`、`docs/design/ai-research-team.md`、`docs/design/ai-nnue-optimization-agenda.md`、`docs/development/research-jobs.md`。この依頼は常設ロールではない。

## 担当と編集境界

- 独立保存セッションがこのissueを所有し、実際のcwdを確認する。作業場所は `/workspaces/quoridor/.worktree/search-optimization`、基準main `362feb0542bb5d7ffaa9e31fd8fd48e825bcb248`。
- writerは本人一人。`crates/quoridor-ai`、`quoridor-core`、`quoridor-nnue`、`quoridor-runner`のprofile・同意味処理最適化と対応testsを対象にする。必要最小限の現役入口へ計測を接続し、実験専用の探索器コピーを恒久化しない。
- mainはRootのみwriter・Git index/commit統合担当。本人は全worktreeのstage/commit/ref/merge操作を行わない。source停止後に明示path/SHA・差分・必要証拠を渡し、Rootが採否・保存を行う。
- mainの既存モデル・checkpoint・保存入力・環境はread-onlyで再用する。`research-paths.json`と保存manifestで参照し、コピー・移動・削除・モデル変更をしない。疎worktreeにない文書と科学証拠はmainから必要箇所を読む。
- 追加セッション・再帰的委譲は未配分。並行できる独立課題を見つけたらRootへ提案する。

## 計測と改修

1. 固定する既存NNUE重み・入力・合法履歴・ソース版を記録する。既存の真正局面から序盤・壁が多い中盤・接触/jump・終盤を含む小さい代表集合を結果前に選び、選定理由を残す。距離Dを対照として使えるがDだけを実NNUEの性能証拠にしない。
2. whole-searchと、合法手・距離map・特徴/accumulator・評価・TT key/history/hash/probe・sort・PVS再探索の費用を測る。既存telemetryを先に使い、必要なら利用可能なprofiler又は軽量計測を追加する。計測overheadを確認し、重複時計を合算しない。取得不能な費用はUNKNOWNとする。
3. 永続TTのcold/warmを、実際に合法手が進む履歴付き系列で比較する。raw hitだけでなく有効bound/cutoff、ordering-only、key生成費、保持メモリ、深度・nodes・全時間を確認する。TTのためにhistory/plyやモデル・規則namespaceを省略しない。
4. 実測支配費から最大1の処理最適化を選ぶ。重複した合法手生成、不要な特徴更新、scratch/allocation、計算共有などが候補。重要な意味変更を含むなら実装を始めず次節の判断を依頼する。
5. 同入力・同モデル・同depth/node条件で全結果と親復帰を確認し、baseline/candidateの順序を交替して全費を比較する。対応する独立oracleと限定testsを使い、変更したRustをrustfmt/限定Clippy等で仕上げる。短時間比率を一般倍率・MCTS生成倍率・棋力へ拡張しない。Rootの独立採用レビュー前にmainへ採用しない。

## Root経由で人間が決めること

MPC/LMR等の選択的枝刈り、探索方針・深さの変更、学習した方策や新しいordering方式、評価器/特徴/教師/学習、近似TT・規則・履歴意味、並列探索の導入は重要設計としてRootへ戻す。観測事実、競合案、結果で変わる判断、精度/戦術リスク、実装・検証・全工程費と推奨案を簡潔に示す。Rootから人間へ判断を仰ぎ、返答前に該当する設計を実施しない。影響しないprofile・通常修復は継続できる。

## 資源・停止・報告

- 初回配分はCPU最大2 logical、RAM process-family合計2GiB、GPU0。新しい実計算はcompile/tests/profileを含め累計600秒、各job120秒。モデルforwardも実仕事量として記録する。超過しそうなら終了処理の余裕を残して止め、必要な追加量と理由をRootへ渡す。
- worktree・code・build増分・ログ・raw/圧縮証拠・Git/temp込みの新保存は96MiB。既存全保持12GiBとUNKNOWN128MiBは維持する。既存cacheを参照できるが、増分は本タスクへ計上する。開始準備のfresh容量観測はmain `.artifacts/search-optimization-launch/storage-before.json`。実計算前に必要領域を加えたcoverageと現物CPU/RAMを確認する。旧unused台帳の全史監査を新タスクの入口に追加しない。
- buildは既存の適切なtarget/依存をoffline/lockedで再用し、新規依存取得・環境更新をしない。既存cacheの利用者とsource/binary対応を確認し、共有cacheの無断削除・競合buildをしない。source調査は実測の物理確認待ちと並行できる。
- 2026-10-06の連携調整: 319のprivate immutable native参照のSHA/size・実caller binding通知後、候補のビルド・限定tests/Clippyだけを最大1job120秒、既累計600秒の残内で固定GPU本fitと並行可。CPU0,1/RAM2GiB/GPU0、共有target唯一writer、同時費は競合ありと記録する。交替binary速度比較・再profileは学習のexact自然STOPまで保留する。ビルドSTOP/childwait/cleanupを320とRootへ直接通知し、320の既配分ソフト検証へ共有targetを引き渡す。Root ACK待ちは追加しない。
- 319基準fitの実STOP後、旧600秒の残446.150198430秒から、凍結sort候補の交替plain比較をONE job最大60秒で配分する。320の新software recovery exactSTOPと319後段数値仕事のSTOP又はno-current/no-next-numeric留保が両方成立してからfresh quiet/admissionで開始する。固定5root・B3817・source/binary SHA・同完成仕事を維持し、失敗の自動反復や追加profile・新モデルを配分しない。実START/STOPは両担当とRootへ直接通知し、受領ACKをgateにしない。
- 初回のprofileと最大1比較、予算到達、ユーザーpause、資産/所有/結果妥当性の未解決、重要設計の判断待ちで該当作業を区切る。旧期限・費・失敗は変更しない。長jobは既存背景jobのbounded log/guardian/完了通知を使い、計算待ちでLLM turnを保持しない。
- 初報でclaim/actual cwd/選んだモデル・代表群・実測開始か準備中かを区別する。その後は支配費、実改善、重要判断、障害の節目で報告し、定型進捗turnを作らない。
- 完了時はsource/process停止、子回収、方法・結果・不確実性・費、変更path/SHA、再現command、残課題・次の判断をissueに残してbackupする。必要証拠はmainの本タスク専用保存先へRootが統合する。
- Rootの保存threadは `01a0f2e9-357d-7ef3-a2fe-b16f80accda5`、報告宛先のRoot所有issueは `quoridor-4lc`。`research-session.sh send`で必要な節目だけ直接報告できる。自分のissueを宛先として送らない。RPC不明時は再送を反復せずissueへ残す。
