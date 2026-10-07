# Criterionの数値CLI確認と同一版反復測定

維持版の数値CLIと統計出力を実行確認した。候補との比較ではなく、同じ現行ELFの連続2回測定である。主算術60d4475、旧BEST c0ec、Scalar、5固定合法履歴を変更しない。

`--test` は30項目がPASS。3起動の5局面でhead値bits、Action/PV/完了depth/stop、全23仕事カウンタ、親履歴、保持メモリ記録が完全一致した。各検索内でも既定の完了depth、冷/温TTの値一致と親復帰を確認する。これは全topologyやcancel/errorの新再資格ではなく、既存証拠を保った実benchmark callerの限定資格である。

| 項目                                    | 1回目              | 2回目              | Criterion相対平均変化と95%CI |
| --------------------------------------- | ------------------ | ------------------ | ---------------------------- |
| `nnue/evaluate/initial`                 | 556.070559 ns      | 545.735686 ns      | -1.0089% [-2.5617, 0.7671]   |
| `search/cold_setup_search_drop/initial` | 26379529.060000 ns | 26769182.386667 ns | 1.4771% [0.6399, 2.3937]     |

headの表示推定値は線形回帰slope、探索はFlat samplingのmean。相対変化はCriterionのmean比較なので、表示推定値の単純比と同一ではない。headは `No change in performance detected`、冷探索は `Change within noise threshold`。冷探索のCI下端0.64%が既定1%閾値を跨ぐためであり、差の点推定1.48%が1%より小さいという意味ではない。表示p=0.00は丸めで、厳密な0ではない。

各項目50samples、1秒warmup、3秒measurement target、100000resamples、95%CI/5%significance/1%noise。3秒は外側の期限ではない。冷探索は1回が長いため各起動150検索を50 Flat samplesに分け、実測窓約4秒となった。同一process内50samplesは50独立processではない。統計実測は初期局面のみ、5局面は数値確認である。

headはfullFTをtimer外に事前計算。冷探索はplayer/TT作成・通常rootFT準備・depth3探索・破棄をtimer内に含む。モデル読込/replay/数値preflightはsample外、whole job内。温TTのCLI確認は合法二手進行を使い、seed/setup/dropをtarget測定から除外する。統計では温TTを今回測定していない。

全job22.59539237502031秒。head実呼出24,619,942をstartup/CLI body/warmup/sampleに分けて集計した。sample数と仕事数は異なる。内部ニューロン演算詳細と共有target成長peakはUNKNOWNのまま。家族RAM sampled peak110,055,424B（controller reserve込み）、GPU0。controller/guardian/全3直接bench childがwait/reap/cleanup[]、現PID/ticks不在を再確認しslotを解放した。学習の重い曲線処理は終了・非重複で、軽い文書作業は並行可能だった。

同一版でも約1〜2%の揺れを観測したが、一般的な誤差幅や最適化の有無を確定しない。旧sort/scratch/maps/TT/FTの負結果、allocator証拠、失敗/全費/UNKNOWNは変更しない。新scratch API・モデル・速度・断片化・latency・棋力の採用はない。候補のCriterion比較は別の有限質問と容量証明が必要で、未実行。

正本rawは `smoke.log` / `canonical-a0.log` / `canonical-a1.log` とCriterion標準sample/estimate/benchmark/tukey。`summary.json`はそれらの保存読取集計、`stop-receipt.json`は正確な回収証拠。
