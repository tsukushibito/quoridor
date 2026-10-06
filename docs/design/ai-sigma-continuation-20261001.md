# NNUE研究・現在の実行許可

2026-10-06更新。**固定チームの研究枠は終了し、現在はユーザーが指定した探索高速化と公開100万行GPU学習をタスクとして配分する。** ユーザーが316・317の引渡し後に解体する方針を選び、`quoridor-1gj`で実施した。残予算や過去の契約から次の実験を自動開始しない。

## 現在のタスク許可

ユーザーの明示指示で `quoridor-4lc.318` の独立保存セッションを作成する。初回は代表的な実NNUE探索のprofile、永続TTの実効性、探索意味を変えない最大1処理最適化を対象とする。[担当契約](../../research-data/ai-sigma/search-optimization/task.md)が編集境界・配分・停止・検証を定める。Rootが採用とGit統合を担当する。

CPU2 logical/RAM2GiB/GPU0、compile・tests・profile累計600秒/各job120秒、新保存96MiB inclusiveを初回配分とし、既存の全保持12GiBとUNKNOWNを維持する。初回の成果又は停止条件で区切り、重要な探索設計・方策・枝刈り・モデル変更はRoot経由で人間が選ぶ。このタスクは全体の新しい時間枠や学習・公開データ取得を許可しない。

学習側 `quoridor-4lc.319` は、ユーザーの「その方針で学習セッションに作業させて」により待機を解除する。公開全43ファイル全域から訓練100万行・validation5万行・最終評価5万行を抽出し、不正入力と終了理由不明z0を別理由で除外する。元観測・反転コピーは同分割、別観測の同盤面は許容する。epoch shuffle・GPU本学習・詳細曲線・凍結後一巡評価と、省容量供給を[担当契約](../../research-data/ai-sigma/public-million-learning/task.md)で配分する。公開game/history欠測と旧開封済み入力露出を保持し、100万行を100万種類や独立gameへ読み替えない。

初回CPU2logical/RAM4GiB/VRAM6GiB、新保存768MiB inclusive、取得・変換7200秒、compile/tests600秒、GPU全job費3600秒、最終CPU評価300秒。旧保持12GiB/UNKNOWN128MiBを維持し、終了済みタスクの未使用future保存予約をRootが前向き移譲してfresh coverageを束縛する。旧費・失敗・GPU残量は変更しない。探索318との共有buildと性能計時を調整し、重要なbatch/モデル等の変更は人間判断へ戻す。

独立review後、ユーザーはoriginal-onlyでT100万/V5万/E5万を新規抽出するv2を明示選択した。元のmixed corpus・規則・SHA・費を保持し、新43blob取得系列に最大2,163,752,072Bを追加配分する。二系列合算最大4,327,504,144B、時間・768MiB保存・GPU枠はreset/増額しない。新peak forecastと計測slot成立後に既担当が再処理する。naiveLRの合法性を元盤面・コピーzの妥当性へ読み替えず、導入修正を同reviewerへ戻す。

## 終了した枠と証拠

frame24/extension25の元の開始は2026-10-06 00:08:46 UTC、連続延長の予定終了は04:08:46 UTC。ユーザーの解体指示により予定時刻を待たず終了した。学習310・描画315・提案316・TT計測317は有限引渡し済み。

- 運用は02:00:20 UTCにscheduler/monitorの正確な二つのidentity不在、ownednull、Supervisor idleを確認した。[停止証拠](../../research-data/ai-sigma/frame24-steward/1gj-terminal-runtime-stop-v1.json)。
- 最終研究保存はGit `6e8d4ab5ac1a3305eff66e4c5b72dd36bfb06b28`。[統括の停止引渡し](../../research-data/ai-sigma/frame24-coordinator/final-stopped-coordinator-handoff.md)。
- 全体の旧期限、失敗、未確認費は元記録で保持する。ユーザー終了を期限遵守・全host停止・最高棋力達成へ読み替えない。

## 残資源と未配分

旧範囲はCPU合計4logical/RAM8GiB/保存12GiB/GPU VRAM6GiBだった。新GPU学習3600秒の消費13.493288946秒・残3586.506711054秒という最終点、旧GPU7200秒残量UNKNOWNと保管UNKNOWN128MiBを保持する。[資源引渡し](../../research-data/ai-sigma/frame24-steward/1gj-final-resource-handoff-v1.json)。残量は追加実験の許可や使う義務を意味しない。保存・過去費をreset/refundしない。

316の全域distinct censusは単独の必須工程にせず、319の全域抽出・資格と実subset多様性記録へ接続する。百万種類を保証する学習、旧CUDA4000step追加比較、MPC校正は未配分。TT実NNUE性能は上記探索高速化タスクの範囲で調べる。現状と比較案は[現在計画](../research-findings.md)へ一本化する。

## 次の実行

人間が重要な方針を選び、RootがBeads課題・目的・単独writer・作業場所・実資源・停止条件・検証を明示して担当へ依頼する。[タスク型研究](ai-research-team.md)と[ジョブ運用](../development/research-jobs.md)を使う。固定ロール、role registry、定期LLM監督、枠終了時の全役起床は使わない。

本書や過去の許可枠を読むだけでは研究を再開しない。学習・データ取得・対局などの新しい実行は次タスクの明示範囲に従う。モデル・入力・検証データ・共有DB・使用中worktreeは保持する。
