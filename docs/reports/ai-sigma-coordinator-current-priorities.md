# 現在の優先順位とNNUE学習・独立test計画

frame14ユーザー明示4時間再開。開始2026-10-03T23:20:36Z、終了2026-10-04T03:20:36Z。新重job開始停止03:10:36、監督scheduler03:15:36、monitor03:18:36、最終保存03:20:36 UTC。旧frame13/科学runの期限・成績は不変。CPU4logical/RAM8GiB/保存保持+有効未使用予約12GiB、GPU推論VRAM6GiB各job30分。GPU学習は既累積2hの未使用残不明のため今回CPUで前進する。active role数を研究入場gateにせず同役二重/物理重競合を避ける。SigmaNI/NNUE最高棋力は未達、173正式198holdoutは学習0。

## 今枠の到達判定と実配分

到達判定は、新独立教師・固定train/validation/test・学習曲線と条件選択・候補freeze・未見test評価を一巡し、改善/不確か/不支持を再現可能な結果で判断すること。小QF1-H32試作又は再利用validationだけでNNUE方式の最終性能としない。

| 作業 | 実担当・issue | 単独writerと完了条件 |
| --- | --- | --- |
| 新教師の段階生成 | experiment / quoridor-4lc.194 | tools/ai-sigma-frame14-teachers・frame14-teachersデータ/専用report。新144gameの全slot/π/rootNN/rootmean/leafNN/z/視点/履歴/lineageと資格・費・停止を保存 |
| 3分割manifest・曲線・設定選択・test | hypothesis / quoridor-4lc.195 | tools/nnue-training・研究nnue-training手順・frame14-learning/専用report/models。test隔離とfreeze後評価を薄接続、train段階比較→最大1追加LR→候補/未学習/定数の独立testを一度評価 |
| 露出と独立判断 | critic / quoridor-4lc.196 | 独立tools/data/reportのみ。早期分割の最大1見解、最終全slot/露出/資格/curve/freeze/test算術を必要範囲で独立検算 |
| 期限運用・主手順mirror | steward / 既quoridor-4lc.92 | 親/92運用bindingを停止窓で更新して同runtime起動・回収。研究手順hyp停止/hash引渡し後だけmain同bytes同期 |
| 目標・配分・受入れ | coordinator | 本計画・goal説明/契約・有限受入れ、本人報告から次判断を実配分 |

既savedへ実配送済み、本人claim/static開始を受領。194は全6job144GOAL・適格6996行（train96=4653/validation24=1248/test24=1095）、allattempt generation691.356145秒・physicalNN397012/startup0、科学最後00:01:42.075112Zでsource runtime/全科学子を停止した。共有RuleA資格と195実canonical APIによるlabel-free全144manifest・最大96固定maskを引渡し、現データのval/testは全行eligible/G+=各24。代表性・IID・教師真値は未認定。最大96mask前の部分48版は履歴として保持し、選定には最終版だけを束縛する。export192heap OOMは管理失敗として保持し、同immutable rawをhelper512/guard896MiBでNN0修復、worker cap/NN科学は変更しない。195へ停止・正本使用可能を実steerし、196へlabel-free実mask検算を実配送した。195の固定LAST比較は別moduleで共有v2を保持し、NN0二check成功・学習開始予告の後、00:14:08.640926にtrain24-r1実child（CPU2/PID3802905/starttick32580881）開始報告を受領した。3stage24/48/96はいずれも2000step完了、同initialSHA/各256000train samples、計1019139評価込samples。全beststep0で固定valの学習改善は未確認、学習済み重みへの昇格0。candidate48step0/同初期tensorをfreeze v2 SHA45c27fbfで結果前固定。00:19:26–00:19:28独立test一巡は3uniqueweights3285samples・全子回収。候補rootmean gameMSE.669736対train定数.655448で改善不支持、LAST96minus24+.043023/paired95[-.163854,.251313]で数量効果不確か、重み採用0。196へ最終per-row算術を配送、195へ次最大1競合仮説の判別案を提案依頼した（追加run0）。194有限受入れ済だがBeads所有guardで統括closeは未成立、owneridleで専用turnを作らず次実配分で本人close。既64MiB保存移転は実確認済み。194全pack/Git全文・196全文は学習の入口gateにせず、195がcurrent所有/RAM/自然監督予定を直前admitして学習へ進む。194旧guardianのruntime RSS表示限界は保存し後続版はruntime/nested testを算入した。配送accepted/本人開始/学習効果は別。主報告待ちは195曲線/freeze/test、196独立mask/test裁定、194必要pack/復元/backup、92期限回収。

## 次の最大1判別の現在配分

196最終NN0裁定は全6996署名/mask、63曲線点、1095test per-row、同tensorSHAとpaired2000bootstrap/定数を独自対応し、候補学習不支持・数量効果不確かを支持した。教師π/GOALはproducer/sharedRuleA、後続historyはopaque、forward再認証なしの限界を保持する。

195提案のL2感度を採用し、hypothesis197へAdam weight_decayだけ0→.01/同96train4653/val1248/初期SHA/2000step×128の学習1runを実配送した（00:30:49accepted、00:32:43claim/00:34:03静的開始、NN0）。旧WD0全曲線を対照として再利用する。exp198へfresh24独立testのNN0先行manifest準備を実配送（00:30:52accepted、本人受領00:31:05/claim/24合法NN0manifest準備、NN/GPU0）。新生成はL2 learned beststep>0/初期と異なるweights/val MSEがWD0bestとtrain定数をともに1e-4以上下回る場合だけ。未達なら全24NOT_STARTEDを保存して追加生成を省く。1e-4は数値微差だけの費用起動回避で統計支持ではない。条件達成後はtrain+val+旧testのlabel-free exposureを固定して新test一巡、旧test再開/交換0。197は既19564MiB内の実unusedから16MiB、198はexp1980MiB内の32MiBを直前forecastし、未知旧量減額/親増額0。新CPU学習とGPU生成・自然CPU0監督は本人currentadmissionで非重複。新early heavy01:15/01:10と最終提出01:40/01:35は親より早側。

196の低LR/初期10-100step案は競合候補として保持し、今回は先に配分済みのL2一因子を優先、同時sweepにはしない。正則化量が支持されなければ原因を断定せず、表現/教師視点又は初期学習量の最小判別へ戻す。元144/3stage/testの結果・freeze・guard失敗は変更しない。195最小停止/保存後197へ、194は198実turnで本人close/backup後、新claimした。195は197の現turnで有限受入れ後の本人closeを実依頼済み、196はidleで次実依頼と合わせる所有対応待ち。closeだけの新turn/force takeoverは行わない。

## データ版と3分割・露出

新fresh144gameをtrain96/validation24/test24へ結果前manifest固定。trainだけfirst24→48→96の入れ子、validationとtestは同じgame/rowで固定する。opening8/12/16/20/24/28plyを各partition均衡、新entropy/domain/family/actionseed、色交換・対称・派生兄弟は同partition。K64/root64edge63/tau1最初16newply→argmax/200newplycapを固定、打切りzunknown/value mask0。187モード反復4528行を独立教師として足さない。

family/game重複は拒否。共通初期/終盤を全game巨大groupへ連結せず、label-free state一致 OR history一致 OR 実QF1入力一致でrow露出を記録する。196初見解を23:34に採用し、実入力署名はversion・実forwardのSTM/相手順sortedactiveIDs・同順float32距離bitsとする。生P1/P2配列+sideだけの署名は使わない。最大train96と共有するvalidation署名は固定主曲線maskから外す。独立test主評価は最大train96又はvalidationと共有する署名を外す。全行を捨てず露出secondary診断/全分母/game別countへ残し、未学習game全体と未露出row精度を別claimとする。maskは教師値・結果・lossを使わず条件選定前固定、eligible0game/少数群は不成立/不確かを保持。criticの安価な異論を科学結果前に裁定し、全group再設計を恒久gateにしない。

test-sealedは生成保存ownerが保持し、学習ownerは最初はlabel-free露出manifestだけ参照。testlabelの評価は候補freeze後、一度candidate/初期未学習/定数を同基準で実行する。testで条件再選別・有利test交換0。validationは選定用であり最終holdoutではない。

## 曲線・選択・独立testの条件

192環境Git95be80dcと手順訂正5dd29beeを再利用。QF1二視点312+距離2/H32・hidden32/dropout0/rootmean target、Adam.001、gameequal sampling、同fresh初期seed19080311から各stage2000steps×128=256000train samples。eval100step、earlystop patience0で固定量曲線、best checkpointは固定validation gameequal MSEだけで選ぶ。step/sample/epoch/wall、row/game等重み、定数基準、rootmeanと真z/符号/飽和/群別を保存。データ量の差とepoch数の差、教師K64のノイズを保持する。

追加対照はtestを見る前に最大1LR.00025/同96train同steps。全幅LRtargetのsweep0。有限val条件でcandidate/config/checkpointSHA/beststep/valhash/mask/selectionreasonをfreezeする。未学習同初期modelとtrainだけから決めた定数を、独立test主subsetと全行secondaryへ比較し、gameweighted/rowweighted誤差・群別/不確かさ・費を別表示する。 supervisor23:53案を結果前採用し、stage24 LASTとstage96 LASTも同actual256000train samples/同初期SHAで固定diagnostic contrastとして候補freezeに束縛する。同一test一回アクセスで最大4uniqueNNモデル+定数、paired96minus24誤差と増分教師生成/学習/保存費を示し、beststep差を数量効果へ混ぜない。未完了contrastは未知、追加train0/test再選定0。test1095行を独立1095標本とは扱わず、予定24game/familyとG+のpaired差・区間・欠測を報告する。単seed/同samples異epochの限界、条件付き未露出primaryと全行secondaryの結論差を保持する。curve改善を棋力又はNNUE特徴の最終性能へ拡張しない。

条件未成立又は改善なしでも全attempt/未知と曲線を保存して終了できる。結果から次の一つの判別実験を選び、データ不足・過学習・分布差・容量・教師noiseを一意に断定しない。有効な候補なら同QF1重み→native evaluator→NNUE+αβ同資源の小対局という次単位/必要教師・予算を提案し、今回自動対局連鎖0。

## 費用・保存・期限

194:6GPUjob各24game/300s、総heavy2100s/手NN1843200+debug1024、CPU0/2/4/6・RAM6guard5.5・VRAM6。新256MiB予約/guard224はexperiment既2044MiBの確認済未使用内、科学硬02:20/保存提出02:45。

195:CPU2単1/torch1・RAM2guard1.75、heavy900s/管理込み1200s/sample5000000上限、各job120s。新64MiB/guard56をexperiment確認済未使用から移転してhyp旧量と別計上。候補freeze02:30目安/newheavy02:45早側/test科学02:50硬/提出03:08。計算はGPU/他重NN回収後のみ。

196:CPU0単1/NN0静的180s・各60s/RAM1guard896、既critic112MiB内新4MiB。newcommand03:02/処理03:08/提出03:12。各roleのcurrent保持+Git+一時+残metadataforecastを直前確認、未知旧量減額/parent増額0。保存成功を全host全期間資源保証へしない。

92は親14 SHA292c722fを引継ぎ期限binding/通常runtime start→running/loadedと停止責任を報告する。main nnue-training mirrorはstewardのみ、研究writerhyp停止/hashと同期する。運用source/registryを統括は編集しない。

## 再利用する有限成果

187/191のGPU24適格12.814931行/s対CPUJS8.212635比1.560392は同24/K64の単回固定順・CPU配置差込みの有限利益。RustCPU3UNKNOWN+21NOT_STARTED、7state/20occのtrain-val露出を保持する。190はQF1-H32学習/差分/小αβ接続まで、新valrootmeanMSE.994812>定数.715720で重み不採用。188低LRは退行部分緩和だけ、176既定/181代替保持。旧190ログは4train点とval0/200のみ、192旧曲線は途中valを補完しない。共通trainer旧190重みimport/native/ONNX導出は未接続で、今の新学習conditionと区別する。188保存guard超過/190残225B通常write停止/一部receipt未Gitは保持。旧frame13の停止/成績を今回救済しない。
