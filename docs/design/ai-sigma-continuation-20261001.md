# NNUE研究・現在の実行許可

2026-10-06更新。**固定チームの研究枠は終了し、現在は新しい研究実行を配分していない。** ユーザーが316・317の引渡し後に解体する方針を選び、`quoridor-1gj`で実施した。残予算や過去の契約から次の実験を自動開始しない。

## 終了した枠と証拠

frame24/extension25の元の開始は2026-10-06 00:08:46 UTC、連続延長の予定終了は04:08:46 UTC。ユーザーの解体指示により予定時刻を待たず終了した。学習310・描画315・提案316・TT計測317は有限引渡し済み。

- 運用は02:00:20 UTCにscheduler/monitorの正確な二つのidentity不在、ownednull、Supervisor idleを確認した。[停止証拠](../../research-data/ai-sigma/frame24-steward/1gj-terminal-runtime-stop-v1.json)。
- 最終研究保存はGit `6e8d4ab5ac1a3305eff66e4c5b72dd36bfb06b28`。[統括の停止引渡し](../../research-data/ai-sigma/frame24-coordinator/final-stopped-coordinator-handoff.md)。
- 全体の旧期限、失敗、未確認費は元記録で保持する。ユーザー終了を期限遵守・全host停止・最高棋力達成へ読み替えない。

## 残資源と未配分

旧範囲はCPU合計4logical/RAM8GiB/保存12GiB/GPU VRAM6GiBだった。新GPU学習3600秒の消費13.493288946秒・残3586.506711054秒という最終点、旧GPU7200秒残量UNKNOWNと保管UNKNOWN128MiBを保持する。[資源引渡し](../../research-data/ai-sigma/frame24-steward/1gj-final-resource-handoff-v1.json)。残量は追加実験の許可や使う義務を意味しない。保存・過去費をreset/refundしない。

316の公開43ファイル全体の多様性調査、百万種類規模の学習、CUDA4000step追加比較、TT実NNUE性能、MPC校正は未配分。現状と比較案は[現在計画](../reports/ai-sigma-coordinator-current-priorities.md)へ一本化する。

## 次の実行

人間が重要な方針を選び、RootがBeads課題・目的・単独writer・作業場所・実資源・停止条件・検証を明示して担当へ依頼する。[タスク型研究](ai-research-team.md)と[ジョブ運用](../development/research-jobs.md)を使う。固定ロール、role registry、定期LLM監督、枠終了時の全役起床は使わない。

本書や過去の許可枠を読むだけでは研究を再開しない。学習・データ取得・対局などの新しい実行は次タスクの明示範囲に従う。モデル・入力・検証データ・共有DB・使用中worktreeは保持する。
