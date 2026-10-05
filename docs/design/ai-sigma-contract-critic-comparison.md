# SIGMA-COMPARE-CRITIC / 試行1 / 契約版1

Beads子issue quoridor-4lc.4、目標issue quoridor-4lc。担当 critic / 01a0f31d-8227-7e03-a7e6-915b4918c11b。報告先 coordinator / 01a0f31b-3409-75f2-a30e-453a50484f94。
目標契約 docs/design/ai-sigma-research-goal.md 版1を全文読み継承する。共通/critic指示、AGENTS、チーム設計、AI設計§8/14.4/14.5、storage policy、handoffも確認。既存ユーザーの自律開始権限による実依頼、準備試験限定の旧契約を置換。再委譲/追加サブエージェント0。
作業場所 /workspaces/quoridor/.worktree/ai-sigma / codex/ai-sigma。唯一の書込み docs/reports/ai-sigma-critic-comparison.md。ソース/他担当文書/registry/モデル/依存/lockfile/主checkout/UI/描画/M2を編集しない。自分の子issueだけclaim、目標や起動検証.1の担当を変えない。
予算は起動30分以内、1CPU/1GiB/32MiB、GPU0。短い既存Python/Nodeのメモリ内確認と限定一次資料読取を許可。モデル/clone/環境取得、build/性能測定/対戦/学習は対象外。
全体開始UTC 2026-09-30T17:17:58.145139+00:00、締切UTC 2026-10-01T01:17:58.145139+00:00（JST10:17:58）。17:39UTC時点残り約7時間39分。全体4CPU/8GiB/12GiB、新規学習GPU累積2時間以下。正式計算/モデル/学習実績は初期hypothesisで0、steward集計待ち。今回同時LLMは統括+steward+criticの最大3。計算は読取各1CPU/1GiB以内。大きい取得前の容量点検はsteward。

入力: docs/reports/ai-sigma-hypothesis-initial.md、SHA256 8b4938e6bd1774a5313f808f8c5c0de3a67618c00cc63a4cd6efd404fde9a032、quoridor-4lc.2。目標契約と移入hashは /workspaces/quoridor/.artifacts/research-team/sigma-launch/launch.json。現HEAD 1482df8da6dd91c95db211aeaa914af775b2bc76、HEADだけで未コミット内容は確定しない。
参照Sigma候補commit 751186344fc52ad0c29bc65922e62c6fa915f006。原報告を証拠/仮説として扱い、重要な比較条件を一次コードで独立照合する。固定URL/hashと現ローカルinput hashを残す。15ファイルを全再調査する必要はなく、規約/特徴Action/P2・jump/CPU/Web/native違いの重要部分に絞る。性能改善、solverバグ、モデル配布可能を原報告や合意だけで確定しない。

問い1: 目標の同一資源・思考時間比較を成立させる最小参照経路は何か。
統括案は固定Web NN-MCTS+ONNXをブラウザ参照とし、ORT numThreads1/GPUなし/先読みなし、C++ tournament+CPU torchをnative候補として扱う。native/Webのsolver/TT/FPU等を勝手に同一視しない。機能を弱めず、単一CPU化・同実時間adapterという目的の必要差分だけを許し、その版/hashと限定した結論を固定する。別のnative経路がより再現可能なら費用/同等性の根拠を付けて提案する。
Sigmaの3回目反復禁止/200ply規約とRust標準規約の差を、内部探索まで整合させるadapter案を比較する。rootで不正手を拒否するだけでは不足。製品標準ルールは変更しない。どのhistory情報が必要か、合法集合/P2 encoding/value視点の事前parity fixture、時間範囲（root expansion/features/inference/adapter/finish）とdeadline超過扱いを明示する。
持ち時間はlatency測定前なので未固定。候補0.1/0.5/1秒を仮案とし、勝敗を見る前に単一CPUの両者latency・終了処理の分位/超過上限から1条件を決める手順を提案。simulation一致は分析だけ。探索threadだけでなくtorch/ORT/BLAS/CPU affinity/対局並列の制限と実観測を要求する。

問い2: 結果前に固定可能で予算に収まる非劣性判定は何か。
統括案: score=(W+0.5D)/N、許容差5ポイント、独立開始手順の先後ペアを単位、片側95%下限>0.45。native/browserは別に判定。paired相関と選択/optional stoppingに対処した統計方式、固定holdout局面/seed/temperature/最大手数/反復/timeout/無効対局の扱い、事前固定の標本数・停止規則を提案。200gameを精度保証にしない。必要標本/持ち時間が今回残枠に入らないなら探索的試験と達成認定を分け、未達を明記する。nやCI方式を対戦後都合よく変えない。局面が決定的で複製だけなら独立サンプルと数えない。

問い3: H1の安価な判別計測に進めるか。
原B03局面/192 sims/seed1979/512 nodes/depth24を維持対照に、合法手・壁距離・evaluate・transition・select・確保等の排他的時間/呼出し回数を計測する案を批判。inclusive時間の二重加算、instrumentation overhead、3局面への偏り、cap-hit、固定seed/tie orderを確認。H1の予測は合法手/BFSが展開時間の半分以上、不支持は20%未満、間は判別不足。割合の分母とexclusive/inclusive分類を定義して提案。結果に応じて固定queue等の1要因試作を選ぶが、今回criticは実装しない。先に同一条件の未instrumented baselineを保存する。可能なら小さくholdout fixtureを増やす案を示す。

受入れ: 独立照合の支持/不支持/保留、比較条件案と不足、事前統計案と予算可否、H1計測go/no-go/必要修正をhandoff項目に沿って報告。今回の受入れは方法・調査のみ、棋力/速度達成ではない。モデルSHA256/graph/provenance、実thread数やOS競合、同時間対戦は未実行として残す。
開始と送信直前にBeads wrapperでready、目標と自子issue show。pauseで配送/実行停止。短い処理はremaining以内timeout、自己PID/終了状態を確認し他者停止なし。書込み停止後backup sync、UV_NO_SYNC=1 UV_OFFLINE=1 PYTHONDONTWRITEBYTECODE=1 bash /workspaces/quoridor/scripts/dev/research-team.sh report --to coordinator --issue quoridor-4lc --body-file /workspaces/quoridor/.worktree/ai-sigma/docs/reports/ai-sigma-critic-comparison.md。
状態・担当はBeadsのみ。報告後受入れ待ちはin_progress、統括受入れ後に本人close、目標closeしない。

追加入力（同契約版1、配送前追記）: docs/reports/ai-sigma-steward-initial.md / quoridor-4lc.3 / SHA256 52b8d53b07cf725f1b53510048abfd0c4d4d13b03461f0c814e16695cb4ff5a5。stewardは書込み/自己処理停止、現在idle。統括がbridge依存のmain流出を再実行確認。並行experiment子issue quoridor-4lc.5は依存隔離とB0基準/profilingのみ、速度最適化・モデル・対戦は未配分。唯一のソースwriterはexperiment。criticは読取inputをhash化し、途中でprofiling変更があれば基準hash/HEAD入力との違いを記録して、読んだ版を確定する。実行窓のCPU競合を避け、criticの短い確認はCPU0 affinity、build/性能jobを開始しない。hypothesis初期のCPU/RAMは解放済み。今後同時LLMは統括+critic+experimentまで。
