# OOF利益と固定validation未達の次主配分 / quoridor-4lc.220

2026-10-04 frame16、hypothesis独立静的見解。受領07:04:27 UTC、ready/show goal+self・no pause・担当を確認して220 claim、静的開始07:05:47。218はclosed/停止版readonly。216公開sourceとcompact resultの既存fieldだけを読んだ。今回の新科学CPUjob/計算解析job/NN/model/torch/forward/train/teacher/test/GPUは0。以下数値はproducer公開値で、219独立支持やowner最終handoffを未確認のまま独立再算一致と呼ばない。

**次の最大1配分は、保存OOF/固定validationの共通群・支持域による残差gap分解を先に行うNN0診断を推す。standard200 hidden readoutの新forwardは保留する。** ローカルに有効な小実験かどうかと、今のNNUE目標へ判断を進める優先順位を分ける。

## 大きい不足

raw CVのλ1 OOF gameMSE .382828 < foldD .408041だが、fulltrain-fitのval .548893 > D .485147。これを直ちに「学習可能だがvalidationだけ分布が違う」と確定できない。単foldpartitionで3λからOOF最小を選ぶので、選定したOOF値には条件選定の楽観が残る。OOFはraw626を使い、D・mu/std・ridgeを各foldのtrainだけでfitしているため、learned encoderがheld gameを先に学習したwholemodelcrossfitではない、という欠点はこのraw方式には当てはまらない。一方、OOFのfit母集団は72/78game、fullfitは96gameで、係数・D・尺度が違う。これはOOFとval差の交絡であり、分布変化だけの因果比較ではない。

公開exposure診断はstate OR history OR actual STM-f32 QF1入力の完全一致を調べ、5fold heldout共有row0、固定val共有row0を報告する。完全重複による説明はこのproducer検査の範囲で弱まるが、近傍状態・組合せ支持域・同familyの扱い・履歴で同じ入力へ対応しないtarget差・teacherノイズを排除しない。OOFを独立testや最高棋力効果へ拡張しない。

重要な既存証拠は、λ1 OOF利益がearly phaseに集中していること。公開signed contributionはearly −.025802、middle +.000499、late +.000090、残壁stock bin1は−.019654、opening16は+.015285と逆方向である。全groupを保持した集計なので次の低費用診断の入口になるが、最良群だけを評価対象に選び直さない。train96/val24はopening6cohortを均衡させたgame分割なので、単にopening混合比が違うという説明より、同cohort内のphase/state支持・残差関係の違いを調べる方がよい。

## 最大1方法：保存予測の群構成・条件内関係を分ける

対象を結果前に固定する。λは既選定1を保持、OOF96game4653rowのfoldD/OOF predictionと、fullfit val24game1248rowのD/full predictionをそれぞれ対応するteacher rootmeanへjoinする。旧test/正式173/新教師は不要。OOF/full-predictionsと既216のmatched label-free group metadata/targetからの読み込みだけで、新model・forward・fit・λ選定は0。ファイルのimmutable path/SHAとjoin IDは216ownerが束縛し、全handoff/219全文を入口gateにしない。

primary群は既opening6cohort×既phase early/middle/lateの18セルを固定。元group内重みw=1/(G*n_game)で、各split/cellのrow/game/G+・mass・gapを保存する。距離差/残壁stock/距離clipの既binsと入力支持診断はsecondaryとして全群を保持し、結果を見てbin境界を変えない。

セル内でr=N−D、eD=y−D、g=E[r²]−2E[eD*r]をOOF/valそれぞれ記録。条件内meanbias、r/eDの振幅と相関、target残差の平均/分散、clip状態を別にする。既ridge/clamp仕様は変えない。相関だけでgainを代弁せず、必ず同重みのsigned contributionを全体へ戻す。

共通支持セルではOOFのgをval massに置いた参照を一つ示し、差を「構成比差」と「同セル内gap差」に分ける。具体的にはΣ(mV−mO)gOとΣmV(gV−gO)。片側セル0、late極少数、支持域欠測は外挿/0補完せず、別のunsupported mass/実gapとして残す。これが因果transport推定ではないことを明記する。実game等重みをrow等重みへ置換しない。

group単位のgain/loss全分布と5fold別gainも併記する。必要なら固定予測に対するpaired game bootstrapを小範囲で行うが、同λ選定・overlapping foldtrain・再use val・モデル再fitを含まないconditional区間であり、nestedCVや独立testの区間と呼ばない。近似共有状態なしも独立IIDの証明にしない。

費用案はNN0/1CPU/既448MiB程度、compact scalar予測をstream/メモリjoinし、1短算術job hard5s目安・小表/receiptのみ。新モデル/大行列/forward/copyは不要。216のstatic残・現在owner/process/保存forecastが不足なら統括が別の有界現配分へ移す判断であり、180s capをresetしない。218/220がこの計算を実施したり216sourceを変更したりする案ではない。

## 結果で主計画を変える

|観測|主方針|
|---|---|
|共通セルへのmass合わせでgap差の大部分が縮む|状態/phase支持とtrainingの重み付け・対象教師分布が次の律速候補。encoder齢/幅より、保存trainingの該当支持を改善する1条件を結果前に選ぶ。新教師を無条件に足さない。|
|同cohort/phase/支持域でもeDとrの関係がOOF/valで違う|教師条件付き残差・履歴/状態情報不足又はsplit変動を優先。learned hidden齢だけの改善を原因切分けとして先行しない。|
|少数game/foldにOOFgainが集中、conditional不確かさが大きい|現OOFは弱い選定証拠として保持し、同testを交換せずDを維持。sweep/次checkpointを自動増殖させない。|
|全群に一貫した支持・残差関係があるのに現readoutだけ転移を失う|standard200 hidden対400を同D/ridge.01で比較するfeature-training-age対照を次に再検討し、新5901観測の情報価値を正当化する。|

standard200 hidden対照は局所的には妥当だが、今回はOOF raw補正と固定valの不一致を直接説明しない。encoderは全train教師を既学習しておりwholemodelcrossfitではなく、hidden geometry/zero列/尺度と固定λの実効penaltyも齢で変わる。新forwardを使う前に保存された失敗の位置と関係を把握できる。

knownD target sanityは、観測から単純距離関係の表現/学習が律速という具体証拠が再び強まる場合に有力。現在はnonzero gradient/早期曲線/尺度利益/距離only fitがあり、補正の転移を分析する前の自動入口にはしない。fresh testは選定後の確認評価、teacher/幅/LR巨大sweep/arenaは今の原因分析を代替しない。

結論は探索的判断であり、単foldpartition/少数λ/再用val/penalty容量/clip/履歴不足/teacherrootmeanと真値の違いが残る。最高NNUEへ進む意味は、新しい条件を増やす前に「何を表現・学習・生成へ変えると利益が移るか」を保存失敗から限定すること。科学成立や契約一致を研究優先の根拠に代えない。

solewriterは220自域2path。subreserve256KiB/文書source128KiB以内、保守combined58,480,714 < guard58,720,256B。旧caps/未知量減額/親追加0、読取30s上界。07:15 source/doc停止、07:20までに必要Gitbyte/index保持・notes/backup/stop/handoff。216/219の開始や承認のgateを増やさない。
