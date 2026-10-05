# 凍結228 QF1のnative接続：最小一経路の選定 / quoridor-4lc.231

選定は**190のNode native-hosted f32 evaluator/full-deltaとsharedRuleAを私有薄adapterで再利用し、228凍結576BEST2000を接続→固定forward/action診断→同αβの距離D対照小対局**。今回231は静的調査だけで実装・export・NN・compile・gameを開始していない。native-hosted NodeとRust/Wasmを区別する。確認したcrates/toolsのRustソース範囲ではQF1学習重みを読むNNUE evaluator/αβ入口は見つからず、host-wide不在を証明したわけではない。

## 優先する理由と到達範囲

228は新testでteacher-rootmean gameMSE .260522204対train-fitD .400448510、paired95[-.192885480,-.084129888]をowner有限報告し、真z/signも改善と報告した。これは本課題への入力根拠で、231がtestラベル/結果を再評価又は229独立裁定を確定した結果ではない。凍結PTを開かず、公開freeze current SHA `2bac8f1f7ad87b83ac0549c01bb32eb0c8d0a2f39a05c717420e20cd668e6a60` の一致だけ確認した。candidate checkpoint広告SHAは `81c1effc6a3228c337b52a38efec07a0952d6e8b898fa8387cffed0e13c5436b`、576/step2000。候補変更・旧testからの設定再選定はしない。

追加量/LR/表現修正より、いまは改善したvalueが探索のleafに有用かを先に問う情報価値が高い。これを測らずteacher誤差だけ最適化すると、MCTS rootmean蒸留とminimax leaf utilityの差・同時間での評価速度・探索horizonを見落とす。まずNodeで意味を小さく判別でき、広いRustαβ/C++移植の開発を性能認定の入口にしない。逆にNodeの速度だけでRust/差分評価の最終費用を否定しない。

forward/full-deltaと合法actionは機能診断、小対局は同資源・同時計での探索的効用診断である。4game/D対照からSigma同等・最高棋力・Rust/Wasm実用性能は認定しない。192/576のepoch/旧96再用/representation・選定validation相関、K64教師のnoise/history欠落、固定testでのconditional推定の限界は残る。

## 既source/APIと必要差分

| 再用source | APIと現在の意味 | 私有差分 / 未確認 |
| --- | --- | --- |
| `tools/ai-sigma-nnue-qf1-prototype/qf1.cjs` | `features(s,p)`, `maps(s)`, `input(s)`, `load(file)`, `full(s,w)`, `delta(parent,child,w)`, `value(q,w)`。共有312→32両視点、64+2→32→tanh。loadは12193f32=48772B | load/full/deltaをreadonly再用。private `valueScaled(q,w,scale)`のみ追加し、f32 STM distance標準化を再現。旧valueはraw distanceで228へそのまま適用不可 |
| 同 `learn.py` | 専用packing順 `ft.weight,ft.bias,h.weight,h.bias,out.weight,out.bias`、shapes `[32,312],[32],[32,66],[32],[1,32],[1]` | 元main/trainを実行・importしない。後の配分で小exporterがweights_only CPUで `cp['model']`をread、config/shape/dtype/finite/SHAを検査して同順little-endian f32を保存。190のcheckpointは素state_dictだが228はmodel/model_config等のwrapperなのでschemaを区別 |
| `tools/ai-sigma-frame18-data-learning/scaled_model.py`、`tools/nnue-training/model.py` | `(d-mu_f32)/sigma_f32`、canonical STM input、ReLU FT/hidden→tanh。mu/sigmaは登録bufferではない | scaleSHA `68f8b43a0e4408a1546f8fa2652ffdf21f1f7bdcfbac9a25a86ac666b27aa4ee` とbitpatternを専用manifestへ保存、candidate/layout/evaluatorに束縛。configだけ又はPT state_dictだけでは尺度を再現できない |
| `tools/nnue-training/frame14_data.py` | `canonical_model_input` はSTM/opponent sorted IDsとSTM順distance f32bits | native `input(s)`はP1/P2 idsと実side、distance既STM。native accumulatorをside順にconcatする経路とTorch canonical→side1経路が同入力になることを有限fixtureで確認。P2でdistanceを再交換しない |
| `tools/ai-sigma-native-baseline/reference.cjs/context.js/game.js` | `createReference().r`: fromPrefix/referenceState、getLegalActions/next、terminalResult、rustAction | rules/history/terminalを再用。勝敗・draw200/合法手なしをNNより先、child STM valueをnegamaxで反転。artificial diagnostic stateと合法prefixゲームを区別 |
| `tools/ai-sigma-nnue-qf1-prototype/probe.cjs` | old4fixtures、選定27Torch/native、全合法child515のfull/delta、親buffer/key/history復帰。2root depth1、depth2は1024cap打切り | testを旧scriptで再実行せず、private parameterized probeへ固定機構だけ再用。旧190重み/counter/結果pathを編集しない。新候補について独立にparityを測る |
| `tools/ai-sigma-native-baseline/controller.cjs/clock.cjs/arena.cjs` | child IPC generation/pending ID、stop/wait、cause-side cleanup、時計。旧arenaはPUCT CP/root_visits/simulationsと402/411/500ms及び165 gateに固定 | private controllerが新engine entryとalpha-beta CP `{generation,action,completed_depth,nodes}`を受ける。generation/action/完成depth/配送時計だけに必要な薄検査へ。旧arenaをそのまま使う・旧PUCT schemaへ仮visitsを捏造する経路は選ばない |
| `crates/quoridor-ai/src/lib.rs` | `Evaluator::evaluate(Position, legal)->Evaluation{weights,value}`、`SearchSession`はPUCT | value-onlyモデルからSigma policyを推測できず、uniformprior挿入は探索policy変更。native baseline Rust Registryも648/logits136の忠実PUCT。今回はNNUE readyと呼ばない |

### 数値と尺度

候補のh距離列/biasは既に標準化座標で学習済み。export時にinitialの `columns*=sigma; bias+=originalcolumns@mu` を再実行しない。旧raw evaluatorへ逆fold `column/sigma, bias-column/sigma@mu` する案は数学上同値でもf32順序を変えるため、今回は選ばず**runtimeの明示標準化**に固定する。`d_f32=fround(distance)`、`standardized=fround(fround(d_f32-mu_f32)/sigma_f32)`、FT/hidden積和のf32、最後tanh f32を同conditionで比較する。BLASとscalar/deltaの加算順は異なるのでweightbit一致だけでforward一致を主張しない。

parity toleranceは結果前 `abs1e-5 + rtol1e-4` を第一提案とし、各maxabs/maxrelative/入力ID・値・failを保存、tol緩和による救済0。元228初期関数parity1e-6の意味と、異backend/scalar/deltaのtoleranceを別記録する。oldfixtureの27や515は再用機構の参考数であり、新candidateの成功科学ではない。

maxtrain maskは選定データのexposure契約であり、探索中に合法手を除外するNN maskではない。feature/model/scale/candidate freezeとmaskSHAのlineageを保存するが、ゲームのlegal expansionへmaskを適用しない。rootmean/leaf/zを混合しない。HistoryはRuleA stateに保持、312inputには履歴がないため同QF1入力でもRuleA合法/terminalが異なり得る。wallmapは壁/goal/graph版の完全keyだけ、合法壁/NNcache/TTと無条件共有しない。parent copy/delta方式をmutable undo保証に拡大しない。

## 次の最大1実配分案と費用

これは**次の統括配分の提案**であり231の起動許可ではない。単一private routeで複数モデル/幅/LR/clip/shrink/TT/noiseを選別しない。

1. source/export/layout/scalefreezeとNN0 schema/argv、27固定P1/P2/pawn/jump/diagonal/HV Torch vs native。full/deltaは固定4rootの全合法childを1pass、親accumulator bytes/key/history完全復帰。terminal goalのSTM ±1/draw200/合法手なしを先判定、終局NN0。packet/schemaやrounding失敗ならtyped未接続として止める。
2. 固定4rootの同leafbudget depth1→2 alpha-beta。各root nodecap2048、全合法手を列挙、policy除外0/TT0/noise0/temperatureなし/FPUなし/solver追加0、定順tie（Action昇順）を結果前固定。NODE_CAP/未完成depthのPVはdiscardしlast completedだけを報告。全legal child mapping/Action・value・nodes/completed_depth/wall/RAMを残す。これだけならWDL利益は不明で有限終了可。
3. parityが成立し実装/物理headroomがある時だけ、**同じαβ＋同nodeguardでNNUE対train-fitDの2opening×色交換4game**を一つの探索的診断として提案。openingは非holdoutの合法prefix空と190固定8plyの2個（人工board fixtureをゲーム初期へ混ぜない）、事前hash固定。D係数はcandidate freezeのtrain-only a=.06038215201109912/b=7.925687690687516をfreezeしclip/f32順序も固定。candidate/Dとも100ms/手（私有子内90ms探索、10ms配送margin案）、t0は入力供給可→合法完成action配送まで、同CPU2一論理/1thread/GPU0。処理終了・旧generation回収をcause側へ別記録し相手へ転嫁しない。completed depth1すらない場合はtyped incomplete、勝敗への置換・都合よいfallback・局数補充0。共通goal/RuleA200plydrawの全4slot/fault/timeout/未完分母を保存し、有限WDLと各手nodes/NNeval/wallを分ける。

同wallではDが安い分nodes/depthが多くなり得るため、固定node action診断との対応を併記しvalue情報と実評価費を切り分ける。同nodeだけで同wall棋力を認定しない。Sigma-Web MCTSのpolicy/FPU.2/temperature0とは別search conditionであり、4game/D対照をSigma同等へ読み替えない。

| 将来費用項目 | 上界/見積と条件 |
| --- | --- |
| 私有実装+export/schema+時計/action検証 | 25–40分、既source再用、build/依存install0。見積で実CPU scienceではない |
| 小export＋27Torch parity、全child full/delta | CPU2単1/torch1、RAM2GiBguard1.75、1job120s。export読み込みはforward0、parityは全actualを台帳へ |
| 固定4root action診断 | 4×2048 nodeguard、最大8192NNleaf、1job120s。terminal/cache等でactual葉数は減るがunknownを0へ変換しない |
| 4game（成立時のみ） | 各game<=200ply、4×200×100ms=80sの思考時間上界＋初期/合法/feature/pipe/記録/回収未知。2game単位jobhard120s×2、totalheavy最大480sを第一提案。最大NNleafは800手×2048=1,638,400、parity/actionと合計1.7m cap案。timeが先に尽きたら部分/NOT_STARTED保存 |
| 保存 | layout48,772B＋scale/evaluator/schema、圧縮weights・必要perply/root/action/fault＋uniqueGit/temp/metadataで新16MiB/guard14MiB案。現在2312MiBへ実重み/ログを追加しない。expunusedを再測定後に別配分 |

13:15→13:50の実装/接続見積、parity/actionは14:05まで、小対局が成立する場合も14:15科学停止/14:20必要保存を狙う。親heavy14:23:18/end14:33:18より早い。25–40分の上側やadmission不成立で余裕不足ならstep2までの診断を優先し、ゲーム利益はNOT_RUNとして次枠1単位へ渡す。次実契約はjob数・sample・fault/終了/slot規則を結果前固定してownerに配送する必要がある。231は科学job/compile/forward/fit/train/GPU/game/test0のまま終了する。

## 結果によって変える判断

parity不成立ならview/scale/layout/accumulatorの具体差を修復する最小1単位が次で、追加教師/LR/モデルを救済に使わない。parity成立・action診断だけではteacher誤差利益の探索効用は未知。4gameで候補がDより悪い/不確かなら、nodes/leaf予測/終局手前のcaseからleaf-targetとhorizon又は実評価費のどちらが次の問いかを選び、4gameを原因保証にしない。候補が有限有力なら同feature/evaluatorをRust private evaluator/αβへ移す費用を次に配分し、同wall/独立arenaで確認する。どちらでも現凍結testを再開・候補選び直しはしない。

## 231自身の停止・保存

receipt13:10:35、ready/show goal+self no pause/本人担当→claim/static13:11:29。227を同実taskturn内に受入れ根拠で本人close、backup0済。read-only source/publicmetadata19pathをSHA/lenで束縛、source-read90s上界・管理120s、モデルPTロード/科学子/torchimport/forward/学習/compile/GPU/game/test0。新2MiBは確認済expunused157392896から別計上、残155295744。scope+uniqueGit/temp/残metadataforecast1MiB/guard1.5MiB、旧hyp56MiB/2274MiB/unknownを保持し親追加0。source/doc停止後、必要小Gitbytes/index不変更/notesbackup/統括へ有限handoff。役/主手順mirror/92/共有source編集0、最高棋力未達。
