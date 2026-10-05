# frame18 凍結scaled QF1のnative接続 / quoridor-4lc.232

228の576局BEST2000を変更せず、190のNode native-hosted load/full/deltaに私有距離標準化adapterを接続した。固定27入力のTorch/native最大差8.940697e-8、固定4rootの全515合法childのfull/delta最大差1.192093e-7で、結果前tol abs1e-5+rtol1e-4を通った。固定node探索も全4rootで合法Actionを返した。Rust/Wasm実装、同時間棋力、Sigma同等の認定ではない。旧228のcurve/test/bootstrapについて229独立NOT_RUNをPASSへ救済していない。

## 凍結・表現・視点

candidate-freeze-v1 SHA2bac8f1f7ad87b83ac0549c01bb32eb0c8d0a2f39a05c717420e20cd668e6a60、candidate PT SHA81c1effc6a3228c337b52a38efec07a0952d6e8b898fa8387cffed0e13c5436bを束縛。weights_only CPUのcp.modelから順ft.weight/bias,h.weight/bias,out.weight/biasで12193little-endianf32=48772Bを出力した。byte SHAはb81792d5ba00c6d79b58cada2fc81d84ea822db48c04420b4e269fb9b71841b3。学習済h距離列/biasの再補償0。

旧scale SHA68f8b43a0e4408a1546f8fa2652ffdf21f1f7bdcfbac9a25a86ac666b27aa4eeのf32 mu/sigmaをmanifestへ明示。runtime f32((d_f32-mu_f32)/sigma_f32)、P1/P2 accumulatorを実STM/相手順にconcat、distanceは既STM順を再swapしない。Torch側は共有canonical入力でside1へ正規化。旧qf1.cjs/sharedRuleA/source/model/環境/228test結果はreadonly、再fit/モデル取得/共有編集なし。原初期関数parityと、今回scalar/BLAS/deltaの加算順差のtolは別契約。

## 到達点1：機能・数値

固定rootはinitial-p1、asym-hv-p2、straight-jump-p2、固定合法8ply diagonal-p1。元fixtureRows27を結果前NN0で固定。P1/P2、pawn、straightjump、diagonal、H/V壁を含む。515全合法childのfullとdeltaのID/finite valueを照合。親accumulator byte/key/historyはchildごと不変。これは親copyを維持する方式でmutable undoの保証ではない。

terminal goalのSTM値−1、200ply draw0をRuleAで先判定し、終局NN0。履歴はRuleA stateに保持するがQF1入力に履歴は入らない。teacher rootmeanはminimax leaf真値と同一ではない。

Torch27 + native1057 =1084sample。parity job13:58:08.904730–13:58:10.834342、guardian1.929623s、peak familyRSS806522880B、CPU2単1/Torch1/GPU0、exit0/全子wait/current PIDtick不在。

## 到達点2：固定4rootのαβ診断

candidateとtrain-fit D(a=.06038215201109912,b=7.925687690687516)を同RuleA、全合法、実board Rust Action昇順、strict greater同値first、TT0/noise0/policy除外0で比較。depth1→2 iterative negamax αβ、各root/engine累積processed2048cap、未完成depthを捨てて最後の完成depthだけ採用。DはNN0値評価であり、MCTS visits/piは作っていない。

| root | 候補採用depth / Action | D採用depth / Action | 候補processed / NN | Dprocessed / D値評価 |
| --- | --- | --- | ---: | ---: |
| initial-p1 | 1 / 148 | 2 / 13 | 2048 / 2015 | 655 / 522 |
| asym-hv-p2 | 2 / 67 | 2 / 67 | 501 / 376 | 627 / 502 |
| straight-jump-p2 | 2 / 31 | 2 / 31 | 1039 / 905 | 535 / 401 |
| fixed-legal-diagonal-p1 | 2 / 48 | 2 / 48 | 893 / 762 | 807 / 676 |

初期候補のvisited2049はprocessed2048+拒否entry1であり、2049NNではない。深さ2のpartial Action/valueは採用していない。完成depthのroot合法Actionは全数探索対象、内部αβcutoffは保持。非最善root childのfail-soft返値はboundを含み、等値root Actionの違いを勝敗/値誤りへ変換しない。別順序比較ではroot等値・bound/値整合を別検証する必要がある。

第二科学14:10:54.813585–14:10:55.466123、guardian0.652543s/peak129134592B、nativeNN4058。Node全8探索のwholewall574.979ms。terminal inclusive spanはinitialNNUE128.534msなど目立つが、terminal内合法生成、既State cache、経路/順序、map warm、入力処理を含む。排他的律速又は純eval支配へ断定しない。各spanとwholewall、depth別nodes/evals/cutoff/full-delta更新数をsearch-resultへ保存し、重複区間をwholewallへ足さない。

同node上限でも実nodes/depth/数値/経路が違う。同wall棋力・一般cache/delta速度利益は未確認。4game全slotはNOT_RUN(残枠/時計接続検証費)として保存。成功補充・追加condition/runなし。

## 管理失敗・背景実行・会計

初回search-r1は次自然監督までquiet120+30不足でguardのPopen前に停止。owner投入前確認不足。background exit1/allcleanup/wall4.316586s、元counter欠測/原stderr/receiptを保持し、sourceproofでNN/model0を補足。科学性能負例や成功置換にしていない。元activeで処理済み失敗のpending通知だけcancelし、deliveredとは呼ばない。

新private wait_and_runは自然owned回収と十分窓をPythonだけで待ち、14:17前にguardianを一度だけ呼んだ。wait395.536016sとbackgroundouter397.747073sはscientificguardianwallと別。人数だけのgateではなく既physicalguard/windowを維持し、他owner/周期/運用sourceを変更しない。parity/searchのjob IDをBeadsへ記録してIdle、completionで同savedroleへ再開した。

全2科学5142NN/2.582166s、元50000/240s内、warm/train/GPU/build/game0。max familyRSS806522880<1.75GiB。新16MiB reservation/14MiBguardはexp確認unused155295744から配分し残138518528、旧512等保持/unknown減額/親追加0。必要weights/fixture/数値/Action/全attempt/source/clock/cost/processを保存し、default/privateindex不変更・小archive memberSHA/Gitbyte復元・Beadsbackupへ。science-stop正本は14:12:37点で源/payload SHA、全子wait/currentexact不在を束縛する。将来全host不在は保証しない。

## 主判断・次最大1

凍結valueのnative-hosted数値と合法探索接続は成立した。rootmean教師精度の利益がleaf効用へ移るか、同時間で距離より有利かは未確認。初期rootのdepth2未完は、評価値の分布、αβcutoff/順序、合法生成、入力/cache/eval費の交絡を含む。NNUEの不支持、教師唯一原因、性能最終認定へ広げない。

評価器側は今回のf32/scale/STM/full-deltaを基準として移植・低費用化を検証可能にした。探索側の次最大1候補は233案の「前完成depth最善root手だけ先頭、残stable・全合法」のordering-only対照。同じ凍結評価器/仕事量で完成depth/nodes/leaf/全費、root等値Actionとfail-soft boundを別に確認し、限定policyも合法手除外ではなく順序だけ・推論費込みへ位置付ける。TT/historyや大きい移植は別検証。新対照/対局/再学習は統括の別配分であり、今枠から自動開始しない。

証拠範囲補足: 全root childのexact値/等値argmax集合は未保存（NOT_RECORDED）。選択Action/valueは最後の完成depthに束縛されるが、非最善childのfail-soft boundをexact値として扱わない。counterfactual orderingはNOT_RUN。66archive member復元とGit e86938e8/68path242723B bytePASS、defaultindex不変更を確認。
