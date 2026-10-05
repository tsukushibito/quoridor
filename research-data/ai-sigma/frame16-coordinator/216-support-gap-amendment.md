#216 phase5 — 保存OOF/validationの共通支持・残差差分解

220独立選定案を採用。phase4 λ1 OOF .382828<Dfold .408041だが固定val .548893>D .485147。最大未解決はこの差が共通label-free群の構成か、同じ群内の補正関係か。standard200hidden age/hiddenλ1の追加fitやNNforwardより、現在の保存予測で問える低費用分析を優先。主計画を更新し、同issue/元scope/原phase1/2/3/4scientificsource/result/Git/stop不変更、別support-gap-analysis新source/preregister/result/stopを保存。

既保存OOF λ1/foldD4653とfullprediction λ1/globalD val1248を同元rootmeanにjoin。全train96/val24・rowweight1/(G*n_game)固定。phaseは既early/middle/late、cohort6openingの既label-free6×3=18cell全固定。各セルmass、rows、distinctgames、e=y-Dのmean/RMS、r=P-Dのmean/RMS、cross E[e*r]、conditionalgap=E[r²]-2E[e*r]、corr/zero variance unknown、元signedglobalcontributionを保存。独自のセル内game等重みへ置換しない。OOFはfoldD/OOFpred、valはglobalD/fullfitpredと明示。baseline/model差を隠さない。

全体差gap_val-gap_OOFの記述分解: 共通cellについてsum[(mass_val-mass_OOF)*conditionalgap_OOF]をcomposition、sum[mass_val*(conditionalgap_val-conditionalgap_OOF)]をwithin。片側0massのセルはunmatched signedcontribution sum[valmass*valgap-OOFmass*OOFgap]を別欄、未観測側の外挿/0補完なし。3項の和が全体差に有限一致することを検算。18cellの小標本・特にlate0val保持、群を結果で削除/再定義0。OOFwholepipeline fit72/78game対full96/別baseline、同OOF3λ選択/単partition、val24・再用selectionを残し、within差を純粋covariateshift/teachertruth因果へ変換しない。

費用内でgamelevel fixedprediction pairedbootstrap2000/seed2161605を記述追加: OOF各96game(PminusownfoldD)とval各24game(PminusglobalD)、平均差とpercentile95、係数/λ/folds refit0。固定fit・λ選択を条件とした探索的区間でselection/folddependenceの不確かを全部捕えるとしない。情報量と次判断が変わる範囲を短く示す。

NN/model/forward/optimizer/backward/fit/GPU/teacher/test/game追加0、NN29505/30000不変。元static139.412996/180保持、追加source/preflight上界5s+全math/失敗修復<=15s(実jobhard15、見込5s以下)、20s以内で旧残40.587内、capreset0。CPU2/BLAS1単1/RAM512guard448、X/hiddencopy不要、保存予測JSONLはstream/read参照、current scope+uniqueGit/temp/metadataforecastに追加compact128KiB以内、16MiB/14guard内で直前計測。新予約/旧unknown減額/parent追加0。超過なら具体不足返却、source静的準備・必要保存を進める。

219phase4独立算術と同heavy競合なしを本人fresh admit、正live16monitorownedNone/quiet/currentPIDtick/RAM/storageを直前確認。firstmath07:25/stop07:30/保存07:40、親07:45:50newheavy/07:55:50end維持。216既phase4stop正本/科学payload保存は別に先渡し、全稿gate0。phase5はowner有限自己確認/統括compact読取範囲、219に新算術を要求して旧120resetしない。

結果で変わる主判断: within差が支配し大きなconstbias/clipでは説明できなければ、既入力の補正relationの安定性/履歴や教師noiseを優先問へ、NN容量/readout調整やfreshtest反復を抑える。composition/coverageが支配なら不足群の情報収集/代表分布を次方針にする。game uncertainty大なら分布因果を留保し、cheapfeatureage/既知関係sanityを次に比較。追加実行を自動化せず、観測から主計画を更新する。正式棋力・独立test利益・特徴無効認定0。
