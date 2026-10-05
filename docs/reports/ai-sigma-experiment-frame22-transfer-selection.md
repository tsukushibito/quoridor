# frame22 保存予測の転移不足と次介入 / quoridor-4lc.278

次の最大1候補は、既D保持モデルの出力補正に固定の正則化を加える比較とする。新family追加だけではBESTの転移改善を認めず、保存された補正は新selectionで弱いalignmentと大きい片側biasを示した。これは過適合・校正を制約する低費用の介入を支持する選定資料であり、教師・QF1表現・データ量の原因を一意に定めない。本課題で実施したのは保存予測のNN0算術のみ。

## 対象・原重みと有限照合

274 A/Bは同initial ec4167、同old scale、Adam LR1e-4、game等確率sampling、batch128、seed19080311、256000 seen。Aは旧96game4653行、Bは旧96＋新36game5981行。同sampling方式でも行集合・epoch・batch SHAが変わり、純粋な量の効果とはしない。A/BのBESTは旧選定validationで200stepを選択している。ここでnewselectionを使って再選定していない。

新selectionは12game392行、全行適格、欠測game/0eligible/除外0。原global rowweight `1/(12*n_game)`を全bin内でも保ち、群内game再等重みへ変更しない。五つの保存モデル予測をそのまま読み、274のgameMSEへabs1e-12で一致した。全group/phase/cohort/残壁stock/距離差の排他的binはmass合計1、signed contribution合計が全体gapへabs1e-12で戻る。

Dは保存Initial予測を参照した。別解析f32 Dとの約3.12e-9の集計差を補正・置換していない。モデルimport/forward/fit/新入力生成/再教師/対局/GPU/buildは0。canonical metadataはid/group/splitと保存rootmean/zを一致確認して必要selection行だけjoinした。元cache全コピーはない。

## Train-fitと転移

| モデル | train gameMSE | 旧val gameMSE | 新selection gameMSE |
| --- | ---: | ---: | ---: |
| A Initial | .421411 | .489404 | .392634 |
| A BEST200 | .385503 | .478510 | .399633 |
| B Initial（combined train） | .409555 | .489404 | .392634 |
| B BEST200（combined train） | .380739 | .479679 | .399173 |
| A LAST2000 | .030967 | .849425 | .979297 |
| B LAST2000（combined train） | .032026 | .679028 | .921886 |

後半の強いtrain fitとval悪化が共存する。Bは後半悪化を小さくしたがBEST旧valはAより+.001168悪く、新selectionのB−Aは−.000459。固定予測gamebootstrap95%区間は[-.010581,.009479]で0を跨ぐ。新36familyが不必要、教師全無効、NNUE一般性不足という判定はしない。

## 補正の方向・振幅

`e=y−D`, `r=N−D` として `MSE(N)−MSE(D)=E[r²]−2E[e*r]` を原重みで保存した。

| モデル | gap | 変位 E[r²] | alignment 2E[e*r] | r平均 | r RMS | 中心corr(e,r) | 改善/悪化game |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| A BEST | +.006999 | .007239 | +.000241 | +.077484 | .085084 | −.155716 | 6/6 |
| B BEST | +.006539 | .006185 | −.000354 | +.072611 | .078645 | −.185122 | 6/6 |
| A LAST | +.586663 | .441846 | −.144817 | +.031906 | .664715 | −.178023 | 6/6 |
| B LAST | +.529252 | .341597 | −.187656 | +.038700 | .584463 | −.262303 | 5/7 |

BESTの補正は正方向へ寄り、連続残差情報との中心相関も負。B BESTは平均成分の二乗が変位項の約85%を占めるが、biasだけを原因と認定しない。LASTは大きい振幅と逆方向alignmentが両方悪化へ寄与し、単純な定数biasでは説明できない。BESTの固定gamebootstrap区間はA[-.010062,.024511]、B[-.006643,.019668]で0を跨ぐ。LASTはA[.013457,1.209712]、B[.090948,1.021076]。12game・固定fit・既選定条件に依存する探索的区間で、selection/teacher不確かさを全て捕えない。

原row符号率はD .724490、A BEST .767857、B BEST .750000。今回の原game重み符号率はD .783932、A BEST .819542、B BEST .807450であり、分母の違いを保つ。符号率の改善をrootmean MSEの採用基準へ交換しない。今回 `abs(prediction)>=.99` はD/BESTで0、A/B LASTの原game重み率は.081107/.057524。これは274の既saturation定義・row分母とは別診断で、元raw counterを変更しない。

## 群寄与とcoverage

phaseは既sourceと同じopening ply<20、middle20–59、late>=60。壁域はQF1 `290+selfremaining`, `301+oppremaining` のstock合計で、placed wallsや複雑さではない。距離差はSTM f32の `80*(opp−self)`、[-1,1]境界はf32誤差1e-5を許して分類した。これらはラベルに依存しない固定分類。

| 群 | rows / game | 原mass | B BEST signedgap | B LAST signedgap |
| --- | ---: | ---: | ---: | ---: |
| opening | 48 / 6 | .090379 | +.001297 | +.063143 |
| middle | 314 / 12 | .872026 | +.005487 | +.450897 |
| late | 30 / 2 | .037595 | −.000245 | +.015212 |
| remaining stock0–5 | 298 / 12 | .834785 | +.003790 | +.377964 |
| remaining stock6–12 | 94 / 4 | .165215 | +.002749 | +.151288 |
| distance difference<−1 | 147 / 12 | .383257 | +.026441 | +.178492 |
| distance difference[-1,1] | 127 / 11 | .293209 | −.001777 | +.261466 |
| distance difference>1 | 118 / 12 | .323534 | −.018125 | +.089295 |

残壁13–20は観測0、lateは2gameに限られる。複数軸は重複するため行間のsignedgapを足して独立原因へ変換しない。各軸内は合計が全体へ戻る。

B BESTの悪化はfamily46/37/41等へ分散し、各原signedgap+.004311/+.002943/+.002811。一方family43/40/45等は−.002877/−.001140/−.001117。最大1gameだけで結論を出さず、全12gameをresult.jsonに保存した。LASTの大きいlossはfamily46/37などへ集中するが成功選別や事後除外はしない。A/B両BESTは不利距離域で悪化、有利域で改善しており、単に特定phaseのみの障害とはしない。

maskはstate/history文字列/actualSTMinputのOR一致0。history形式互換はUNVERIFIEDで、fullhistory/countは欠測。同history非露出、全state独立、IID、代表多様性を保証しない。新selection12gameは既開いた選定資料、未見test0。6opening cohortすべて各2gameだが長さ・到達分布は異なる。新tau1全plyと旧first16後argmaxの分布差は保持する。

## 競合と次の一介入

候補(a)の**出力補正正則化**を第一候補にする。未来条件案は同B5981行・同game sampling/initial/scale/seed/batch/optimizer/256000seen、同zero4/H32に対し、lossを `E_game[(N−y)^2] + 1*E_game[(N−D)^2]` とする一条件。Dは同f32距離式を固定し再fitしない。原200stepをprimary、同10点curve/旧BEST方式をsecondaryとし、新λ/幅/点/seedを結果後追加しない。現在のsource実装・fitはNOT_RUNで、統括の具体配分が必要。

判断が変わるのは、rを弱めるだけでなく旧valと新selectionのDに対するgapが改善し、方向/片側bias・game別寄与も改善する場合。Dへ戻っただけでは距離を超える情報を認定しない。両選定資料を再用する探索的対照で、独立評価・棋力・leaf意味は別。改善が無い又はtrainfit低下だけなら正則化反復を止め、教師安定性/位置付き経路情報の順位を上げる。

(a)ゲーム等重みは既sampling済みなので新介入にならない。幅増はtrainfitが既に高い現証拠では先行しない。単なるLR sweep・係数の事後縮小選別も選ばない。

(b)位置付き経路場・壁効果は有力。265の固定source-mapはSigma751186の全goal距離場とClaustrophobia ae093653の距離場/経路membership/legalwall等を区別して記録する。QF1は全駒・配置壁・残壁疎IDとpawn地点の距離2値で、全map出力を直接入力していない。DAG4追加BEST利益不支持を全経路特徴棄却へ広げない。ただし表現追加はnative全mapの取り出し・更新・差分・モデル容量・学習量の費と交絡を伴う。277は戻りcontextを保持しなかった親計時で不成立、費用順位/TT機会は未実測。489wall-change/14non-changeのNN0経路検査は費の大小を保証しない。追加native費UNKNOWNとして今回は低費用正則化を先にする。参照AIの採用を設計T1へそのまま移植したと推測しない。

(c)274推薦の固定序盤K64対K256教師安定性は有力な代替。旧序盤rootmean-z誤差の大きさとK64教師の不確かさを保持する。新selectionのrootmean-z原gameMSE .116570、符号一致.966905はteachertruth/leaf妥当性の証明ではない。一方今回の補正lossの主signed量はmiddle、BESTで既に片側biasが強く、同teacher/表現/native経路を変えずに転移を制約する(a)の方が今回直接の問いに安く対応する。正則化が改善しなければK256安定性か同入力・同horizonのleaf接続診断を再検討する。rootmeanはMCTS集約、zは単game結果であり、両者の差から誤教師と断定しない。

| 次案の費（未来の未測見積） | 準備/検証 | 科学 | 保持 | native同時間費 |
| --- | --- | --- | --- | --- |
| (a)固定lambda1出力補正penalty | 15–25分、recipe/parity数秒 | fit5–10秒＋既評価parity量、274 B4.93秒参考 | 2MiB目安＋既入力共有 | 同shape/入力・forward数学、追加特徴演算0の設計。値差による枝刈り費UNKNOWN |
| (b)位置付き経路場1群 | field/schema/P2/full-delta/build30–60分 | 同256kseen対照とnative費probe別配分 | fullmapsは追加RAM/保存UNKNOWN、まず必要統計のみ | 277計時不成立につきUNKNOWN |
| (c)固定root K64/K256 | 274見積10–20分、必要有限資格 | 候補24root×4seed warm含上界30912NN、30–120秒未測 | 1MiB目安 | teacher backendbatch1費、leaf速度利益は未測 |

これらは実行許可や実費ではなく比較の見積。今回の次案を実装しない。新data生成は273の有効全guardian費と独立48familyを根拠に費用面では可能だが、BEST転移が改善しなかったので増量のみを固定工程にしない。全候補agendaの探索ordering/PVS/TT、合法/評価cache、量子化、教師/学習/表現の競合を保持し、探索高速化単独を目標にしない。

## 実行・不成立・停止・所有

278ready/showgoal+self/nopause/本人assignedを確認して13:28:41 claim。r1入口は全hostprocess RSS9.73GiBを研究8GiBへ誤比較しrefusalした。科学/解析0、0.119237秒、元source/preregister/process/admission/stdout/stderrをr1として保持。研究外editor等を含むallhost RSSと研究currentをprospective r2で分離した。foreign実script位置を分類、未知foreignscientificは拒否、研究runtime/science RSS＋自己512MiB上界/host MemAvailable>2GiBを確認した。perprocessRSS重複のあるallhost和を排他実メモリと呼ばない。

r2は13:33:47.410084–13:33:47.633876、CPU4単1/RAM512MiB/GPU0、0.223875秒、peak19,312,640B、exit0/wait/exactabsence。frame22 current24hash全一致、正scheduler1233793/45593355とmonitor1235182/45599721、running/ownedNone/実foreignscience[]、scope保存をfreshbindした。これは点確認で未来free保証ではない。モデル/ML/forward0。

Pythonは担当sourceのみ現Ruffでformat→formatcheck/lint PASS。既予測metric一致・元mask/metadata join・allrow/group・排他的分解が今回の必要検証。独立した再forwardや新leaftruthはNOT_RUN。測定済2entry wall合計.343111秒、source/管理の未測読取・LLM費UNKNOWN、90秒source/解析と60秒管理の上限を保持し旧273費をresetしない。

新1MiBは旧273data128MiBの確認unusedから移転し、旧273127MiB＋2781MiBで総128MiB不変。旧273actualforecast21,696,512Bを保持しunknown減額0。current＋必要Git/temp/metaforecastと全停止/hashは本scopehandoffに記録する。Git/index操作は統括のみ。

273教師生成は同actorの自己証拠、274モデルの保存予測算術は別owner入力を検算したowner278証拠。研究チーム外の独立認証・独立棋力PASSへ広げず、最終配分は統括が行う。必要source/payload/元失敗を停止版で引き渡し、本人notes/close/backupを同実質turnで完了する。最高棋力goal、旧229最終独立NOT_RUN、旧費/予約/期限は不変更。

## 13:40以後の統括採択・新計測point（管理追記）

統括から278推薦の固定lambda1 output penaltyを280 hypothesisへ別実配分したとの通知を受領した。fixed200step primary、2000step/256000seen secondary、teacher/nativefeatures不変更。278の保存予測算術と280実装owner自己検証は別で、統括がsource/採否reviewを行う。採択は本278の追加fit/forward許可ではなく、新科学0・本人closedを保持する。

277のprospective修復actual-child計測について、統括新報告pointはmap構築66.73%、sorted IDs10.42%。原親計時不成立とその費UNKNOWNの記録を上書きしない。これは正しい移行先についての新費観測として順位の根拠を更新するが、wholealpha改善率や新feature増分費は未認定のまま。279 wholemap bitparallelは別scope配分で、本278はRust/feature源へ編集しない。

K64/K256×4repeatの固定24root教師安定性案も同候補集合へ含めた上で、今回の補正bias/振幅と弱alignmentから(a)を推薦した。teacher seed内分散/K差が大きいことが別配分で観測された場合、又は固定penaltyがrを抑えるだけで両選定集合のDgap/方向を改善しない場合、教師安定性/leaf接続を次優先へ戻す。位置付き経路場は情報増分とnative追加費が対応して支持されるときに再検討する。高K・平均・単game zも真値ではない。

この追記は新解析job/新予測/条件追加ではなく、統括配送pointの受領と採択境界の記録。旧stop/source/process/必要archiveと278 NN0/全費90秒上限は不変更。
