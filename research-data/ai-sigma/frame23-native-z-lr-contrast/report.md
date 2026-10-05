# 真正zのLR・早期学習窓（302、旧ランダムdraw条件）

二条件ともユーザーの全行epoch追補の到着前にspawnし、元登録のgame一様→row一様の復元抽出で自然完了した。追補を過去結果へ適用していない。A=Adam1e-4、B=3e-5、WD0、4000step×128=512000 seen、共通QF1+D/H32/Zero4/rawD0,8/尺度175f077/initial ec4167/seed19080311、同T14803/432family・rawV4733/144family。旧既見コーパスの選定で、公開/新96のtargets・誤差・resultsを選定に使っていない。

|条件・点|train family z MSE|selection family z MSE|train飽和割合|
|---|---:|---:|---:|
|共通初期D|.615387488|.660867274|.02439|
|A 1000|.280252574|.585894418|.23218|
|A 1250 BEST|.206971819|.584376578|.31473|
|A 4000|.005187532|.747894928|.88563|
|B 1000|.565757127|.638777546|.03466|
|B 3000|.342086096|.580472192|.16544|
|B 3750 BEST|.271168857|.574644168|.23563|
|B 4000|.249902146|.574924200|.26001|

LRを下げると有効な窓が後へ移り、Aのdense最良点1250も旧1000→4000の粗い記録から新しく観測できた。B3750とA1000は到達train誤差が近いが、Bのselectionは約.01125低い。これはLR/更新軌跡を先に疑う有限材料で、LR唯一原因・独立転移・強度を認定しない。B終点は最良点より.000280だけ高く、明確な退行/収束完了には足りない。右端の最適化不確かさを保持し、自動延長や追加LR/WD/gammaを行わない。Aではfitと飽和が進む間にselectionが退行し、仕事・early stopping・正則化も競合である。

A/Bの実row/family sampling countsは完全一致（SHA6bb63a83）。追加evaluationはforwardを同課金内で増やし、sampling RNGを進めていない。Aの旧298と共通9点はnative weights byte SHAまで一致した。全batch順列は個別保存しておらず、同source/seedと実count・snapshot整合の範囲の証拠に限定する。row epoch proxyは512000/14803≈34.59だが、完了した無復元epoch数とは呼ばない。復元抽出ではrow別露出が不均一である。保存PTから23点のparameter displacement normとLR×step proxyを算術保存した。Adam更新量の同一性はLR×stepでは認定しない。

元選定規則（family z MSE最小、tieは少seen→case A）に従う観測候補はB3750、480000 seen。full run512000とは区別する。candidate-freeze-v1.json SHA6da696b6a013e8b85f439abc6db2541ff599b6430c4d408dafd62b0fcf2b2329にPT/native/config/initial/scale/全Tseen/rawV/原roworder/scalarsを束縛した。研究用候補でありdefault採用や旧独立評価の成功ではない。

各fitは現役mainのpython -m quoridor_training.train trainを使い、WT trainer・ループコピー・shimを使っていない。sourceはmain-readonlyで登録し、正しいcache.load 5tuple(binding,rows,x,distance,labels)、rows list[dict]、全tensor行数19536とtarget f32 metadataをNN0で検査した。native-only/23pointの同forward scalar・weights保存を使い、ONNXや追加validation forwardは0。各新BESTをmain maintained binary6a2fc4fのP1/P2・full/delta・親復帰とTorch値で有限parityした。native22＋Torch2=24NN/caseを課金し、unchecked新重みへ旧312proofを代用しない。main CLIのSIMD fieldは未記録なので今回新重みSIMD実行PASSには広げない。

A actual22:55:10.004914→22:55:21.484924、B22:55:56.285608→22:56:07.395750、全fit/parity子wait/currentidentity/pgrp不在、MAX2全消費。実NN=961352×2=1922704、保守予約1923656/processed上界2039536。科学command合計22.609762秒（model/parityの包含spanを再加算しない）。peakとactual/remaining保管を条件ごと再admitした。main math/Rust/依存/build/GPU/Git/indexの編集は0、旧費・UNKNOWN・各原失敗は保持した。

全行epoch追補には直ちに実quietを返した。main scientific sourceを追補前に小archiveへ保存・stream byteSHA復元し、coordinatorの新canonical実装へreaderを解放した。両旧entryは既に完了/MAX2消費なので、新32epoch・無復元shuffle・tailbatch・N/(G*n_g) weighted lossの科学はNOT_STARTEDである。新epoch方式はrow一様露出とfamily-equal目的を分けられるが、旧復元抽出とAdamの有限batch経路が異なるため性能を先取りしない。再allocation・新source/fixture/clock/physicsが必要で、302のcap resetや第三条件にしない。原registered source/configはそのまま保護した。今回の結論は、LR＋露出/停止の再設計を学習側第一に置く根拠で、domain/教師・表現・数量の原因確定ではない。

必要な未来独立protocolは別allocationとする。新UID/seed/opening domainの無関係96 RuleA family（旧29996は開封済みなので不使用）をlabels前登録し、観測候補または新canonical epochで選んだ一候補＋旧native57684865＋D＋train-only constantを比較する。全actualTseen unionとALLraw selection、使う全baselineのpublic exposure参照に対するstate/fullhistory literal/actualSTM f32 ORをfreezeし、null/欠測を非露出保証にしない。producerはlabels sealed、reviewerはinput-only refsからmask/rulesを固定し一巡、testから候補/条件を選び直さない。96全予定/完成/UNKNOWN/除外/0eligible、cohort/side、familypaired差・SD・固定2000bootstrap/.025,.975を保持する。

旧96の170255NN/41.7156科学秒は期待費の起点で、worst200ply×65×96+warm72=1248072生成NNを別admitする。新raw最大19200行×2 NN predictors＋1000fixture=39400予測NN、旧密度3280行なら6560＋144=6704程度。資格・cold start・source準備・mask/入力対応・解放・保存・回収/Git/tmpを含めproducer準備10–30分/科学45–180秒/8–16MiB、reviewer準備・parity・scoring・保存5–15分/.5–2MiBを概算幅として返す。差分入力やbackend変更時の資格費は別に実測し、wholepipeline保証にはしない。

旧native96のCI幅からfamily差SD≈.45を粗く仮定すると、96 pilotのCI半幅は約.09、半幅.04には約487、.02には約1945の有効familyが必要となる。これは別候補・別domain・cohort依存を無視した概算で、理論最低量・IID・power保証ではない。新pilotがSD/有効unique/lineageを更新して段階量を選び、小候補成功を十分量の入口gateにしない。新epoch/regularization/scheduler/duplicate weighting、十分family量、位置付き経路/history、root→leaf/horizon、TT/ordering/whole search費を同候補集合に残す。現在はユーザー指定の全行露出canonical検証を先にし、LR sweepや同選定MSE循環だけで止めない。未見z改善と同wall棋力は別評価である。

保管は新24MiBでactual source/assets＋必要Git/tmp/metadataを包含して約22.95MB、old285280/old29914とfresh92 conservationを保持した。source/reader/selector STOP、明示main科学source小archive・owned control archive、全scalar/PT/native/persistent asset hashを引き渡す。coordinatorだけがmain統合とGitを所有する。親最高棋力は未達。
