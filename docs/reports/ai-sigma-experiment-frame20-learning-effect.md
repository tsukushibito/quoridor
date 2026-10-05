# 学習済みL対忠実初期Iの同探索対照 (256)

全4slotはNOT_STARTED(CURRENT_WINDOW_UNAVAILABLE)。02:40:30の新科学入口までに背景helperの待機条件が成立せず、モデル科学は始まらなかった。学習利益なし、棋力同等、parity不成立という結果ではない。

## 固定した問い・recipe

Lは228576BEST2000凍結tensor b81792d5、12193 LE-f32 /48772B。Iは同構造・同config・seed19080311・元ScaleModel/RawModel constructor・距離尺度補償を一回適用する忠実step0。元configと旧initial.pt SHA5e6da7ede197f7bc0e554b61e607eac01717f740260c614b01841d830dbcc407、およびraw初期e5d218c9・scale68f8b43aを束縛した。科学jobで初期checkpoint全tensor byte照合、27Torch/native STM full/delta parity(abs1e-5+rtol1e-4)、modelID schema/旧model応答discardの有限確認後だけ対局する源を準備した。今回I export・モデル初期化・Torch import・parityは全NOT_RUNであり、recipeの実行成立を先取りしない。

新私有源は共有trainer/model・旧232/249/254源をreadonly参照する。初期化/forward/fixture→対局はMAX1 command内、fit/optimizer/GPUなし。元NNUEの幅・距離標準化・実STM・terminal/fastleaf・rootbest-first/全合法・TT/noise/policyなし、node32768・内90ms・親完全parse/generation/modelID/key/history/合法Action受領100msを維持する接線である。未実行源の全動作保証はない。

## 全4分母・停止

| slot | family | 学習済みL側 | 状態 |
|---|---|---|---|
| 1 | 0 | P1 | NOT_STARTED |
| 2 | 0 | P2 | NOT_STARTED |
| 3 | 1 | P2 | NOT_STARTED |
| 4 | 1 | P1 | NOT_STARTED |

入力は249/242と同2prefixの再測定計画であり、未見holdoutや独立4openingではない。旧成功を一条件へ流用せず、WDL・UNKNOWN結果は不存在。開始後censorを未開始へ書き換えたものではない。

background job31600855-c3d2-4147-9e2d-a2d6990a4b22、created02:37:35.284784Z、command02:37:37.115976Z〜finished02:40:32.475210Z、exit2、cleanup_complete=true/remaining[]。背景wall175.512893590s、control_wait175.275387465sは自然窓待機でありモデル科学wallではない。科学0job/0s、Torch/nativeNN0、processed0、initial.f32不存在。記録子602162/tick42087560・supervisor602106/tick42087379は02:41点でexact不在。Idleへの完了通知delivered、command再実行なし。

待機helperはrunning/current loadedに加えowned=None、次dispatchまで165s以上を要求した。submit前02:36:24点のnext_atは02:36:45で約21s、次turnは02:36:48開始して02:41点でownedだった。全待機期間のCPUtool/物理競合は計測しておらず、実CPU不足が継続したとは認定しない。LLM人数制限による停止や科学性能負例にも置き換えない。ownedなしという保守的条件と実CPUguardの評価前段を分けた運用上の未到達として保持する。最遅入口後にquietを読み換えて開始しない。

32 source/input/元config/元initial/frozenL SHAのcurrent一致、静的Python compile/Node --checkだけPASS。科学源Git98c9cbf6a04e97a8d63ecc5f79dedfe226dc3548、実entry learning-effect-256-v1/schema learning-effect-v1。元MAX1/135s/400000NN、旧254・249・全旧費・unknown・時計をresetしない。静的源準備と管理の全CPUwallは全command個別計測されておらずUNKNOWN、通信/LLM/待機と科学wallを混ぜない。必要保存費はpreservation-v1.json。

## 開始局面の偏りと判断

root255 suppliedの既Sigma d790 CPUORT1.30 raw開始値はP1視点opening0(8ply)−.6504098177、opening1(16ply)+.4746417999。rootが実2NNだけ測った参照であり256追加NN0、勝率/確定勝敗/均衡保証ではなく、浅いminimax後値とも範囲が違う。固定prefix/順序は変えなかった。色交換しても同盤面側が勝つ旧2prefixの示唆はこの小対照の検出力を制約する。将来L/IのWDL一致でも一般同等や学習利益なしとは認定できない。

未来の棋力評価は、拮抗した多様な局面を主とし、即勝ち/浅い強制勝敗/開始評価/距離差/残壁/色交換を考慮して偏った局面を別能力層へ分ける。Sigma閾値単独の一律gateは置かない。訓練生成は優勢/劣勢/拮抗/終盤も必要なので一律除外せず、構成比/重複/有効教師量/費を把握する。評価用選定と訓練用分布を同一化しない。今枠の新生成/学習/対局は追加しない。

次最大1は、この同構造L/I対照を十分な現在資源窓を持つ別実配分で実施する方向。保守的owned待機と実CPU競合admissionを明確に分け、初期化/数値parity費も含む時計を先に確保する。現在はNOT_RUN/未配分であり新jobを自動起動しない。履歴単独案は具体的RuleA不一致が出た時の保留候補、最高棋力goalは未達。

新4MiB予約/guard3.5MiBは旧poolunused11640832→7446528の一度計上。旧予約・unknown割引・親追加なし。必要source/input/preregister/settings/wait/background結果/停止/報告を小pack/Git currentbyteへ保存し、default index不変、本人close/backupで有限引渡しする。
