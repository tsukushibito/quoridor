# frame18 独立増量と低LR標準化QF1 / quoridor-4lc.228

新672局生成、192/576訓練局の入れ子学習、固定validation96局の候補選定、凍結後の新test96局一巡を完了。新test rootmean game平均MSEは候補0.260522、距離基準0.400449、定数0.690546、未学習初期0.703811。真zも候補0.575940対距離0.718082で改善した。同生成分布の教師精度の結果で、Sigma同等・棋力・最高目標の認定ではない。

## データと結果前境界

新672family/actionseed/master entropy、opening8/12/16/20/24/28各split均衡を結果前固定。7つの96局manifestを14×48局chunkで実行。全672局GOAL、Rpolicy/Rz/Rjointは32,520行。旧frame16新96局は旧版を保持した新manifest aliasでtrainへ再割当、独立testとは呼ばない。benchmark兄弟、旧開封testlabels/results、173正式198局は非学習・選定非読取。

train192=旧96+新96、train576=旧96+新480。validation96/test96固定。最大train576と全validationのlabel-free state OR history OR actualSTM-f32入力署名でmaskを曲線前固定。train27,463/val4,813/test4,847行が参照集合内で全eligible、除外0・0eligible game0。参照外の無共有・IID・代表分布は保証しない。custodianによるtest教師資格確認と、候補選定ローダーへのtestlabel非使用を区別。OS全人物理隔離は主張しない。

## 同条件学習と曲線

原QF1-H32/tanh、全FT/h/out trainable、AdamLR1e-4/WD0、batch128/game sampling、seed19080311、各2000step=256,000train samples。旧211のtrain-only mu/sigma固定、hidden距離列/bias補償で同初期関数を保存。各train/val全行の追加raw parityを課金し、最大差1.4901161e-8<=1e-6 PASS。原initial e5d218c9、scaled initial51b9a8c0。13点曲線・全game/phase/cohort/sign/saturation・固定12train witnessは同評価passから保存。

| train局 | train行 | BEST/LAST | train rootmean gameMSE | val rootmean gameMSE | train-fit Dのval |
| --- | ---: | ---: | ---: | ---: | ---: |
| 192 | 9,025 | 2000 | 0.035509 | 0.362468 | 0.429385 |
| 576 | 27,463 | 2000 | 0.107258 | 0.305239 | 0.433135 |

同256,000sampleでlarge−small val差−0.057229、52/96局改善。曲線前固定の非選定secondary small400対large1200では0.497118対0.313156、差−0.183963、69/96局改善。期待samples/gameを合わせる参照で、密度/epoch/旧96/samplingの交絡を消す純量因果ではない。

![保存曲線と新test](/workspaces/quoridor/.worktree/ai-sigma/research-data/ai-sigma/frame18-data-learning/learning-test-curves.png)

## 凍結と一巡test

固定規則stage BESTのval primary gameMSE最小（同値は小G+・早step）で576BEST2000を選定。checkpoint/initial/config、train-only距離係数/定数、mask/metadata/scale/selection/evaluator/sourceをcandidate-freeze-v1.json SHA2bac8f1f7ad87b83ac0549c01bb32eb0c8d0a2f39a05c717420e20cd668e6a60へ束縛。labelsはowner広告SHAのみfreeze前に参照、本体hash/decodeはfreeze確認後。候補tensor b81792d5、初期51b9a8c0。追加fit/test・候補選び直しなし。

| test96 / 4,847 eligible行 | rootmean gameMSE | 真z gameMSE | 真z sign行accuracy |
| --- | ---: | ---: | ---: |
| 凍結候補 | 0.260522 | 0.575940 | 0.771611 |
| train-only距離 | 0.400449 | 0.718082 | 0.725603 |
| train-only定数 | 0.690546 | 0.999872 | 0.505261 |
| 未学習同初期 | 0.703811 | 1.014015 | 0.494739 |

候補−距離のrootmean game差−0.139926、66/96改善、固定fit paired game bootstrap2000（結果前seed2281805）のpercentile95[-0.192885,-0.084130]。真z差−0.142142、67/96改善、区間[-0.231833,-0.050944]。選定・教師依存・分布不確かを全て捕える区間ではない。teacher rootmeanは真値と同一ではない。

## 全attempt費・失敗・背景実行

生成1,849,212physicalNN/guardian2175.606740秒/最大sampled familyRSS2,320,748,544B。test第一chunk旧wire split不成立は1,623NN/10.945371秒を保持。testをreadonly workerへevaluation wireで送り、資格後exportでtestへ戻す薄い新版を保存。失敗prefixは適格datasetへ重複採用していない。全旧失敗/source/Git保持。

CPU192は449,732sample/10.664901秒/996,073,472B、576は707,864/22.714155秒/1,062,039,552B。初期raw parityと13評価を含む。testは9,694/2.569327秒/787,955,712B。累1,167,290sample/35.948383秒、CPU2単1/Torch1/GPU0、全wait/exacttickabsence点確認。gen2.2m/5400秒、learning-test2m/900秒内。

background gen-r2 8255c4c9、learn-r1 e18b2b4a、test-r1 1769d738をBeadsへ記録してturn終了Idle、completionで同saved session実再開。outerwall/queue自然待ち/scienceguardianwallは別。root slot留保657.929秒と人工CPUtest6.551秒も別。未計測の手動source/通信/全team費を0にしない。

保存plot管理はtraining環境matplotlib不在→既plots環境で図保存。cost receipt tailのNameErrorも別失敗として保持。新NN/model/science再実行0、元aggregate/stop byte不変更。PNG/SVG保存済み。raw14packのmember復元/Git証拠を参照し、全履歴複製なし。

## 判断・再現・次最大1

増量した低LR標準化QF1候補は新96局testで距離/初期/定数より有効。元96局だけの距離未達から特徴無効・データ十分を断定できなかった点と整合。量/分布/旧96/epoch/updateの交絡があるため量を唯一原因にしない。新重み既定昇格・arena・正式NI・自動学習混合はない。

次最大1案は、凍結scaled QF1のnative full/delta/undo数値対応と有界αβ接続を別配分で確認し、教師精度利益が実valueへ移るかを問う。現在課題から対局/再学習を自動開始しない。

再現正本: generation-plan、dataset-v1のplan/quantity-freeze/adapter、learning-plan-v1、candidate-freeze-v1、test-settings-r1、全guardian、scientific-final-stop、learning-test-summary、protected-artifact-manifestと停止source。必要archive/memberSHA・Git byte復元/defaultindex不変更・Beadsbackupを有限保存。親最高goal未達。

保存費・外挿補足: 当672の全attempt guardianから1000局相当 53.9585分。測定済みgeneration管理の下限を加えると 56.0875分＋未測費。30分目安は未達、60分は短外挿の既知範囲に限り、実1000未実施。現在scope 154060616B＋Git/temp forecastは448MiB guard内、512MiB予約を保持、旧unknown減額/親追加/未使用返却認定0。learning archive10,478,945B/member byte復元PASS。
