# 現在の研究選定 — frame22

2026-10-05 11:36:03–15:36:03 UTC。新heavy入口15:26:03、監督正owned15:31:03、monitor15:34:03、必要保存15:36:03。課題候補は[改善課題集合](../design/ai-nnue-optimization-agenda.md)に集約し、担当・着手・依存はBeadsを正本とする。

目標は距離を超えるNNUE最高棋力。期待利益が現れない原因を、教師情報と分布、学習転移、特徴と尺度、探索接続、評価費と到達深度に分けて実測する。小不支持・未成立・不足量を方式全体の断念へ一般化しない。

## 初期の選定

- **273 / experiment**: 既resident GPUとnative pumpの真batchを測る。前枠CPU推論APIが固定K64 root費の99.1%を占めたため、core改良を重ねるより教師の有効行/全job秒を変える可能性が高い。既TensorRT B8/fill2ms/worker1、activegames24/48で同48familyを各48trajectory、総96trajectoryを結果前固定する。canonicalは片側だけ36train/12選定validation、追加32は未実行保留。限定affinityとhost reserveを分ける明示inference coreの小APIを実装する。実topologyで2/3同physicalを検出し、worker2/inference4の同2logicalへ再配分した。AOTI/CUDA等は利用可能性と全費で代替を選ぶ。
- **274 / hypothesis**: 保存train-only教師のrootmean/z/距離・局面group対応を分析し、独立game量又は教師目標の小CPU学習対照を実施する。旧A/Bの400step悪化は転移不足を示唆するが、DAG4一般否定にならない。新教師の全局完了を待つ固定工程にせず、登録train ID順の完整12/24/36prefixの最大一つを使う。Aは既96train/256000seenの実学習を完了しBEST200旧選定val .478510425、原前枠との対応を保持した。Bは96+新train、同seen・同初期尺度で比較し、epoch差・tau1生成分布差を残す。新12validationは選定用で未見評価とは呼ばない。
- **275 / critic**: u128採用後のTT手跨ぎ、ordering、NNUE scratch/差分費を比較して最大残費へ実装を選ぶ。初回4root D/L profileでL advance44.64%/evaluate20.81%、TT97hit/0cutoffだったため、同算術順accumulatorとleaf入力scratchを最大2候補に選んだ。3variant同binaryの順序反転確認でdepth2のAction/値bits/仕事/履歴復帰が一致し、delta capacity再用は中央値合計比 .9878/.9782（有限約1.2–2.2%減）だった。leaf入力scratchの追加利益は安定せず、保存後にproduction hookを除く方針を採択する。最終源停止pointで統括が実装レビュー・必要テスト根拠を独立確認して採用を判断する。手跨ぎTTはこのwithin-searchだけで棄却せず、合法sequence再利用の機会を保留する。共通coreだけでMCTS教師倍率が上がるとは扱わない。
- **92 / steward**: 親有効版22、現在runtimeとassets binding、fresh保管admission、既周期監督、終了回収と長期保守判断を所有する。本人claim/publictool、11:57:26新running/loaded、current24hash/正2identityを確認。全新growth込保管11061895168B<12GiB/errors0、最初自然observe/finish/notesbackupが有界到達した。未来全期間・科学・判断品質保証と区別する。

## 保留と再検討

全距離map・壁効果・bottleneck等の情報拡張は保持する。教師残差が経路位置情報へ依存する証拠、十分な独立量でも転移しない条件、取得・評価費の見通しで再配分する。LMR/選択探索は正確性を保つ枝の費と品質を見た後、戦術診断・同時間効用を含めて比較する。正式棋力反復は前枠24slotのNNcap打切りを解消する現実的forecastと多様拮抗openingが必要で、未成立を利益なしに変換しない。

## 実行境界と終了

並行source所有は各契約へ、Git/indexは統括一人。CPU合計4/currentRAM8GiB/保持+有効unused12GiBをfresh currentと全forecastで確認する。各固定時間比較は他計算と重ねず、CPU学習とGPU生成は実資源余裕で調整する。旧cap/予約/unknownをresetしない。15:00までを目安にSupervisor終了振返りの必要範囲を既自然報告から選び、92の整理・長期保守判断と並行して受領・採否を残す。自動延長しない。173正式198非学習、開封test非選定、旧失敗・期限・成績を保持。最高目標は未達。

12:10 Supervisor自然点検の提案を採択する。同seen対照は同学習仕事の比較で、各epoch・実steps/seen/学習wall・生成初期化/輸送/保存/回収を含む総費は別に返す。Dにも効く探索改善からNNUE相対強さを代弁しない。新役定義coordinator.mdはRoot276単独writer、92が安全窓/binding/session適用、統括は源重複編集せず新正本保存後に責務・権限・独立性を一度確認する。自己実装の独立評価は別ownerで行い、毎配分の全文再読・全役ACKは増やさない。

12:29 役改定276の指定34pathを20ba314へbyte/SHA一致で保存。改定時にcommonと自分含む6役を正本から一度確認した。273 teacher cache metadataの薄拡張は同teacher WT quoridor-data/lib.rs+必要test、統括sourceレビューと274入力・label-free mask検証を分離して実配分。276の現在runtimeはscheduler1233793/45593355・monitor1235182/45599721へ通常再開済み。恒久idle refreshは92 pendingで科学gateにしない。
