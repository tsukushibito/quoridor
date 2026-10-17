# 零在庫P候補：元384callの有限費用解析

Pを現役候補として保持する有限支持は得られなかった。主対象のLMR ONで、BEST43 NNUE・固定Dの双方が事前条件「P whole中央値<=Mかつ<=O、全固定rootで両Pがいずれの対照中央値の1.10倍も超えない」を満たさない。今回のP撤去が妥当であり、元411 Mとenable既定OFFを維持する。これは有限8root・二反復の保持判断で、一般速度・棋力の優劣を確定しない。

元の一回の実行だけを使った。各層O→M→P→P→M→O、各pass8真正prefix×cold/warmの16calls、4層で384calls/192sessions。Control/PVS/TT1048576、BEST43または固定D(0,8,tanh)、D8/各4M nodes、時間上限なし、近似・診断・depth callback OFF。追加run、warmup、refill、Search/native/model/forward/game/fit/test/solver/BFSは0。結果と明細は[result.json](result.json)、[passes.csv](passes.csv)、[calls.csv](calls.csv)に固定した。

| 評価器 | LMR      | O whole中央値 s |       M s |       P s |      P/M |      P/O | 全96callsのD8完了 |
| ------ | -------- | --------------: | --------: | --------: | -------: | -------: | ----------------: |
| BEST43 | ON 主    |       10.906673 | 10.946294 | 10.927163 | 0.998252 | 1.001879 |                96 |
| 固定D  | ON 主    |        6.377468 |  6.340758 |  6.377624 | 1.005814 | 1.000024 |                84 |
| BEST43 | OFF 補助 |       14.821315 | 14.879067 | 14.676180 | 0.986364 | 0.990208 |                84 |
| 固定D  | OFF 補助 |        6.429707 |  6.504987 |  6.604298 | 1.015267 | 1.027154 |                84 |

両Pが1.10×O中央値を超える主対象rootはBEST43のr3/r4/r5/r7、固定Dのr3。BEST43 r4ではO中央値39.642msに対しP=55.905/50.020ms、比1.4103/1.2618。固定D r3はO=41.766msに対しP=49.808/48.439ms、比1.1926/1.1598。主対象で両Pが1.10×Mを超えるrootはないが、「いずれの対照」条件なのでO側の違反で不支持になる。全層・全rootの二反復と違反は[root-checks.csv](root-checks.csv)。補助BEST43 OFFの中央値改善もroot条件を満たさず、主対象の代用にはならない。

実際は348callsがdepth8 COMPLETE、36callsがUNKNOWN:NodeLimit。全UNKNOWNは残壁6のr0で、BEST43 OFFと固定D OFFはcompleted_depth6、固定D ONはdepth7、各12calls。各4M nodesを使い切った時点の返値をD8完成値に置換しない。全実nodesは243,362,776/上限1,536,000,000。未完了一覧は[unfinished.csv](unfinished.csv)。全24operation PASSはソフトと清算の成立を示し、384件D8完了を意味しない。

同評価器・LMR・方式・root・温度の二反復192組は、valuebits/action/PV/全work/完成深さ/stop/root完全history/親不変などの非時計値が192/192一致した。全384callsがparent_unchanged=true、返却Ok、選択手は実root合法手集合内。root identityと完全historyは全方式・passで元8prefixと一致した。[repeat-verification.json](repeat-verification.json)と[verification.json](verification.json)に記録した。方式間はproofと選択木が変わる。主対象M→Pの16対応call枠ではBEST43でvaluebits4/action2/PV10、固定Dでvaluebits4/action0/PV8が異なるが、完成深さとstatusの違いは0。一致を強制せず、旧い木や反実仮想の未訪問nodesへ換算しない。[cross-method-output.csv](cross-method-output.csv)は同じ16枠の比較で、独立16局面の統計ではない。

Pのcommitted return originは次のとおり。各行は同層・P二反復32callsの実event合計で、M/F2/Pathのfresh returnとtyped TT再用を分けた。全384callsでorigin合計=proven、TT returns<=raw hits<=probesを確認した。

| 評価器/LMR | fresh M | F2 即goal | F2 sealed | fresh Path | TT return | proven合計 |
| ---------- | ------: | --------: | --------: | ---------: | --------: | ---------: |
| BEST43 ON  |   7,242 |         0 |         0 |     12,956 |     4,760 |     24,958 |
| 固定D ON   |   8,564 |         0 |         0 |      6,068 |     5,460 |     20,092 |
| BEST43 OFF |  12,684 |         0 |         0 |     63,250 |     2,000 |     77,934 |
| 固定D OFF  |  15,112 |         0 |         0 |      8,590 |       536 |     24,238 |

主対象のM provenはBEST43=15,584、固定D=15,678。Pではproofが増えたが、M対比の実visited nodes減少はBEST43 16,825,636→16,783,678（0.249%）、固定D 17,682,922→17,649,618（0.188%）。通常evaluation eventも12,255,116→12,235,124（0.163%）、12,575,272→12,560,968（0.114%）にとどまる。これらは実行された別々の木の記述値で、Pが省いたはずの未訪問nodesやphysical NNUE head数を示さない。[work-comparison.csv](work-comparison.csv)。

主対象Pのstock0 opportunitiesはBEST43=49,212、固定D=355,662。Path tests/passesは37,210/12,956と341,638/6,068で、残り24,254と335,570はintermediate条件で拒否された。全P層でmap_missing/invalid_map/opponent_first/endpoint/history rejectsは0。一般history checksは主対象で20,198と14,632、TT再用の二重scanを含めない。F2の成功・return・二key count queryはいずれも0で、この有限費用結果からF2の実用効果は判断できない。OFFのsafe_race counter0は計測無効を示し、零在庫機会が存在しなかったことを示さない。全eventと拒否分母は[counters.csv](counters.csv)。異なる評価器・LMR・木の分母を合算した成立率や独立局面率は作らない。

wholeは結果前に固定したnative子guardian wall。実BUILD commit `eb30b2ea08059d7ae8cd535d3cf0a6fa5be4ca57` のmeasurement.rs（107393B、SHA256 `f3ba22666ee58d2b8b01d1ec1dcc03d8eead3e2c729e391b6d273cb72e3aa614`）で、resetはroot_whole開始前、session teardownは両callの外、root_body_including_journalはprepare/call/finish_call/publishを内包することを確認した。foreign patchはこのpathを変更しない。JSONLはpublish時点の行なので自身のjournal時計を持たず、追加時計の正本result.measurementsとそれ以外の全384行が一致する。nested Search/driver/setup/drop時計を重ねて加算しない。

全24passに正しく対応する8reset/8teardown/16call bodyが存在し、native wall−8session bodiesの残差は35.562478〜78.973769ms、負残差・欠測・session不一致は0。各rootに1/8、各cold/warmに1/16を等配し、root8件・call16件の配賦和を別途Decimalでnative wallに照合、誤差<1e-12s。元outer jobの351.4671437400sは一度だけ記録し、内包するnative24pass合計231.5830703708sを足さない。[input-binding.json](input-binding.json)に実source抜粋と事前whole単位を保存した。

下表は主対象で各温度16calls（二pass）の配賦whole合計/2、すなわち8calls/passの平均。coldにreset、warmにteardownを配賦した固定会計単位で、孤立したroot/predicateの実測費ではない。

| 評価器/方式 | cold s/pass | warm s/pass |
| ----------- | ----------: | ----------: |
| BEST43 O    |    5.782678 |    5.123995 |
| BEST43 M    |    5.850908 |    5.095385 |
| BEST43 P    |    5.842057 |    5.085106 |
| 固定D O     |    3.358019 |    3.019450 |
| 固定D M     |    3.400255 |    2.940503 |
| 固定D P     |    3.409238 |    2.968386 |

Pの直接bodyはBEST43 cold/warm=5.553480/5.033644s、内包Search=5.478645/4.983778s。固定Dではbody=3.136321/2.929853s、Search=3.093514/2.877224s。cold→warmは同sessionのTT等を引き継ぐ順序であり、独立反復ではない。補助固定D OFFのOはwarm配賦3.340133sがcold3.089574sより長く、warmが常に速いわけでもない。[temperature.csv](temperature.csv)に全層の直接時計と仕事量を残した。

root悪化にはsetup配賦と短時間変動も含まれる。例としてBEST43 ON r4のP第1passは、両call body合計7.598msに対しreset39.816ms、teardown2.061ms、残差配賦6.430msでwhole55.905msとなる。O第1passのbodyは7.998ms、whole40.001ms。従ってroot比1.4103をPath predicate単体の41%増と解釈しない。whole条件の不成立はそのまま維持し、結果を見てSearch-only時計へ差し替えない。二反復の小差、OS/時系列変動、孤立したmap/history/predicate費、連続peak RAM、一般速度・棋力、未完了D8、金銭費用は未確定/UNKNOWN。

正本collection SHA256 `ac5c4271b9e9278b2bfabb04561212b6c0bc4f7e013ea06165aa877e6cd93933`（337942B）と、その実BUILD SHA256 `368944551cc2e33e35af014f4d1fa92e8635c258b3f89d852a29f5abba123810`、image SHA256 `30c1746ae0b3b9a76e33e0d9d3fe7ba8c88c2372c4a8e9378ecc42ef1d072f46` に結論を束縛した。モデル/実行image payloadは読まず、実manifestのrefとnative実command identityを照合した。182個の実消費refをbefore/afterでSHA/bytes/modeまで一致確認した。最初の保存解析はsettings.jsonを生configと誤認したmetadata assertionで停止し、失敗source/log/receipt/STOPを保持した。wrapperとRootSpec.jsonl_match=null、Request.observe_lmr=falseのnative既定を明示比較して修復しただけで、native再実行はない。

元Build tool-drift FAILED、Root collectorのmetadata修復、全旧FAILED/R1R2/返却NULL対disk/費UNKNOWN、十一新検査の来歴制限、過去のUSERPAUSE/default/model/sealを維持する。旧solver/171/成功suiteやwithdrawal差分を再reviewしない。実Mainソース読者は[Main-source-reader-STOP.json](Main-source-reader-STOP.json)で停止を固定済み、後続は私有保存表のみ。資源・最終ref・本人close/backupは[completion.json](completion.json)と対応guard STOP、実量一度の記録は[最終保存量](../cost-final-storage.json)を参照。RootがMain/Git/ソース保持・撤去と正本への統合を所有する。
