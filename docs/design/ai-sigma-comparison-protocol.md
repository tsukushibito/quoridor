# Sigma比較の現行方法

## 人間選択の三者比較（374、2026-10-12）

現在選択された比較はSigma、固定D、単独BEST43 NNUEの三pairingである。NNUEは勝敗zの予測を目的とするモデルで、Dを出力へ加える補正器やD＋NNUE混合ではない。既存の標準化distance head入力とT-only scaleは保持し、final tanh・output bypass OFF、重み046fe/BEST43・descriptor46ec/evaluator96a5を固定する。Sigmaは保持ONNX d790と既存policy/value/PUCT設定、Dは既資格の固定評価を使う。新しい学習・teacher・重み・defaultは選択していない。

固定予定は128 opening families、先後交換384 pairs／768 games、各pairing256 slots。100msの応答時計と5ms reserve、goal-first/true threefold、full history、200ply未決着UNKNOWNを保持する。Alpha側のcontinuation/static orderingは両方OFFとし、Sigmaの即時authority receiptと終了drainを区別する。保存358 traceから結果前に選んだ78 parentsへの234 single proposalsは別の診断分母で、欠けた18 milestonesを補充しない。診断は得意・不得意の仮説を作る有限比較で、他engineの一致やD6値を最適手の真実としない。

旧347のSigma cost qualificationは期限切れであり、新しいcurrent Build／backend／model／library／資源tupleへの一回の64 requestsを先に行う。32 untimed＝16 warm＋16 measure、32 timedの二phaseと既存4×＋2ms計算、実launchから一度固定する24h windowを用いる。古い証拠の期限更新や静的source proofによるempirical PASS代用をしない。失敗・不足・期限切れではunsupportedのまま保存し、自動再qualificationや別の対局campaignを追加しない。

詳細の正本は一つのlossless archive、result/manifestはcompact censusとexact referencesとする。missing/torn/不一致appendでは利用できるotherwise-unrecoverable outcomeだけをbounded failure evidenceへ保持し、canonical successを作らない。初期化の元error object、既知の最初の理由、返ったarchive/publication errorsを保持する。変更境界のレビューを受けた[現役Source採用](../../research-data/ai-sigma/three-engine-comparison374/source-adoption-v1.json)はsource-onlyであり、actual Build/private／backend／library／cost／gamesの成功を証明しない。各工程の実STOP・returned/persisted facts・UNKNOWN・費用を分ける。

家族単位の結果と時間／エラー／UNKNOWN、保存された有限特徴・decision factsから改善方針を検討する。128 familiesや選択済みanalysis settingsを結果後に変えず、IID・Elo・母集団棋力・唯一原因を主張しない。既存の研究入口・正本と[inclusive772MiB支持](../../research-data/ai-sigma/three-engine-comparison374/support-v2.json)を用い、shared target・実reader/clock intervalを保護する。終了後の一般化保守377は実374 STOP・受入れ後に別途行い、今回の測定設定を遡及変更しない。

[目標](ai-sigma-research-goal.md)と[実行枠](ai-sigma-continuation-20261001.md)を継承する。2026-10-02、契約改善指示により機能診断・探索的棋力評価・正式認定を分離した。過去の計画・標本・条件はGit/実行記録で参照し、変更していない。

## 参照と共通条件

固定Sigma-Web commit `751186344fc52ad0c29bc65922e62c6fa915f006`、9x9/10壁、NN-MCTS、`best.onnx`、C_PUCT1/FPU.2/temp0、ORT WASM推論1スレッドを参照する。root noise/先読み/analysisなし。参照原版の機能を弱めた別設定へ無断で置き換えない。モデル/依存/sourceの実版はrunから参照する。

最初のnative/localはRust-native対ローカルSigma-Webであり、Sigma C++ nativeの成績ではない。Rust-Wasm対Sigma-Webは別に測る。

2026-10-07の最新の人間採択により、今後の研究self-play・棋力/arena評価は共通の **standard-2p基本則＋3回同一局面で自動draw** を使う。これは出版社規則に追加した明示的な裁定慣行である。[出版社の英語規則](https://export.gigamic.com/wp-content/uploads/2021/01/INS-RULES-QUORIDOR_10-2016.pdf)は前後移動と対岸goal到達による勝利を定め、3回反復drawを指定していない。製品UIの出版社standardモードはこの研究採択によって変更しない。

1. goal到達のWIN/LOSSを反復と運用上限より先に判定する。
2. 初期局面を1回と数え、同じ局面の3回目をdrawとする。出現は連続でなくてよい。両pawn位置、H/V壁配置、両残壁数、side-to-moveを局面の正本identityに含める。実対局履歴と現在の探索pathを重複rootなしで数え、3回目へ入る手は合法、次stateはterminal draw0とする。旧RuleAの3回目pawn手禁止filterを残さない。
3. total200pliesは運用の収集上限である。goal/真の反復drawで未決着ならunfinished/censored/UNKNOWNで、draw/z0/terminal eval0/ProvenDrawに変換しない。境界goalと3回反復は真の結果として優先する。error/cancel/late/no completedも未完了である。standard非goalで合法手なしの不正/未対応stateに旧RuleA drawを継承しない。距離による上限採点や罰則drawを追加しない。
4. 完了したself-playだけWIN+1/DRAW0/LOSS−1を正確なSTM視点へ写す。上限/未完了はpositions/policy/endcauseを記録しても確定outcome labelを入れない。旧公開corpus z0の終了由来不明はそのままで、新裁定のprovenanceとして格上げしない。323pause・生成/fit/export/label開封の保留は解除しない。
5. 評価では予定denominator、complete pairs/draws/unknowns、bounds/completion rateと規約版を保存する。

NNUE/D/Sigmaの審判だけでなく内部αβ/PVS・MCTS・solverにもこの裁定を適用する。canonical moves/features/math/contextを共有し、config/context/TT namespace/run receiptにrulesetを明示する。反復identityとTTのhistory/ply identityを混同せず、history依存drawをboard-only普遍値としてcacheしない。terminal drawはNN値呼出しを通さない。head/FT/model/features/float/order/pruningは変えない。暫定の研究official-only入口を恒常互換shimとして増やさず、実利用する製品standard機能は維持する。

旧327の3勝13敗/4勝12敗、332の敗戦分析、331既存4機能windowは使用時のRuleAに束縛された証拠として保持する。新規約の結果へ読み替えず、cohortを混合しない。未開始331比較は両engineで同じ新規約・新source/private版を使い、変更legal/history/terminal/TT/caller境界だけを確認する。first/second非terminal、third合法draw、stock/side/key区別、root+path/nonconsecutive、goal優先、undo/cancel/error/reentrant、200未決着UNKNOWNと境界反復drawを対象にする。native入力/head数値の不変範囲は再用し、旧D/Torch/book/全suiteを一律再実行しない。既存prefixbookは再選定せず新規約の合法性を検証して使う。新規約D再比較は別の全費用付き提案でありSigmaの必須gateではない。

直前の「self-play RuleA/評価official-only」は今後の研究には適用しない。既に始まったimmutable job/readersは使用した規約のまま自然STOP・回収し、次entryから最新採択に移行する。過去label/結果/費/binding/UNKNOWNは不変である。

同じPC・指定論理CPU・推論1スレッド・GPU推論なしを使い、測定中の重い研究jobを停止する。入力供給可能時のt0から合法応答の配送完了までを測る。モデルload/warmup、共通審判処理は区別して記録する。現在の500msとearly-sealの数値は既存試験の条件で、製品の一般上限ではない。

旧探索の停止・後始末を次の相手の時間へ無条件に課金しない。各engineの配送前後の時間とCPU費用を原因側へ帰属させ、正式run前に同じ実効予算となる時計/資源課金を確認する。遅延結果や旧局面応答は採用せず、終了・所有・processの回収を確認する。

## 機能診断と探索的対局

エンジン/モデルの識別、合法性/入力変換、共通時計、資源上限と停止を最小経路で確認して、固定goldenや少数局から進められる。最大run/局数/時間を総予算内で配分し、修正版はGit版/runを分けて反復できる。通常診断へ正式認定の標本数・全fault検証・独自issuer/proof形式の完備を一律要求しない。

実行入口はrun種類・Git版・設定・入力・予算・停止を明示する。診断/正式の取り違えは拒否するが、独自認可payloadの整形をAI性能の不成立理由にしない。既runnerがその形式を要求する場合、Rootと担当が最小controlを使うか、所有範囲でrunner外の実行管理へ分離する。pause・資源・所有の制御を迂回する許可ではない。

探索的対局はW/D/L、得点率、先後・局面・誤り/timeout・時間の分布を報告し、改良や仮説選定に使う。精度不足は明記するが、正式な同等証明ができないだけで診断を禁止しない。探索用局面/結果を後から正式holdoutへ格上げしない。

## 正式な同等判定

固定候補と参照の版/モデル/探索設定/規約/資源/時間/局面抽出/seed/先後ペア/標本数/集計/エラー分類/再試行/終了条件を結果前に登録する。合法開始手順の先後ペアを単位にし、同じholdoutで候補を選んだ結果を選定後の独立認定へ流用しない。時間不足や標本未完了は未立証とする。

旧採択の保守方式は片側95%下限 `max(0, mean_pair_score - sqrt(log(20)/(2*m))) > .45`。平均.5付近では約600ペア/環境が必要で、少数の研究枠での達成を保証しない。この方式で事前登録済みの計画・結果は維持する。

新しい正式計画ではRootと必要な独立レビュー担当が推定対象・許容差・信頼水準・必要精度/検出力・標本数・最悪所要時間を先に見積もり、利用可能な予算と両立する方法を結果前に選ぶ。予算不足なら正式認定は将来計画として分け、現在は診断/改善測定を行う。既に見た結果に都合よく方法や判定を緩めない。最終native/localとbrowserの主張は独立根拠に基づき区別して受け入れる。

## 性能の原因判別

固定探索量での速度と固定実時間での棋力を区別する。重複区間を二重計上せず、warmup/steady・wrapper全体/内部APIの費用を区別する。計測器のoverheadや誤差はその主張への影響と感度を報告し、境界値だけで全ての診断を止めない。数値schemaと安い機能確認を先に行い、重大な因果主張に必要な独立確認だけ依頼する。

## 追加pairing：Sigma対固定D

人間が承認した追加16slotsは[336契約](../../research-data/ai-sigma/arena-evaluation/sigma-distance336/task.md)に従い、331 NNUE対Sigmaの実STOP・回収後、同担当で別pairingとして実施する。新threefold規約・保持book・clock・model・source/versionを結果前に固定し、使用済み331出力と新出力を共に保存予測へ含める。331 matches64MiBの再利用を容量支持とみなさない。旧327 NNUE対DはRuleA-onlyであり、新rulesのNNUE対D追加対局はこの承認に含まれない。
