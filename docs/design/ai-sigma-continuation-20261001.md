# NNUE研究・現在の実行許可

2026-10-06更新。**固定チームの研究枠は終了し、現在はユーザーが指定した探索高速化タスクだけを新しく配分した。** ユーザーが316・317の引渡し後に解体する方針を選び、`quoridor-1gj`で実施した。残予算や過去の契約から次の実験を自動開始しない。

## 現在のタスク許可

ユーザーの明示指示で `quoridor-4lc.318` の独立保存セッションを作成する。初回は代表的な実NNUE探索のprofile、永続TTの実効性、探索意味を変えない最大1処理最適化を対象とする。[担当契約](../../research-data/ai-sigma/search-optimization/task.md)が編集境界・配分・停止・検証を定める。Rootが採用とGit統合を担当する。

CPU2 logical/RAM2GiB/GPU0、compile・tests・profile累計600秒/各job120秒、新保存96MiB inclusiveを初回配分とし、既存の全保持12GiBとUNKNOWNを維持する。初回の成果又は停止条件で区切り、重要な探索設計・方策・枝刈り・モデル変更はRoot経由で人間が選ぶ。このタスクは全体の新しい時間枠や学習・公開データ取得を許可しない。

学習側はユーザー指定の `quoridor-4lc.319` で独立保存セッションを作成し、暫定方針の受領とIdle待機だけを許可する。多様性・代表分割・compact供給・GPU本学習・詳細曲線を方向として共有するが、取得・走査・変換・解析・学習等の実行は未配分。定期起床・計算ジョブを作らず、具体の方針・資源・停止・検証をRootから渡すまで待つ。担当と待機状態はBeadsで管理する。

## 終了した枠と証拠

frame24/extension25の元の開始は2026-10-06 00:08:46 UTC、連続延長の予定終了は04:08:46 UTC。ユーザーの解体指示により予定時刻を待たず終了した。学習310・描画315・提案316・TT計測317は有限引渡し済み。

- 運用は02:00:20 UTCにscheduler/monitorの正確な二つのidentity不在、ownednull、Supervisor idleを確認した。[停止証拠](../../research-data/ai-sigma/frame24-steward/1gj-terminal-runtime-stop-v1.json)。
- 最終研究保存はGit `6e8d4ab5ac1a3305eff66e4c5b72dd36bfb06b28`。[統括の停止引渡し](../../research-data/ai-sigma/frame24-coordinator/final-stopped-coordinator-handoff.md)。
- 全体の旧期限、失敗、未確認費は元記録で保持する。ユーザー終了を期限遵守・全host停止・最高棋力達成へ読み替えない。

## 残資源と未配分

旧範囲はCPU合計4logical/RAM8GiB/保存12GiB/GPU VRAM6GiBだった。新GPU学習3600秒の消費13.493288946秒・残3586.506711054秒という最終点、旧GPU7200秒残量UNKNOWNと保管UNKNOWN128MiBを保持する。[資源引渡し](../../research-data/ai-sigma/frame24-steward/1gj-final-resource-handoff-v1.json)。残量は追加実験の許可や使う義務を意味しない。保存・過去費をreset/refundしない。

316の公開43ファイル全体の多様性調査、百万種類規模の学習、CUDA4000step追加比較、MPC校正は未配分。TT実NNUE性能は上記探索高速化タスクの範囲で調べる。現状と比較案は[現在計画](../research-findings.md)へ一本化する。

## 次の実行

人間が重要な方針を選び、RootがBeads課題・目的・単独writer・作業場所・実資源・停止条件・検証を明示して担当へ依頼する。[タスク型研究](ai-research-team.md)と[ジョブ運用](../development/research-jobs.md)を使う。固定ロール、role registry、定期LLM監督、枠終了時の全役起床は使わない。

本書や過去の許可枠を読むだけでは研究を再開しない。学習・データ取得・対局などの新しい実行は次タスクの明示範囲に従う。モデル・入力・検証データ・共有DB・使用中worktreeは保持する。
