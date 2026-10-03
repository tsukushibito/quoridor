# 現在の優先順位と評価・学習計画

2026-10-03版11。ユーザー確定方針により、棋力検証・大量対局・自己対局の主環境をネイティブとし、高速化・効率化で結果と学習データを得る総費を下げる。最終目標はNNUE型の最高棋力、初期Sigma同等は未認定。Wasmは必要な数値/探索/合法/応答/取消と少数の実用確認に限定し、大規模Wasm NIを主研究の入口にしない。CPU/GPUは目的と実費から選び、GPU利用を開始条件にしない。

開始00:15:21UTC維持、明示4時間追加で終了08:15:21UTC、重開始08:05:21/監督08:10:21/monitor08:13:21。CPU4logical/RAM8GiB/保持＋予約12GiB、既GPU推論6GiB/job30min・追加GPU学習0。親期限と92運用はsteward単独writerで更新済み、同schedulerを重複開始しない。旧枠の個別期限/結果は変えない。

| 優先 | 問い・到達点 | 配分と完了条件 | 次判断 |
| --- | --- | --- | --- |
| 主1 | 最小native忠実Sigma基準と同時間対局が動くか、総費はいくらか | 165既experiment。151 Rust探索＋固定Web751186のnative-hosted参照＋同ONNX/既CPU provider、私有build→5入力sameK32→条件付き新8pair16診断。build120s/機構180s/対局1800s、新64MiB既枠内 | 同K有限対応とsamewall費/結果を分けて受入れ、native正式設計・教師生成へ。障害なら最小route修復。formal1200/Wasm再検証の義務0 |
| 並行小調査 | CPU/native輸送と既GPU providerの実行可能性/費用の選択 | 164既hypothesis。新NN/GPU/学習0、静的60s/128KiB、10分速報。既依存とsourceから最大1経路 | CPU first優先。GPUは必要な単局面/batch実測を後続配分、GPU対応を文字列だけで認定0 |
| 必要独立視点 | native参照・時計・局面/標本が主問いを満たすか | 166既critic。静的90s/新2MiB、10分速報。実装開始gate0 | 重大scope差を結果前修正、少数診断をNIにしない。正式比較の新native条件を後続固定 |
| 学習準備 | 実対局π/z/rootmean→lineage group→本PV学習→独立arena | 162で小CPU toy 20step/weights-only checkpoint/ONNX5行parityが実成立。現在は5診断の4train/1validationのみ | native基準のπ/z出力を小schemaへ接続する次配分。full selfplay/学習規模/実PV構造/独立holdout未整備、GPU学習追加0 |
| NNUE/方策 | 前段の基準・教師・費用からNNUE＋αβ/方策順序を選ぶ | 156予備コスト終了、主NNUE実装拡大0。方策head候補は正本登録済み | 総探索費と棋力を比較できる段階で別配分、toy損失やcache速度を棋力へ置換0 |

同等の実用定義は5pp非劣性/片側95%という旧158案を保存し、browser m600/1200gameや旧rawを遡及変更しない。旧式L=max(0,mean−sqrt(log20/(2m)))>.45、m600でmean.5を通すが高power保証はない（例示Bernoulli pair power約.51628、分布自由95%power十分m2397）。計画成立、実測不足保留、非劣性支持、劣性支持、不確かを区別する。新native版の参照・モデル/backend・時計/資源・独立開始分布/抽出仮定・fault全分母・固定m/停止を正式データ前に別固定し、今回16診断や教師へ正式holdoutを流用しない。native結果をbrowser NI達成へ読み替えない。

161 NN0 clock14mock、163 browser fixed1000ms/12要求のD500までACKとmain402採用を有限受入れ。163preregisterに1000cycleがあり、161『ACKは次1000前で可』との差は『D500まで必須』として保存、prototype14mockをD500実証へ転用しない。kernelCPU/TID/cutoff誤差等欠測を残しformal_ready=false。費用の大きいbrowser正式clock全保証へ自動連鎖せず、この基準を主native経路へ移す。151/153/155の機構/合法16局7勝9敗を再利用するが同等未立証。

監督の『fixture負担除去を実探索/棋力改善としない』『全cacheの優劣を4状態結果で決めない』『軽い学習準備と正式評価を分ける』を採用。次効果確認はnative機構成立の有無・games/sec/有効教師行/sec・起動/NN/輸送/記録の支配費と実際の配分変更。主基盤の巨大化/追加承認層を効果と数えない。前のbrowser主計画はresearch-data/ai-sigma/frame10-coordinator-start/priorities-before-native-20261003.mdに保存。

04:37–04:38UTC：165本人04:37:21.307017受領/claim私有静的開始、既nativeCPU ORT1.30.0を両engineで使う（browser1.21とは別）。164本人04:38:34.800333受領/claim静的開始、166本人04:38:32受領/04:38:55claim静的開始を確認。166独立速報のevent-driven共通quiescence→新actualt0方式を採用候補として165へactive補足配送。特徴/NN/pipeABI/受信検証を500msへ同ruleで含める定義と原因側cleanup費を事前固定、1000msbrowser周期義務0。推定kernelCPUや完全公平性へ格上げしない。rootへ実配分/開始と必要設計3path writer案を実報告受理04:40:08、本文反映待ちは研究開始gate0。

04:44UTC結果前補足：166が参照だけのbrowser用simulation setTimeout費と異種clock epoch仮定を独立発見。private native wrapperの共通制御/yield/実輸送とcontroller単一monotonicでのt0/受信採用/publicを結果前固定するよう165へ採用補足配送（原policy変更0、除去自体を棋力改善にしない）。164の常駐CPU-first経路を支持、既ORT metadataはAzure/CPUのみでCUDA/TensorRT未対応、原ONNX固定batch1を8件要求と真batch8で区別。GPU新配分0。root167設計3doc Gitdb9a03bfをmain/mirror/current最小照合しnative主方針を継承、roles/common/registryrefresh不要。実source反映/科学成立の確認は165報告、採否の効果は次自然監督で追う。
