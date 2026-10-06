# 棋力評価preset

現役実行入口は `quoridor-runner arena --config JSON`、book/history・受理時計・pair分母と保存は[runner手順](../../crates/quoridor-runner/README.md)。各runは新outputと実資源/期限を事前固定する。

- `smoke.json`: 人工の一手ゴールprefixからD/D色交換2slot。機能確認用で棋力を判定しない。
- `cancel.json`: pause fileを事前に置いて未開始2slotの取消・UNKNOWN記録を確認する。同じ設定を通常対局へ流用しない。
- `distance-control-100ms.json` / `distance-control-500ms.json`: 初期盤面1pairの調整用D/D。同時間比較のsource/evaluator SHAを束縛する。主評価book・高精度の棋力推定ではない。

時計は暫定 `strict_unknown`。返却後の全履歴合法性検査を含む受理が期限を超えればunknownにする。forfeitへの変更は次run前に固定し、過去のunknownを勝敗へ変えない。モデル比較は同一探索版を使う。異なる探索sourceの二版adapterと時限制約付きSigmaは未実装。presetの存在・ソフト試験PASSは新しい研究runの実行許可ではない。
