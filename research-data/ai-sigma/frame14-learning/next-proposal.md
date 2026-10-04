goal quoridor-4lc /195 次最大1判別案（提案のみ/起動0）

観測: 3stage train rootmean gameMSE は .00065/.00073/.00178までfitした一方、全固定valのbestは同初期step0。これは学習器がこのtrainの対応をfitできる根拠で、正しい視点・十分な情報・未見教師の正確さを証明しない。候補A=小さいgame集合を高epoch反復して過度に記憶/飽和する正則化不足。候補B=historyを含まないQF1表現/STM view実装又はK64 rootmean教師の不安定性により、未見gameで対応が一致しない。両者が共存する可能性も残す。194のRuleA/648/replay照合やSTM canonical mockはBを制約するが、独立な教師品質/全history表現保証ではない。

最大1対照: 元96train4653行/固定val1248行/同fresh初期SHA/seed19080311/AdamLR.001/2000step×128/rootmean/gameequal/同H32を保持し、optimizer.weight_decayだけ0→.01（Adamの既実装L2）にする。既96-r1の全曲線を0対照としてreuse、新対照1runのみ・sweep0・追加LR0・旧testを設定選別へ使わない。全21曲線/定数/全24valゲーム/全phase/符号/飽和を保存。新bestはval primary gameMSEだけ、同初期step0を含め選ぶ。正則化の改善はAへの感度を支持するが原因確定ではない。改善なしならこの正則化量が支持されないという判断で、B又は容量等の静的独立auditへ次配分を戻す。

費用案: CPU2単1/RAM2guard1.75GiB、学習1jobhard120s（既96実4.63–5.47s程度は参考のみ）、最大379921 sample/warm0。新未使用testは別entropyのfresh24family、6opening-ply各4/RuleA/K64/tau/同生成品質。結果前に所属とlabel-free maskを固定し、train96+全val+開封済旧testの署名集合に対するstate OR history OR actualQF1で露出を別計上。旧testは再開/交換0、旧test labelsを再選定へ入れない。モデル候補をcheckpoint/config/selection/mask/initial/定数とfreezeしてから新testを一度評価。candidate=initialなら実weightSHA予測reuse。新test行数不定につきNN評価capを例えば12000sample/1jobhard120sで別契約固定、超過は欠測停止。

生成1batch案CPU3worker+GPUhost1/VRAM6/RAM6guard5.5/jobhard150s（既194各24game102–123s、新game長に保証なし）。学習と新生成は非重複、自然CPU0監督owned/次予定がhard+30s窓を満たす場合だけ。新test生成が不成立/残費不足ならval対照までの不確かさを提出し、別testへ交換しない。保存は新job raw+metadata+weightsの実forecastを194の直近実量からcoordinatorが配分。新rootmean蒸留候補を棋力へ読み替えず、αβ/対局は自動開始0。現在frame残時間は十分でもこの文書は追加科学許可ではなく、統括の新現在配分が必要。
