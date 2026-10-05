# frame14 新現在配分: 凍結QF1下層＋head-only残差1条件
担当hypothesis saved01a0f31c-2e4b-7170-82c5-69e1428c2418、worktree /workspaces/quoridor/.worktree/ai-sigma。既frame14内、parent CPU4/RAM8GiB/保存12GiB/03:20:36終了不変。旧200を有限受入れ200-finite-acceptance.jsonで本人close+backup（現在の実taskturnで実施し専用turn無し）後、ready/show goal+self/no pause/本人割当→claim/新静的実開始を報告。

## 問い・owner
200のdistance-fit初期は新test rootmean gameMSE.371023対定数.770258で有限支持、全層residual LAST.663064で悪化、BESTstep0は残差増分0。202提案を採用し「同初期のQF1 transformer/hiddenを固定し出力headだけ学習すると既distance基準より未見validationに移るか」を1条件で安く判別。低容量感度であり容量不足/過学習/教師noise/分布差の原因確定ではない。λ.1推論縮小・ordering/追加幅LRtarget sweepは保留、同時実行しない。
単writer tools/ai-sigma-qf1-head-control/、research-data/ai-sigma/frame14-head-control/、models/experiments/nnue/frame14-head-control-*、docs/reports/ai-sigma-hypothesis-head-control.md。元200/sharedtrainer/194teacher/mask/旧173正式holdout/旧testsource結果はreadonly。新shared依存/環境/モデルeffort/製品編集0。

## 結果前固定
200のhead0初期checkpointの実tensorSHAを再用しFT+hidden全tensorを固定。H32/共有312features/hidden32・同STM-f32 input/距離coefSHA77ce9e79/settings115181bf、same freshseed19080311/Adam LR.001 WD0/2000step×128=256000train samples/gameequal/rootmean、step0含む21曲線、same stage train96=4653とval24=1248/max96mask10b502cdは維持。train初期は200のinitialweightをweights_only CPUでロードしhead0及び全対応tensorを確認、学習対象をout.weight/out.biasだけ33parameterへ限定。FT/hidden/距離coeffはrequires_grad=False、optimizerもheadのみ。source hashと初期SHAを結果前bind、下層のlast/checkpoint tensor不変をNN0 byte比較で確認。readonlytrainerを私有薄adapterでreuse、sourcecopy/全raw複製しない。
演算は元200と同distance+super tanh residualをouterclip[-1,1]、terminal教師mask/視点も原条件。head0/outerclip勾配制約は記録。変える因子はtrainable parameter subsetだけ、初期からLAST frozen下層を勝手に使わない。NN0 AST/argv/mock/schema、元source/hash、入力targetが原train/valだけであることを先確認。追加forwardは初期eval5901の既課金内で有限distanceparity確認し、成功科学再学習0。デバッグattemptは総予算内typed保存、有界修復と同run新版を区別。

## 曲線・gate・test
同全21stepのtrain/validation rootmeanと真z/sign/saturation/game/cohort/row/gameequal/定数を保存、same fullresidual200曲線と比較（旧testlabels/results再読0）。candidateはval primary gameequal rootmean MSEだけbeststepを選び、初期step0を含む。固定gate四条件: (1)beststep>0かつweightSHAがdistanceinitialと異なる、(2)valgameMSEがdistanceinitial.48514681311997876より1e-4以上低い、(3)finite coeff/input/下層不変schema PASS、(4)科学/source子stop/currentexact無し。旧200/197gateを変更せず新条件。gate-result/evaluator-settings/checkpoint/weights/initial/source/coeff/val/mask/stop SHAをexperimentへ停止handoff。未達ならfresh全24NOT_STARTED/NN0で終了し閾値緩和/追加学習0。
GATE_MET時だけexperiment別fresh24testを生成、oldtrain96+全val+開封済oldtest24+distance-test24のlabel-free署名に対するstate OR history OR actualSTM-f32 input露出mask。testmetadata+mask+owner advertised sealedlabelpath/hashだけ先受領、testlabel本体/hash再計算はcandidate/evaluator/config/coef/selection freeze後まで0。candidate/BEST/LASTとdistance-onlyを同新test一巡で評価、BEST= candidate予測reuse/NN実unique表示。distance/constantは解析NN0。最大3unique/12000samples・hard120s。paired24family bootstrap2000固定seed20480311、rootmean蒸留と真z/signを分け、group/0eligible/全予定/欠測・不確かさ保持。testを選定/追加trainへ戻さず旧test再開0。改善でも棋力/NIではない。

## 費用・期限・保存
CPU2単1/torch1/GPU0、RAM2GiB familyguard1.75。学習1job120s＋one-test120s、heavy計300s/sample総500000（train379921+test12000+debug上限を別表、超過ならtyped停止）。static180s/管理計600s、GPU生成と重NN非競合・本人freshcurrent/PIDtick/RAM/pause/所有を直前admit。自然監督CPU0は強制interrupt/tick/周期変更0。
新8MiB subreservation（guard6MiB/current+uniqueGit/tmp/残metadata先forecast5MiB）はhyp既64MiB内の確認unusedから配分。old195/197/200保守combined49,567,818B+8,388,608=57,956,426<58,720,256B guard、旧未知減額/parent追加/証拠削除0。必要weightはarchive lossless2-3表現memberSHAで小保存、曲線PNG/SVG最低必要・全21JSON/CSV、privateindex0/defaultindex保持、CAS localGit/必要bytes復元/Beads backup。
新学習開始02:25UTC/学習停止02:30、条件付きtest新開始03:00/科学stop03:05/全process03:10/最終提出03:15で親早側。receipt15分内（science成功と区別）、最初学習actualstart/stop/gateを即報、各commandは本人受領+60分の早側も守る。deadline/資源/所有不明は該当job停止。改善なしでも有限不支持で記録してclose可。NNUE目標からの次最大1だけ報告、自動新run0。
