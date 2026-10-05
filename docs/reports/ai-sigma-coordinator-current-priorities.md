# 現在の研究選定 — frame22

2026-10-05 11:36:03–15:36:03 UTC。新heavy入口15:26:03、監督正owned15:31:03、monitor15:34:03、必要保存15:36:03。課題候補は[改善課題集合](../design/ai-nnue-optimization-agenda.md)に集約し、担当・着手・依存はBeadsを正本とする。

目標は距離を超えるNNUE最高棋力。期待利益が現れない原因を、教師情報と分布、学習転移、特徴と尺度、探索接続、評価費と到達深度に分けて実測する。小不支持・未成立・不足量を方式全体の断念へ一般化しない。

## 初期の選定

- **273 / experiment**: 既resident GPUとnative pumpの真batchを測る。前枠CPU推論APIが固定K64 root費の99.1%を占めたため、core改良を重ねるより教師の有効行/全job秒を変える可能性が高い。既TensorRT B8/fill2ms/worker1、activegames24/48で同48familyを各48trajectory、総96trajectoryを結果前固定する。canonicalは片側だけ36train/12選定validation、追加32は未実行保留。限定affinityとhost reserveを分ける明示inference coreの小APIを実装する。実topologyで2/3同physicalを検出し、worker2/inference4の同2logicalへ再配分した。AOTI/CUDA等は利用可能性と全費で代替を選ぶ。
- **274 / hypothesis**: 保存train-only教師のrootmean/z/距離・局面group対応を分析し、独立game量又は教師目標の小CPU学習対照を実施する。旧A/Bの400step悪化は転移不足を示唆するが、DAG4一般否定にならない。新教師の全局完了を待つ固定工程にせず、登録train ID順の完整12/24/36prefixの最大一つを使う。Aは既96train/256000seenの実学習を完了しBEST200旧選定val .478510425、原前枠との対応を保持した。Bは96+新train、同seen・同初期尺度で比較し、epoch差・tau1生成分布差を残す。新12validationは選定用で未見評価とは呼ばない。
- **275 / critic**: u128採用後のTT手跨ぎ、ordering、NNUE scratch/差分費を比較して最大残費へ実装を選ぶ。初回4root D/L profileでL advance44.64%/evaluate20.81%、TT97hit/0cutoffだったため、同算術順accumulatorとleaf入力scratchを最大2候補に選んだ。3variant同binaryの順序反転確認でdepth2のAction/値bits/仕事/履歴復帰が一致し、two-candidate prototypeのdelta capacity再用は中央値合計比 .9878/.9782だった。一方leaf hook除去後の最終版は合計比1.001267で、prototypeの約1.2–2.2%減を最終版の利益へ移植できない。最終同binary順序反転確認は既caps内で登録済み、現在は速度利益・main採用を保留する。leaf入力scratchの追加利益は安定せず、保存後にproduction hookを除く方針を採択する。最終源停止pointで統括が実装レビュー・必要テスト根拠を独立確認して採用を判断する。手跨ぎTTはこのwithin-searchだけで棄却せず、合法sequence再利用の機会を保留する。共通coreだけでMCTS教師倍率が上がるとは扱わない。
- **92 / steward**: 親有効版22、現在runtimeとassets binding、fresh保管admission、既周期監督、終了回収と長期保守判断を所有する。本人claim/publictool、11:57:26新running/loaded、current24hash/正2identityを確認。全新growth込保管11061895168B<12GiB/errors0、最初自然observe/finish/notesbackupが有界到達した。未来全期間・科学・判断品質保証と区別する。

## 保留と再検討

全距離map・壁効果・bottleneck等の情報拡張は保持する。教師残差が経路位置情報へ依存する証拠、十分な独立量でも転移しない条件、取得・評価費の見通しで再配分する。LMR/選択探索は正確性を保つ枝の費と品質を見た後、戦術診断・同時間効用を含めて比較する。正式棋力反復は前枠24slotのNNcap打切りを解消する現実的forecastと多様拮抗openingが必要で、未成立を利益なしに変換しない。

## 実行境界と終了

並行source所有は各契約へ、Git/indexは統括一人。CPU合計4/currentRAM8GiB/保持+有効unused12GiBをfresh currentと全forecastで確認する。各固定時間比較は他計算と重ねず、CPU学習とGPU生成は実資源余裕で調整する。旧cap/予約/unknownをresetしない。15:00までを目安にSupervisor終了振返りの必要範囲を既自然報告から選び、92の整理・長期保守判断と並行して受領・採否を残す。自動延長しない。173正式198非学習、開封test非選定、旧失敗・期限・成績を保持。最高目標は未達。

12:10 Supervisor自然点検の提案を採択する。同seen対照は同学習仕事の比較で、各epoch・実steps/seen/学習wall・生成初期化/輸送/保存/回収を含む総費は別に返す。Dにも効く探索改善からNNUE相対強さを代弁しない。新役定義coordinator.mdはRoot276単独writer、92が安全窓/binding/session適用、統括は源重複編集せず新正本保存後に責務・権限・独立性を一度確認する。自己実装の独立評価は別ownerで行い、毎配分の全文再読・全役ACKは増やさない。

12:29 役改定276の指定34pathを20ba314へbyte/SHA一致で保存。改定時にcommonと自分含む6役を正本から一度確認した。273 teacher cache metadataの薄拡張は同teacher WT quoridor-data/lib.rs+必要test、統括sourceレビューと274入力・label-free mask検証を分離して実配分。276の現在runtimeはscheduler1233793/45593355・monitor1235182/45599721へ通常再開済み。恒久idle refreshは92 pendingで科学gateにしない。

274 pre-B v2はfit/stats前のtrain group選択、state/history/実STM f32入力のOR除外、同cacheのselection labelsとlabel-free mask predicateの区別を明記した。統括のPython readonly初期reviewでこれらの境界を確認、実教師cache/対応group/hashと新入力parityは273→274の後続実観測として保持。fake checksをproducer独立認証へ読み替えない。

12:39 275の最終版で性能結論を更新。別owner source reviewは同算術・親不変・per-ply所有・エラー復帰・鍵/探索順の保持を支持するが、性能の支持とは別である。最終版の方向が安定しなければ保守費を増やすmain hook追加は見送り、比較専用源と証拠を保存してNNUE幅/呼出側分布等の変化で再検討する。prototype有利系列だけを採用理由にしない。残advance内部費とTT実sequenceは有力保留案として、科学停止後の次判断で費と判別力を比較する。

273のmetadata v2は明示P1/P2 ids・STM distance/view orderを保持し、統括の別owner source reviewで既tensor writer不変を確認した。実新cache/parity/Bは未成立。GPU資格slot1は[N/A]監視整数化で自己停止し、数学反証ではなくUNKNOWN NN+620保守課金を保持、MAX4内必要0game修復へ。旧verification179.958s/旧static180保守charge/未測UNKNOWNを保持し、残接線に将来NN0準備180sを明示追加配分した（親物理・NN/GPU/MAX4不増、旧reset0）。現在GPU成功を先取りしない。

275最終版の順序反転は .956850、前回1.001267と方向が揺れた。統括は4source SHAと保存全attempt NN243500/processedcharge1566984の和を独立確認し、source correctnessを有限受入れ、main源追加は保留する。必要比較源/dataはGit保全し、特定有利runの改善率を保証しない。Supervisor12:41提案のCPU比範囲も採択:273 GPU24/48同family比較はGPU内対照で、旧CPU4root費を全生成倍率へ外挿しない。今回は適格教師と絶対全job費を優先し、追加CPU全生成jobを必須gateにしない。CPU比が次配分を変える場合に別の有限対照を選ぶ。

13:00 節目: 273資格修復は620 physicalNNで有限PASS、active24は48/48終局・1720適格行（train1328/selection392）、全attempt guardian46.852700秒で36.7108行/秒を記録した。同登録48のactive48を次の既slot3で実測中。canonical一条件の停止cache→274 Bを主接線として優先する。GPU内対照/絶対費を使い、CPU全生成比・教師leaf真値・棋力は未認定。275比較専用4sourceを9d7e02dへbyte/SHA一致保存し、archive112member復元を独立確認、main hooks追加は見送る。次探索配分は安いadvance内部 encode/maps/ID費と合法fullhistory sequence TT機会の診断に限定し、改善実装を先に決めない。既scratch反復より次判断の情報価値が高く、正式棋力比較は教師/B結果と現実的NN費を待つ。

277 / criticへ実配分: advance内部encode/maps/ID取得費と合法sequence fullhistory TTのusable-depth機会を最大1低費用診断で比較する。CPU3単一、compile/test60秒・科学30秒/NN12000/processed32000を別課題へ明示配分し旧275課金は保持。新source/data1MiBとrelease16MiBは旧275確認unused内から移転し、aggregate予約は増やさない。改善実装を先取りせず、273 active48→274 Bの固定計時計算を優先して自然回収後に実測する。main採用判断は統括の別owner判断とする。

13:06 教師接線成立: active24/48は同48family各48GOAL、同1720適格行/Action列/NN仕事。active48全attempt41.484730秒・41.4610行/秒、active24 46.852700秒・36.7108行/秒に対し時間-11.4571%/率+12.9396%。固定実行順/hostwarm/重複spanの限界を保持し、CPU全生成比較は未実施。事前規則でcanonical active48一側を採択し、36train1328/12selection392の停止immutablecacheを274へ実配送、coorはstop/metadata/familymap/cachemanifest SHAを確認。274 v6 fake誤記8PASS1FAILは管理不足として保持し、v7 schema拒否修復後に一Bをfreshadmitする。旧historyキー形式互換未確認を非露出保証へ読み替えず、state/実STM入力の独立mask/parityとcoverageを分ける。277計時は13:15までB入口を有限優先し、B actualstopで早期解放、静的準備は継続。
