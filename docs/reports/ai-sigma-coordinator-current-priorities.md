# 現在のNNUE研究優先順位（frame16）

明示許可05:55:50–07:55:50 UTC。新heavy07:45:50、監督07:50:50、monitor07:53:50、最終証拠07:55:50は92所有。CPU4/RAM8GiB/保存12GiB/同saved六role・model/effort。最高棋力goal未達、旧test選定復帰0・173正式198局非学習。

## 現在の主課題

最大の未解決点は、train内の未学習gameに通用する残差関係が固定validationへ通用しない理由。保存train/validationを同rootmean/gameequalで比較した結果、early200は訓練適合不足、late400は訓練に合うがvalidationで距離を下回る汎化不足が共存する。fresh testを先行する方針を改め、保存入力・教師・予測の原因分析を主配分にしている。

主216 experimentはsameissue/同scope/元NN30000・静的180秒・16MiB予約内のphase4、raw whole-pipeline train-game CVへ実配送06:53:19。3λ(.01/1/100)、5gamefold、各foldの距離WLSと入力momentsもfoldtrainのみでfit、OOF全96game平均で選定し、選定λでfulltrainfit→同24validation一度評価する。validationでλを選び直さない。NN0/教師/test/GPU0。[条件](../../research-data/ai-sigma/frame16-coordinator/216-raw-cv-amendment.md)。raw626の固定λ.01で大きなtrain-val gapが残ったため、表現年齢や容量を変える前に汎化制御を直接操作する。encoderを教師で学習していないrawなのでwhole-pipeline game CVを組める。

公開process/resultの統括読取ではphase4 exit0/allwait/exactabsence、λ1 OOF .382828対foldD .408041、fulltrain .215837/validation .548893対D .485147。正則化は旧raw.01 val .781449から改善するがD未達。本人phase4科学/source停止正本e55d5856を受領・現SHA確認、219へ実配送済み。219の必要NN0独立算術PASSを受領(全15fit再計算なし、selectedfull係数/予測差0)。phase4/source/payload有限保存を統括受入れ、219最終小保存待ち。OOF改善を独立test/棋力へ変換しない。

217はphase1/2必要独立算術180/180を保存・有限受入れ、219 substantive intakeで本人close+backup済。219を別120s/1MiB、既critic112MiB内へ実配分06:55:16し、本人claim/source開始と選定前見解を受領。219のfoldtrain→held state/history/actualQF1 OR露出件数案を採用し、主fold/全96game分母を変えず記述する。実追加算術は元219残枠内、結果後除外/新gateなし。218は距離-only参照提案を採用され本人closed。全役承認gateなし。

## 意味のある観測と主配分変更

| 観測 | 変更した判断 |
| --- | --- |
| standard200 train .548567>距離 .405944、val .613916> .485147。400 train .257283<距離、val .648772へ悪化 | early fit不足とlate汎化不足を分け、fresh testから残差分析へ変更 |
| std400 residual相関 train .607338/val .047912。valgap .163625=変位 .192934−alignment .029310、平均bias/clip寄与小 | fixed learned400hidden ridgeでreadout不足を低費用検査 |
| hiddenridge train .208594/val .612799、scalar再校正 val .484540 | readout変更でD未達。raw入力の加法的関係へ主問いを変更 |
| raw626 λ.01 train .161374/val .781449、distance2 val .484526 | 単純容量拡張を止め、train-game CVで正則化分散を直接検査 |
| CV λ1 OOF .382828<foldD .408041、固定val .548893>D .485147 | 正則化の関与とOOF/val差を区別。独立算術・露出/群寄与の記述から次の原因対照を選ぶ |

Phase1 forward23604/1.515544s、phase2 hidden5901/3.299503s、計29505/4.815048s。phase3 math .895876s+parsefailure .053226s、phase4 guardian2.463894s。CPU2単1/GPU0、過去peakとcurrentは別。全team/LLM/管理費未集計、保守static課金と実wallを混同しない。

217はphase1必要5901算術・元重みdecomposition/排他bin closure、phase2 savedhidden/ridge係数/全gameを独立支持。walls binsは残量stockで配置壁複雑さとしない。phase2 scalar参照は主science終了後の別prospective登録、owner主metrics未読の独立証明なしを保持。phase3はownerのみ、phase4は219が必要範囲を独立検算しPASS。rawλ1 OOF51/96game改善、fixedval11/24改善、valrow/z/signもDより悪化。元120/120を停止し、追加計算を自動化しない。

## 意味のあるCV結果からの次配分

220 hypothesisを別静的30s/256KiB・既hypguard内へ実配送07:04:08、本人claim/source開始07:05:47。保存OOF/val共通支持・残差gap分解を優先する独立見解を採用。216 phase5へ実steer07:12:45、既18cohort×phase全セルで元gameweightのcomposition/within/unmatchedを分け、固定予測paired game区間を記述する。追加forward/fit/教師/test/GPU0、旧static139.413保持+source5s/math15s以内で180cap不変、compact128KiBを旧guard内。phase4以前の成功source/resultは別保存。モデル差(OOF72/78fit対full96)、単fold/3λ選択、少数valgameを純粋分布因果にしない。結果が構成差/条件内関係/小標本のどれを残すかで主問いを更新する。[条件](../../research-data/ai-sigma/frame16-coordinator/216-support-gap-amendment.md)。

## 有力な保留と再検討

standard200 hidden age比較は有力保留。CVの正則化だけでDへ届かなければfeature-training-ageの効果を低費用で問える。ただし現在はOOF/val差が重要なので、既保存群/露出/残差分布の情報が次対照を変えるかを先に見る。learnedhidden crossfitはencoder全trainラベル学習済みなのでconditional head varianceまで。既知distance targetの学習sanityは基本関係を学べない疑いが強まる時に再検討する。fresh test/新教師/追加LR幅/arenaは確認評価であり、この原因切分けへ自動先行させない。

## 運用と報告待ち

92は06:13:31freshstart、scheduler4069898/34737868・monitor4069912/34737890 loaded/24binding一致・親16指定SHA/六digest一致。初回自然turn interrupted、意味内容・全面点検成功は未確認。旧停止原因欠測を保持。現在正monitorpathと各期限は92契約参照、自己運用停止と外部NN停止を区別する。92に最新通常1turnの意味内容調査を実配分07:06:02、受理dispatch後interrupted/items0/readguardなしを有界保存。出力前未到達の原因unknown、点検効果不成立は保持。周期/180秒/同設定変更・推測restartなし。

待つ判断は216 phase5実18cell分解/区間と必要保存、219独立CV選定算術、220静的選定最終保存、92長期期限回収。root215へ初期実配送/開始とruntime成立は実報告済み。意味のある観測ごとに現在主計画を更新し、旧frame原成績・失敗版を保持。原因一意・教師truth・独立test利益・棋力は未認定。
