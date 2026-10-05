# 凍結NNUE–D同prefix・同100msのpaired leaf比較 — quoridor-4lc.242

frame19のモデル科学は全3job・全8slotを終了し、baseline/candidateともNNUEは2W0D2L、UNKNOWN/NOT_STARTEDは0だった。葉合法存在判定packageを両評価器へ適用したため、この相対WDLの一致からNNUE/Dそれぞれの絶対効用や効率利益の有無は分解できない。旧240の3W1UNKNOWNや旧236の2W5L1UNKNOWNは別prefix/node8192で、直接対照ではない。

## frame19の事前固定と科学停止

原frame19は2026-10-04 22:52:46–10-05 00:52:46UTC、242入口00:22/停止00:28/保存00:38。凍結NNUE12193f32/48772B tensorSHA b81792d5、scale68f8b43a、candidatefreeze2bac8f1f、D係数a=.06038215201109912,b=7.925687690687516を保持した。rootbest-first/TT0/noise0/policy除外0、clone-parent/full-delta数学・RuleA/history/P2は共通。baselineはfullterminal/D重複term、candidateはdepth0 pawn合法存在+fullfallback/D known-nonterminal。

新2familyの合法8/16ply prefixを結果前freezeし、各familyでbaseline–candidate–candidate–baseline、各color/packageの開始prefixを共通化した。独立8openingではなく、2family×2color×2packageの8slotである。両package・両評価器node32768/要求最大depth64・内90ms/外100ms。親t1は完全parse・generation/key/history・mode・有限値/合法完成Action検査の完了時刻、setTimeout callbackや内90msだけを期限内根拠にしない。

接線preflightは2root×NNUE,D×boolean2=8条件、invalid boolean7種、共通完成depth値/Actionとmode対応を有限確認（5500NN/.794409179秒）。旧24064fixture/数値証拠を再用するが、新実装全面認定や未確認時計を旧成果で代替しない。

旧科学stop SHA bc674adf1e461c6df407d0096f14c2ddb87b5cb1aee9c7f7e39859d11d12ae71。source9/payload7のcurrent SHA、全3background.cleanupとprocess.wait/recordedPIDtick不在を有限確認。preflight5500+family0145573+family1107830=258903NN/31.731983437秒、原2mNN/600秒/最多3モデルjobの全3を消費しresetしない。peak familyRSS326377472B、GPU0、旧成功science再実行0。

## frame20管理復旧版

新ユーザー承認frame20開始00:51:02–02:51:02UTCに、後続集計/保存だけを専用frame20-recoveryへ移した。旧科学source/result/期限は変更せず、新forward/arena/model/学習0。中断LLM費はUNKNOWN。旧有効reportは未作成だったため、この文書は旧rawを上書きしない新管理報告である。

新task `frame20-paired-recovery-242-v1` / schema `paired-recovery-v1`、実argv/source_SHA/入力SHA/予期outを結果前Git5972a985へ束縛。正frame20 recovered-running-loaded（scheduler478864/tick41516692・monitor478872/tick41516710）・currentowned/実foreignCPU/GPU/RSS/保存・goal/本人nopauseを直前admit。LLM人数gateは置かず、旧quietや古い運用bindingを代用しない。

専用NN0算術最多1jobは01:11:53.124824→01:11:53.198355、PID491747/tick41572665、wall.073539888秒/peak26501120B、exit0/wait/exact不在、NN/model/GPU0。出力task/schema/inputSHA一致もpost照合した。source/math60秒と管理120秒、新予約0・旧16MiB/14MiBguard内で停止保存する。

## 全予定サービス・clock・探索量

全338handが保存上の親完全検査t1<=100ms、generation/id/key/history/mode・有限合法完成Action・partialdepth不採用。latereceived/latevalid/UNKNOWNは0。合法性の根拠はimmutable arenaの実合法Action受理と保存validationであり、新独立RuleA replayやteachertruth再認証ではない。全32768 node上限到達は0で、この範囲ではnodecap打切りが同wall効用を制限した観測はない。

| variant | evaluator | accepted hand | 平均完成depth | processed | NN | cap到達hand | 最小clock余白ms |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| baseline | NNUE | 80 | 2.825000 | 142378 | 107899 | 0 | 2.911834 |
| baseline | distance | 80 | 4.562500 | 193761 | 0 | 0 | 5.425699 |
| candidate | NNUE | 89 | 3.808989 | 185829 | 145504 | 0 | 6.123005 |
| candidate | distance | 89 | 4.797753 | 270670 | 0 | 0 | 4.886245 |

深さの全分布/typedstop/partialdiscard/searchwhole/clock spansは stats-v2.json。深さ64の強制終端探索等の外れ値があり、平均だけでhorizon改善を判断しない。全handで到達State・手数・仕事量が違うためaggregate depth/node比を同仕事量の因果へ変換しない。baseline160hand/candidate178handで、候補の総wholewall増を遅さ・同時間棋力損失と解釈しない。

## 同入力とpaired game

各colorのboard+side+canonical RuleA count-history一致入力だけを対応付け、全128組はexactprefixも一致した。共通完成depth481比較で最大value差0・Action差0。全exactchild/等値argmax集合は元ログでNOT_RECORDEDのまま、nonbest failsoftをexactへ格上げしない。異なる最終完成depthで採用Actionが違うことと、同深さで値が不整合であることを分ける。

| evaluator | matched入力 | candidate深い/同じ/浅い | 平均depth差 | 最終Action変化 | 共通depth比較 | 最大値差 |
| --- | ---: | --- | ---: | ---: | ---: | ---: |
| NNUE | 64 | 4 / 59 / 1 | 0.046875 | 1 | 178 | 0.0 |
| distance | 64 | 4 / 58 / 2 | 0.031250 | 0 | 303 | 0.0 |

| baseline / candidate slot | NNUE side | NNUE結果 | hand数 | matched入力 | 最終全prefix一致 |
| --- | ---: | --- | --- | ---: | --- |
| 1 / 2 | 1 | L / L | 46 / 46 | 46 | True |
| 4 / 3 | 2 | W / W | 50 / 50 | 50 | True |
| 5 / 6 | 1 | W / W | 33 / 51 | 1 | False |
| 8 / 7 | 2 | L / L | 31 / 31 | 31 | True |

3paired色位置は全棋譜が一致。唯一異なるslot5/6は最初の同入力でNNUE最終完成depth/Actionが変わり、以後手数33→51と到達局面が分岐したが、両方Wだった。対応input/共通depthを one-divergence-handoff.json に保存し、後段の葉意味/表現診断へ必要範囲で渡せる。1例や4paired位置から因果唯一・一般棋力/NI/最高性能を認定しない。

## 費用・保存・次判断

原science guardian31.731983437秒、family controller30.762177705秒、background46.625432866秒、各model init-to-ready28.508820/31.301879ms、Python controlwait合計約.00613018秒。重複spanは合算しない。cache/JIT/ABBA順・同heldworker・host状態と小標本の限界を保持する。旧240固定仕事59.20%/NNUE54.38%/D65.14%の節約は別測定で、今回同wallは同horizon/jobwallの倍率を測るものではない。

必要旧raw2JSONLと新statsだけの小packを作りmemberSHA/byte復元する。旧source/Git/原payloadをreadonly参照し全archiveを複製しない。新source停止・process/compact・Git必要bytes/index不変更・notes/close/backupの最終receiptはframe20-recoveryに保存。old16MiB予約/14MiBguard維持、未知保持減額/親追加0。旧229final独立NOT_RUNと旧openedtest/173非読取を保持する。

次最大1案は既配分244の葉value/history診断へ、この唯一の同入力Action分岐を共通完成depth1と追加完成depth2の例として渡し、learned leaf意味/表現と探索効用の競合説明を低費用で制約すること。新arena/TT/policy/学習を自動開始しない。WDL一致だけで更なる速度改善やNNUE学習の価値を否定せず、同wall絶対棋力の認定には追加の結果前固定評価が必要である。
