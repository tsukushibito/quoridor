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

## 評価処理最適化の継続（2026-10-06ユーザー依頼）

初回scopeは完了し、sort変更は不採用。過去のclose・測定・失敗・UNKNOWN・sourceを保持し、同じissue/sessionをこの継続だけ再開する。現在有効な条件・配分は[evaluation-next-phase.json](evaluation-next-phase.json)。原600秒から学習へ120秒を移譲した後の探索保持480秒内で、既161.233360549秒＋旧source support上界90＋初回保存closure上界30＋新phase全attempt180＝461.233360549秒を保守予約する。旧費の減額・cap reset・親資源増加はない。source整形/制御30、build/tests/oracle90、plain比較60の上界、最大2job/各120、8m新forward上界。既CPU0,1/RAM2GiB/GPU0/保存96MiBを維持し、初回source・binary・evidenceと新増分までinclusive forecastする。

学習担当の同BESTに対する明示Scalar/Simd FT・full/delta・make/unmake資格の成功、対象source/weights/config/cache/scale/ELFのSHA付き引渡しと実writer/child停止が開始条件。最終sealed testや別の学習追試の終了は待たない。これらの引渡し前は保存profileの分析と計画まで、評価source変更・build/forward/計時は開始しない。学習の必要sourceをWTへ整合する際は初回8source/patch/evidenceを先に保全し、同じsource版・同じ凍結重みのbaseline/candidateを比較する。拒否したsortを次candidateへ混ぜず、別namespaceで記録する。Root ACKだけを追加gateにしない。

第一候補はResidualModel::evaluateの各推論Vec確保・コピーの除去又はscratch再用。実callerの支配費から一つの同算術candidateを選び、計算順序・丸め・距離尺度・活性化とモデル形式を保つ。SIMD命令導入が計算順序やFMAを変える場合、量子化/精度/特徴/モデル変更が必要な場合は設計判断をRootへ戻す。FTの既SIMD資格と残差head高速化は区別する。検索全仕事と推論単体の両方を記録し、同depth/node・値bits/Action/PV・親履歴復帰を確認する。交替plain比較を主とし、profile時計の倍率を速度利益にしない。

共有targetの唯一writer・fresh directed保存/実物理・モデル等bindingを担当が入口で確認し、numeric/arena時計とは非重複。START/STOPとimmutable準備完了を学習・arena・Rootへ直接引渡す。超過見込や資格不一致で止め、失敗や不支持を保持する。main採用はRootの受入れと必要な独立確認後のみ。新研究条件・再帰委譲・追加fit/game/公開取得・旧資産削除は配分しない。

## ユーザー不在中の自律継続（2026-10-06）

最新のユーザー指示は「時間枠や計算上限は設けないで。進められるだけ進めて。明日進捗確認するときに状況を見て停止をリクエストする」。[autonomous-processing-contract.json](autonomous-processing-contract.json)のend/compute endと時間・job数・介入数・forward数上限はnullで、Rootが仮設定した4時間/30分等を以後の停止条件に使わない。完了済み旧600/保持480/移譲120/NEW90等の原費・失敗・消費slot・UNKNOWNは履歴として不変更で、現在の無期限許可を旧unusedやrefund/resetと呼ばない。候補・順位・次判断は[研究知見](../../../docs/research-findings.md#探索担当の自律継続と検証優先度)を正本とする。

許可した同意味処理最適化は実結果で候補を更新し、ユーザーの停止指示まで進められるだけ進める。各jobの計測入力と問いは有限に固定し、完了後に次の有力介入へ進む。無期限許可を根拠のない同候補の無限反復にしない。1候補の不支持やRootのmain受入れ待ちを全体停止条件にせず、停止版と必要証拠を引き渡し、別の許可済みWT作業へ進む。原則・速度・棋力の採用を混同しない。CPU/RAM/GPU/保存と一人のwriter・重要設計の境界は維持する。具体資源不足・不一致は該当工程のみ停止して報告、重要な意味変更は提案を残して人間判断を待つ。新取得/依存/学習/対局/資産削除の許可は増やさない。

job configのend_at/notify_until/max_runtime_secondsをnullにし、許可を変更せず期限なしで動作するcanonical research-jobを使う。既存実行中jobの凍結configは書換えず実STOPを保存し、以降のjobで撤去済み上限を使わない。pause/owner/取消・bounded log・exact cleanup・一度の完了通知は維持し、計算待ちはIdle/完了イベントで進める。ネットワーク・RPC・lock・cleanupの応答timeoutは作業上限とは別に維持できる。個別作業の細かな追加計測、定期LLM監視、繰返しglobal/target容量scanはしない。明日の進捗確認自体を自動stopとせず、実際の停止指示で止める。

## 一時確保を避け、事前確保バッファを参照して使う方針

ユーザーは「避けたいのは一時ヒープ確保で、事前確保ヒープの使用は良い」と明示した。ヒープ回避を大きな値の値渡し化・コピーや全heap storage排除と混同しない。by-value WallMaps案は確保除去と保存/ABI変更を同時に含み、その速度退行を純粋な一時確保回避の効果とは扱わない。compact pointer版の改善も単独のコピー原因証明ではない。

次の優先処理候補はcanonical算術を基準に、実search/session/workerで適切なサイズの入力scratchを一度確保し、各evaluateでReLU/denseを一度だけ埋め、連続sliceを参照して同じscalar内積を行う構成。大きなmap/accumulatorは安全な参照で扱い、不要なpayload移動・全buffer初期化・hidden rowごとの入力再計算・所有管理を増やさない。全accepted topology、親/history復元、reentrant/nonalias/error/cancel保証を保ち、global mutable・unsafe未初期化・巨大な深さ別stackを導入しない。現役standalone callerも正しく維持し、互換性だけの旧経路や探索器コピーを残さない。

比較は一時確保のあるcanonicalとの最小同算術差分に限定し、過去のFT/TT/map複合候補を混ぜない。initと通常のalloc数、独立bit/reference/実caller/parent/error/cancelとplain wholeを確認する。事前確保ヒープ利用は許可済みだが高速化を先取りしない。先のstack packing patch/全negative証拠は保存して代替案とし、新buildは現163MiBのinclusive成立または具体前向き配分後、数値/公平clockは学習の実STOP後のquiet slotで行う。
