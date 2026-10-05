# 現在の研究選定 — frame22

2026-10-05 11:36:03–15:36:03 UTC。新heavy入口15:26:03、監督正owned15:31:03、monitor15:34:03、必要保存15:36:03。課題候補は[改善課題集合](../design/ai-nnue-optimization-agenda.md)に集約し、担当・着手・依存はBeadsを正本とする。

目標は距離を超えるNNUE最高棋力。期待利益が現れない原因を、教師情報と分布、学習転移、特徴と尺度、探索接続、評価費と到達深度に分けて実測する。小不支持・未成立・不足量を方式全体の断念へ一般化しない。

## 初期の選定

- **273 / experiment**: 既resident GPUとnative pumpの真batchを測る。前枠CPU推論APIが固定K64 root費の99.1%を占めたため、core改良を重ねるより教師の有効行/全job秒を変える可能性が高い。既TensorRT activegames24/48を候補に、現在実装と保持engineから条件を確定する。AOTI/CUDA等は利用可能性と全費で代替を選ぶ。
- **274 / hypothesis**: 保存train-only教師のrootmean/z/距離・局面group対応を分析し、独立game量又は教師目標の小CPU学習対照を実施する。旧A/Bの400step悪化は転移不足を示唆するが、DAG4一般否定にならない。新教師の全局完了を待つ固定工程にせず、使えるgroup境界から判断を進める。
- **275 / critic**: u128採用後のTT手跨ぎ、ordering、NNUE scratch/差分費を比較して最大残費へ実装を選ぶ。手跨ぎTTは有力だが履歴keyで有効hitが少なければ切り替える。共通coreだけでMCTS教師倍率が上がるとは扱わない。
- **92 / steward**: 親有効版22、現在runtimeとassets binding、fresh保管admission、既周期監督、終了回収と長期保守判断を所有する。11:52本人claim/publictool開始を受領。実loadedは別報告で確認する。

## 保留と再検討

全距離map・壁効果・bottleneck等の情報拡張は保持する。教師残差が経路位置情報へ依存する証拠、十分な独立量でも転移しない条件、取得・評価費の見通しで再配分する。LMR/選択探索は正確性を保つ枝の費と品質を見た後、戦術診断・同時間効用を含めて比較する。正式棋力反復は前枠24slotのNNcap打切りを解消する現実的forecastと多様拮抗openingが必要で、未成立を利益なしに変換しない。

## 実行境界と終了

並行source所有は各契約へ、Git/indexは統括一人。CPU合計4/currentRAM8GiB/保持+有効unused12GiBをfresh currentと全forecastで確認する。各固定時間比較は他計算と重ねず、CPU学習とGPU生成は実資源余裕で調整する。旧cap/予約/unknownをresetしない。15:00までを目安にSupervisor終了振返りの必要範囲を既自然報告から選び、92の整理・長期保守判断と並行して受領・採否を残す。自動延長しない。173正式198非学習、開封test非選定、旧失敗・期限・成績を保持。最高目標は未達。
