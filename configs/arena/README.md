# 棋力評価preset

現役実行入口は `quoridor-runner arena --config JSON`、book/history・受理時計・pair分母と保存は[runner手順](../../crates/quoridor-runner/README.md)。各runは新outputと実資源/期限を事前固定する。

- `smoke.json`: 人工の一手ゴールprefixからD/D色交換2slot。機能確認用で棋力を判定しない。
- `cancel.json`: pause fileを事前に置いて未開始2slotの取消・UNKNOWN記録を確認する。同じ設定を通常対局へ流用しない。
- `distance-control-100ms.json` / `distance-control-500ms.json`: 初期盤面1pairの調整用D/D。同時間比較のsource/evaluator SHAを束縛する。主評価book・高精度の棋力推定ではない。

時計は `strict_unknown`。返却後の全履歴合法性検査を含む受理が期限を超えればunknownにする。forfeitへの変更は次run前に固定し、過去のunknownを勝敗へ変えない。モデル比較は同一探索版を使う。Sigmaの同時間callerは現役 `whole_wall_time`/ORT経路を使い、completed-depthは対応しない。presetの存在・ソフト試験PASSは新しい研究runの実行許可ではない。

研究用arena/decisionsは既存のintegration-selected plan/configでfamily/matchup ID、engine順序/model参照、batch/slot、book全履歴、depth/node/time/reserve/TTを指定する。色交換は全family×matchupの2slot、decisionsは全parent×宣言engineの1slotを保持し、未開始・cap・error・未完了を全予定分母のUNKNOWNから落とさない。Alpha orderingは `arena.disable_continuation_static_ordering`（false/省略で現製品factory、trueで継続/static無効）で指定する。Sigmaのbackend/実時計・receipt/drain・library/model identityは別の現役保証で、IDの値からengine種類を推測しない。

保存解析のfamily/ID/matchup数はplanから導く。`bootstrap_resamples`、`bootstrap_seed`、`central_interval`と任意 `linked_examples_limit` は同じ既存解析configの設定であり、固定128/768/三種類のstudyをgeneric codeに埋め込まない。科学許可とnative/software/実caller確認は別で、凍結plan/config/RAWを新設定へ書換えない。authority・未完了・条件付き区間の限界は[runner手順](../../crates/quoridor-runner/README.md#configured-research-plans-and-saved-analysis)を参照する。
