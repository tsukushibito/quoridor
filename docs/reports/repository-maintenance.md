# 保守性レビューへの対応と検証

2026-10-06。Beads `quoridor-fwe`。mainを統合正本とし、6担当の変更を独立レビュー後にRootで受け入れる。元の[23所見](../../research-data/maintenance/repository-review-20261006/report.md)は変更しない。対応証拠は[検証記録](../../research-data/maintenance/repository-repair-20261006/verification.json)に集約する。

## 対応範囲

| 所見                  | 変更と確認                                                                                                                        |
| --------------------- | --------------------------------------------------------------------------------------------------------------------------------- |
| MR-01                 | freeze v2で実評価checkpoint・設定・尺度・基準・入力をhash結合。変更・旧形式をモデル構築前に拒否。                                 |
| MR-02 / MR-14         | Corpus APIへ統一。read-only shard mmap、lazy行記録、batch限定の特徴展開、必須hash・長さ・STM特徴／距離対応を検証。                |
| MR-03                 | cycle全段で同じ停止監視と直接子・記録済み子孫のTERM/KILL/wait。proc情報が取れない場合も直接子を回収し、子孫不明を成功扱いしない。 |
| MR-04 / MR-05         | 通常の研究検査は明示NN0集合、人工モデル検査はopt-in。製品・native・全体検査を分離しaudioを追加。                                  |
| MR-06 / MR-07 / MR-16 | 未使用Godot必須導入・検査、未使用API、旧run専用guardianを撤去。学習環境準備は明示操作へ。既存環境・volumeは保持。                 |
| MR-08                 | backendが要求・実行・warm・失敗行を累積計数。未計測captureとそのphysical合計はunknown。                                           |
| MR-09                 | arena分割をopening family／色交換対単位にし、不正境界は起動前に拒否。                                                             |
| MR-10 / MR-21         | 探索中の停止監視、完了ledgerの逐次flush、metadata込み出力制限、有効制限・停止理由を記録。時間制限をfixed workと呼ばない。         |
| MR-11                 | exportは既存artifact／manifestをモデル初期化前に拒否。中間物は専有一時dir、公開は排他的、失敗時の削除は自己所有物限定。           |
| MR-12 / MR-13 / MR-22 | float／residual／quantizedの有界読込を共通化。model-check、arena、dataset evaluateへ接続しCLI案内を修正。                         |
| MR-15                 | worktree管理rootをGit common-dirから解決。linked checkoutでも同じroot／lockを使う。                                               |
| MR-17                 | production検証は専有root／subpath出力へ。通常distのtest hook buildを拒否し、任意custom出力は強制emptyをしない。                   |
| MR-18                 | 既存言語別整形手順へC++／Bash／TOMLの実施方法と未整備時の明示を追加。新たな統一formatterは導入しない。                            |
| MR-20                 | 13画面証拠が現在の指定先に無いことを環境報告に明記。再撮影・過去成功の置換はしない。                                              |
| MR-19 / MR-23         | 描画fallback diagnostics改善とBFCache復帰は今回の承認どおり延期。                                                                 |

レビュー追加所見3件も修正した：proc identity不明時の直接子回収、任意ビルド出力の強制削除、benchmark metadataの容量超過。独立レビューは最終52source・4削除を停止hashと照合し、承認範囲の未解決コードblocker無しと判断した。

## 検証

担当検証：通常研究gate137件、製品audio／render9件、人工CPUモデル5件、全feature native推論6件、NNUE／runner36件成功。NNUEの既存PyTorch依存テスト1件は省略。独立レビューは小入力parser・改変hash拒否をモデルimport無しで別に確認した。

Rootはdev／release Wasmを再生成し、型・fixture・境界検査とrelease製品Rust検査を実行した。製品Rustテストは39件成功、Wasm research featureのrelease checkも成功した。root／subpathのブラウザ検証はそれぞれ対象7件、計14件成功し、通常dist28ファイルは全byte／SHA不変、test API marker無しを確認した。

最初の全UI検査は音声設定とhidden-tab復帰操作が30秒でtimeoutし、中断した。CPU2から承認範囲内のCPU4へ移した対象再検証では両操作も両URLで成功したが、ホスト暖機等もあるためCPUだけを原因と断定しない。hidden-tabの最初の再検証はgrep指定で0件となり未実行、その入口失敗も保存した。全84件を両URLで完了したという主張はしない。

途中の環境設定不足、仮想address制限、合成fixtureの旧RAM制限、Clippy失敗、RootのTypeScript型エラーを各記録へ保持した。Rootのdev検査で想定より増えたcacheと容量超過観測も保存し、自己生成した再生成可能fileだけをhash／inode／停止確認後に撤去した。以後の検査はcached releaseを使う。旧資産とUNKNOWN容量を空きに数えていない。

## 制約と次の作業

科学学習・対局・生成・GPU推論、依存取得・環境更新・container再作成は実施していない。科学データ、選定／評価split、sampling、batch、モデル目的・weights・過去結果は変更しない。chunked集計／QRの数学的目的と人工fixture対応を確認したが、全コーパスのBLAS bit一致、大規模RSS／供給性能、実GPUcapture量、棋力は未測定。

Corpusのcompact metadataとselectorは行／group数に比例する。dense特徴の全件RAM結合撤去だけで数百万局面への容量・速度資格を証明しない。同期native呼出の強制停止は外側jobが担う。C++とBashはformatter未導入のため既存書式への手動整形とcompile／構文／差分検査を使用した。

今回の受入れはソフト保守の範囲。研究再開や新しいコーパス・GPUbatch・学習方式の実行許可には代えない。
