# FP32 residual head SIMD integration

`quoridor-4lc.318.3`の固定候補をmainへ採用した。独立レビュー`318.3.1`は採用blocker0。人間が許可したFP32加算順変更と僅差の手の変化の範囲で、残差headをruntime AVX2の8lane累積・balanced reductionへ変更する。FMA、FT、モデル/特徴、探索順/TT/枝刈りは変更しない。範囲guardの不成立と非AVX2環境では旧順のscalar算術を使う。

`ResidualEvaluator.mode`はFT modeであり、headのscalar固定を意味しない。範囲normはモデルsetupに属し、入力guard/dispatchは毎評価の時間に含む。scratchはSearch呼出しごとに所有し、SearchSession寿命へ持越さない。one-shot evaluateはscratch setupを含む。実行版/backendを変える場合、TTをresetまたは新しいSearchSessionを作る。推論再現にはsource SHA、FT mode、head方針`fp32_avx2_lane8_balanced_no_fma_guarded_scalar_fallback_v1`とhardware/AVX2可否を記録する。

## 固定測定の結果

旧c0ec重み/FT32H32・5固定局面・depth3・node100000・TT4096。Criterionの2 ABBA blocks、8測定process、各50 samples/暖機1秒/target3秒。各Bを両隣Aへ標準比較し、10項目すべて4/4 Bの95% mean-change CI上端が−1%未満。50 samplesは50 processではない。

| 局面           |   head A→B ns | cold探索 A→B ms |
| -------------- | ------------: | --------------: |
| initial        | 546.58→287.26 |   26.732→22.099 |
| opening        | 553.01→291.23 |   32.821→27.510 |
| walled-midgame | 547.35→290.92 |   23.730→20.057 |
| jump-p2        | 542.03→282.23 |   23.096→18.325 |
| endgame        | 546.44→291.20 |   24.600→19.822 |

上表は4 processのmean estimateの記述平均。head時間は46.71〜47.93%、cold探索は15.48〜20.66%短縮した。headは事前FT/scratch/model setupを除外し、cold探索はrootFT・Search scratch・TT setup/search/dropを含む。範囲norm/model loadはsamples外・process費内。最初4局面はAction/PV/depth/stop/23 countersが一致し、終盤はnodes−0.723481%/eval−0.162940%で仕事量の差を含む。全5局面はdepth3完了。適応測定process wallの比を速度倍率にしない。別hardware/modelや棋力へ一般化しない。

## 数値と確認境界

81,297固定入力対の最終値差は最大2.980232e−7。f64参考との差の最大はscalar2.813838e−7/fast2.031615e−7（同じ丸め済みFP32入力/重み/Dであり数学的真値の保証ではない）。5完全depth2 treeのActionは一致し、各treeのgapが測定leaf epsilonの2倍を超えた。

640相関局面の限定探索では21,512,607 visited head pairsの最大差5.103648e−7。Action20/PV24/counter sets84が変わり、完成depth/stopの変化0。総nodes+0.012784%/eval+0.008414%。返却値の近さは変更手のdepth3 regretや棋力を証明せず、20/640は一般的な危険確率ではない。headの丸めはFT差分状態へ蓄積しない。

提供kernel資格は全2048 FT幅/packed長8〜4102の偶数長/4scale。モデル所有権fixtureは**21 topology（7 FT幅×3 H幅）/84 parent-side-FT-mode/1176 forwards**である。凍結ログの24/96は古い表示literalだった。mainの表示と本解釈を訂正し、元ログとarchiveは変更していない。valid極端相殺/no-AVX2の独立platform runtime、全2048×2048 topology、全モデル・全対局、棋力は未確認。

## 統合と検証

4完全candidate sourceのarchive SHAとmainの4 canonical source SHAを再照合して反映した。測定済みproduction算術に追加差分はない。独立レビューの通常修正としてmodule/FT mode説明、21/84表示、runnerのhead policy metadataを更新した。前後SHAと全差分は[integration.json](integration.json)。既source-bound release build/Clippy/数値・親/undo/error/cancel・Criterion証拠を再用し、mainでは限定差分照合・rustfmt/Prettier・diff checkに合格した。新しいmain Cargo buildや数値runを実行済みとは主張しない。

元job4feb1c91は2026-10-07T06:28:25.548099Zにexit0、controller477.057091709秒、28直接command wait/reap、guardian回収/cleanup[]。Rootの新鮮なPID/start照合と復元証拠も保持する。旧負/混在結果・原ログ・費・build peak UNKNOWNを保全。モデル/default採用、新学習、original323のpause解除、newE/Sigmaラベル開封を含まない。

完全source/raw/report/summary/stop/reviewは[integration.json](integration.json)が絶対pathとSHAで参照する。Gitで復元可能な旧production経路を本番に常設せず、portable/guard fallbackと独立scalar test oracleを維持する。
