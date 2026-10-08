# NNUE研究・現在の実行許可

現行の未来資源上限は[2026-10-08資源方針](ai-research-team.md#現行資源方針2026-10-08人間採択)と[typed支持](../../research-data/ai-sigma/execution-resources-20261008.json)。以下の旧hardware/保存枠は各使用時の歴史契約であり、新工程への上限ではない。

2026-10-07の追加承認により、現在の親保存上限は12.5GiB＝13,421,772,800B。旧12GiB配分の予約・資産・失敗費・buildUNKNOWN・UNKNOWN128MiBをすべて保持し、追加512MiBだけを[現行の前向き配分](../../research-data/ai-sigma/execution-autonomy-20261007.json)へ分類した。CPU4/RAM8GiB/VRAM6GiBは不変、原323の学習pauseとnewE/oldopened封印・defaultweightsを維持する。以下の初回配分は履歴であり、新entryのresource proof/科学順序/イベント配分はこの追加承認と既存タスク契約に従う。2026-10-08JSTは人間の確認日で、科学jobの強制STOP期限ではない。

2026-10-07更新。**固定チームの研究枠は終了し、現在はユーザーが指定した探索高速化、公開100万行GPU学習、棋力評価環境の構築をタスクとして配分する。** ユーザーが316・317の引渡し後に解体する方針を選び、`quoridor-1gj`で実施した。残予算や過去の契約から次の実験を自動開始しない。

## 現在のタスク許可

ユーザーの明示指示で `quoridor-4lc.318` の独立保存セッションを作成する。初回は代表的な実NNUE探索のprofile、永続TTの実効性、探索意味を変えない最大1処理最適化を対象とする。[担当契約](../../research-data/ai-sigma/search-optimization/task.md)が編集境界・配分・停止・検証を定める。これは初回の履歴上の担当記述である。現在は[タスク型研究の設計](ai-research-team.md)に従い、実行・統合担当が採用検証とmain/Git統合を担当する。

CPU2 logical/RAM2GiB/GPU0、compile・tests・profile累計600秒/各job120秒、新保存96MiB inclusiveを初回配分とし、既存の全保持12GiBとUNKNOWNを維持する。初回の成果又は停止条件で区切り、重要な探索設計・方策・枝刈り・モデル変更はRoot経由で人間が選ぶ。このタスクは全体の新しい時間枠や学習・公開データ取得を許可しない。

学習側 `quoridor-4lc.319` は、ユーザーの「その方針で学習セッションに作業させて」により待機を解除する。公開全43ファイル全域から訓練100万行・validation5万行・最終評価5万行を抽出し、不正入力と終了理由不明z0を別理由で除外する。元観測・反転コピーは同分割、別観測の同盤面は許容する。epoch shuffle・GPU本学習・詳細曲線・凍結後一巡評価と、省容量供給を[担当契約](../../research-data/ai-sigma/public-million-learning/task.md)で配分する。公開game/history欠測と旧開封済み入力露出を保持し、100万行を100万種類や独立gameへ読み替えない。

初回CPU2logical/RAM4GiB/VRAM6GiB、新保存768MiB inclusive、取得・変換7200秒、compile/tests600秒、GPU全job費3600秒、最終CPU評価300秒。旧保持12GiB/UNKNOWN128MiBを維持し、終了済みタスクの未使用future保存予約をRootが前向き移譲してfresh coverageを束縛する。旧費・失敗・GPU残量は変更しない。探索318との共有buildと性能計時を調整し、重要なbatch/モデル等の変更は人間判断へ戻す。

独立review後、ユーザーはoriginal-onlyでT100万/V5万/E5万を新規抽出するv2を明示選択した。元のmixed corpus・規則・SHA・費を保持し、新43blob取得系列に最大2,163,752,072Bを追加配分する。二系列合算最大4,327,504,144B、時間・768MiB保存・GPU枠はreset/増額しない。新peak forecastと計測slot成立後に既担当が再処理する。naiveLRの合法性を元盤面・コピーzの妥当性へ読み替えず、導入修正を同reviewerへ戻す。

v2の入口チェック未完了後にsubmitが走った制御失敗は取消・回収と実費を保持する。同scope復旧として、確認済み系列1の未使用取得枠から256MiBを系列2へ前向き移譲し、現在のceilingは系列1が1,895,316,616B、系列2が2,432,187,528B、合算上限不変。原cap/費/SHAを上書きせず、検証済み既blobの直接再用、fresh admission成功からsubmitまでの順序修復、累積時間と非競合枠を入口にする。

ユーザーは `quoridor-4lc.320` の独立savedセッションへ既存Rust native arenaの棋力評価環境構築を配分した。[担当契約](../../research-data/ai-sigma/arena-evaluation/task.md)に従い、開始prefix/history、色交換pair、時計とtyped未完了理由、完全pair単位の集計・再現manifestを整える。初回は静的実装、調整済みslotでの累計600秒compile/testsと最大2job/180秒/4slotのD-only小動作確認。CPU最大2/RAM2GiB/GPU0、64MiB inclusiveを完了maintenanceのfuture reservation160→96MiBから移譲し、親保存12GiB/UNKNOWN128MiB・旧current資産を保持する。Root同fullaccess/never、同model/effort。大book生成、Sigma GPU対局、凍結学習候補の本対局、棋力昇格はこの初回構築に含めない。

### 2026-10-07の追加承認

人間は既存FT差分SIMDを採用済みguarded AVX2 headと併用して実装/設定確認・資格・有限比較する方針を承認した。A Scalar FT/B既存Simd FTで同モデル/重み/特徴/尺度/FT列減算加算順を維持し、FT単体とroot setup・実Search全費/同仕事から採否を決める。次に、採用された固定FT/headをbaselineとして、実手からの直接差分特徴生成とSearch所有のbounded子FT/特徴buffer再利用を実装・資格・比較し、残存距離map費を調べる。SIMD不支持でもその問いを完了して次段へ進む。map共有cache/動的最短路の新方式は無条件に実装せず、必要性・効果/保持/保守境界の根拠が出た時に人間へ戻す。[FT比較契約](../../research-data/ai-sigma/search-optimization/ft-delta-simd-v1/task.md)、[直接差分・buffer契約](../../research-data/ai-sigma/search-optimization/feature-delta-buffer-v1/task.md)。

同じ人間承認により、推論高速化完了を待たず、受入れ済みtrained patience1 BEST51/step209559のnative対応・棋力評価準備を既環境担当へ並行配分する。現採用source/backendとモデル/尺度/入力/学習側期待出力を凍結し、実ELF/source/configをSHAで束縛する。同node評価品質と同時間棋力を分け、重要な未承認book/対戦/protocol条件だけ人間へ返す。具体資源と既条件が成立し情報価値がある場合は現版の基準を取り、FT/直接差分・buffer段階の統合後に最終固定版の関連対応と同時間評価を行う。前版結果を探索量が変わる後版の根拠にしない。[trained native/arena契約](../../research-data/ai-sigma/arena-evaluation/trained-reference-v1/task.md)。

保持Sigmaのoriginal-open V診断は既承認の別leafで継続する。original323の本学習pause、新E/旧封印label/未承認test開封、モデル再選定/default更新、FMA/量子化/FT数学/探索規則/枝刈りの保留は変えない。別の保存セッションが実行・統合/main/Gitの唯一writerを所有し、Rootは方針相談・重要判断を扱う。実compile/numeric/性能/時間対局は具体inclusive保存予測・親内の支持されたfuture配分・soleCargo/private binding・fresh actual quiet/exactSTOPで進める。新しい親枠/CPU/GPUや無制限な追加実験は与えない。通常修復/必要工程へ毎回の人間ACK・周期監視・常設roleを追加しない。各具体scope/予測/STOP/検証と担当・状態は上記契約とBeads、結果は[研究知見](../research-findings.md)へ記録する。

## 終了した枠と証拠

frame24/extension25の元の開始は2026-10-06 00:08:46 UTC、連続延長の予定終了は04:08:46 UTC。ユーザーの解体指示により予定時刻を待たず終了した。学習310・描画315・提案316・TT計測317は有限引渡し済み。

- 運用は02:00:20 UTCにscheduler/monitorの正確な二つのidentity不在、ownednull、Supervisor idleを確認した。[停止証拠](../../research-data/ai-sigma/frame24-steward/1gj-terminal-runtime-stop-v1.json)。
- 最終研究保存はGit `6e8d4ab5ac1a3305eff66e4c5b72dd36bfb06b28`。[統括の停止引渡し](../../research-data/ai-sigma/frame24-coordinator/final-stopped-coordinator-handoff.md)。
- 全体の旧期限、失敗、未確認費は元記録で保持する。ユーザー終了を期限遵守・全host停止・最高棋力達成へ読み替えない。

## 残資源と未配分

旧範囲はCPU合計4logical/RAM8GiB/保存12GiB/GPU VRAM6GiBだった。新GPU学習3600秒の消費13.493288946秒・残3586.506711054秒という最終点、旧GPU7200秒残量UNKNOWNと保管UNKNOWN128MiBを保持する。[資源引渡し](../../research-data/ai-sigma/frame24-steward/1gj-final-resource-handoff-v1.json)。残量は追加実験の許可や使う義務を意味しない。保存・過去費をreset/refundしない。

316の全域distinct censusは単独の必須工程にせず、319の全域抽出・資格と実subset多様性記録へ接続する。百万種類を保証する学習、旧CUDA4000step追加比較、MPC校正は未配分。TT実NNUE性能は上記探索高速化タスクの範囲で調べる。現状と比較案は[現在計画](../research-findings.md)へ一本化する。

## 次の実行

人間がRootとの相談で重要な方針を選び、実行・統合担当がBeads課題・目的・単独writer・作業場所・実資源・停止条件・検証を明示して担当へ依頼する。[タスク型研究](ai-research-team.md)と[ジョブ運用](../development/research-jobs.md)を使う。固定ロール、role registry、定期LLM監督、枠終了時の全役起床は使わない。

本書や過去の許可枠を読むだけでは研究を再開しない。学習・データ取得・対局などの新しい実行は次タスクの明示範囲に従う。モデル・入力・検証データ・共有DB・使用中worktreeは保持する。
