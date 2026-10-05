# frame18 / 独立段階増量と低LR標準化NNUEの学習接続

ユーザー明示10:33:18–14:33:18UTC新4h、heavy14:23:18/監督14:28:18/monitor14:31:18/保存14:33:18、既CPU4/RAMcurrent8GiB/保持+有効unused12GiB/GPU推論6GiB・各30min/旧GPU学習確認未使用のみ。same saved/model/effort/cwd・LLM人数gate0/turnnull・pause/所有/正binding/自己子回収を維持。旧run/費/失敗/個別期限reset0。common/currentrole/実行記録を参照、rootACK/全役全文承認/全史監査gateなし。173正式198非学習/旧開封testは選定へ戻さない。共有環境toolchain更新/install/model取得/製品統合/push/公開0。親/運用source92単独writer。

## 問い・選定
最大の未解決は既96trainだけでデータ量不足を除外できず、実際に増量した独立gameで低LR/距離標準化QF1-H32がtrain/validation/未見testの利益を出せるか。前枠Graph/codecは同48で有限改善、新96は4603joint/既知1000約52.5min+unknown。225の二model censorにより同host完全速度対照は不成立、残candidate単独より増量/学習が判断を進めるため追加最適化を停止。既成立roundrobin codecGraph/GPU24/B8/K64を固定する。cohort均衡/array転送/Rustpump/C++は将来改修費回収と新分布/尾部が阻害するとき再検討、今回基盤移植を新gateにしない。

## 所有・実作業
同experiment saved actor codex:01a0f31d-6d15-7620-bb63-4b4f878e4746/worktree ai-sigma。solewrite tools/ai-sigma-frame18-data-learning/、research-data/ai-sigma/frame18-data-learning/、docs/reports/ai-sigma-experiment-data-learning.md。旧225 scientific sourcewriter/子停止を点確認してreadonlyreuse、新scope準備は225全稿/Git完成を待たない。227の私有manifest_adapter.pyは227solewriter、stop/hashと動作interfaceを受領してreadonlyreuse、必要薄training runner/configのみ自域に実装。旧trainer/canonical/make_mask/plotsをreuse、全trainer/sourceコピー禁止。全benchmark兄弟をこの独立データへ混合しない。

## データ数量・結果前条件
旧frame16新96evaluation-only候補を、理由明記した新manifestでtrainへ再割当。旧evaluation-only版/成績を維持し、独立testと呼ばない。新672game第一候補はfresh480train+96val+96test、6opening cohort各16/96job・各game/family/actionseedが新domainでunique。旧fresh96固定生成sourceのcategory RNGを一ply一回に固定し旧48のfilter内RNGへ戻さない。前96label-freeのstate/history/actualSTM-QF1露出signatureとのORを保存、oldtestlabels/results173は読まない。各tree/ゲームの独立RNG・K64/root64edge63/modeld790/RuleA/P2/pi,z/Graphstartup108/codec/温度/探索規則維持。

最大7つの事前96manifestを全payload/labels計測前に固定し、生成順はnew val96→sealed test96→new train96×5。96はsplit/family計画の単位であってprocess固定数ではない。provider cap307200が長いgame群で打切りを生み得るため、結果前に各manifestを48等の小実行chunkへ分ける選択を許す。同game/domain/seed/K/品質/全planned672を変えず、chunk/startup/全費とcancel/reapを明示しnewgen2.2mNN/heavy5400s内、各hard600/VRAM6GiB内。過去completedの再生成や品質量削減として扱わず、最大7manifestをmax7process制約へ誤読しない。test labels/教師予測payloadは隔離sealして選定者/学習ローダーへ渡さず、品質資格のaggregateとlabel-free signatureだけ共有。testは候補/条件freeze後に1巡、未見結果を選定へ戻さない。生成が部分停止なら全予定/GOAL/未完了UNKNOWN/NOT_STARTED/zeroeligibleを保持し、適格・完了familyのみの数量を明示する。途中prefixのunknown-zを有効教師へ数えない。同domain再入口の失敗と兄弟traceは保持し、適格datasetに同family二重採用しない。

train192=old96+第一newtrain96、train576=old96+全newtrain480を入れ子、fixedval96/test96。曲線前に最大実取得train集合のlabel-free OR maskを固定し小大で共用。旧scale mu/sigmaを固定して条件差を抑え、ラベルjoin/moments/教師評価をval/testへ流出させない。stageごとのtrain-onlyD係数/定数と同gameequal rowweight1/(G*n_game)を保存。局数/row数/lineage/露出/epoch/seen/stepsを別表示、兄弟や内共有をIIDへ格上げ0。

時間/量不足branchは曲線前13:05UTCで固定:holdout96+96とtrain192が成立すれば小stageを実学習、大stage576不足なら取得済み適格trainを使う大stage又はNOT_STARTEDを結果前manifestで明示。holdout不足は観測済train/valの診断範囲に限定して独立test未実施を保存。見栄えの良い結果を得るため量/split/maskを曲線後変更しない。672/192/576全量完了を新gateにしない。

## 学習・判断・必要確認
全FT/h/out trainable、QF1-H32/tanh同型・標準化距離/AdamLR1e-4WD0/batch128/gameequal/rootmean固定。各stage seed19080311の同初期関数/同共通maskとinitialtensor、fresh optimizer、sampling seed/orderを結果前保存。各stage2000steps=256000training samples固定、early eval points0,1,2,5,10,20,50,100,200,400,800,1200,2000を第一条件。同sampleではepoch約3倍差なので純データ量因果にせず全pipeline比較。保存費/NNcapに入るpoint数の変更は結果前のみ。
229提案を採用した非選定secondary:full192/576なら既smallstep400とlarge step1200を同期待samples/game=266.7で並記、best/freeze規則は変更しない。数量branchなら曲線前のsmall400 anchor（無ければtypedmissing）に対しlarge savedpointのabs(step/G_large -400/G_small)最小を固定、同距離tieは早いstep、distanceを明記。点追加/補間/結果後pair選択/新NN0。row densityやgameequalはrow epoch同一ではなく純数量因果を認定しない。

train/valのD/定数/initial/plain既結果と同target同指標/rootmean/z/signを区別して曲線、全pergame・有限同forward witness/activeFT観測を保存、追加probeを先行しない。validationは探索選定として明示し、小大のbest checkpointとLASTを比較して最大1候補・NN/D/定数/指標・失敗規則をfreeze→新test96を1巡する。独立testMSE利益とnative接続/棋力/最高目標は別、arena/正式対局を本課題では自動開始しない。小datasetnegativeからデータ十分/NNUE無効/teacher唯一原因を認定0。newtest結果で再選定しない。

確認はmanifest家族/split/ID/dynamic count/zero rows/weights/mask/train-onlystats/loader/config/初期数値・有界sourceSHA/finite pi,z/RuleA合法/P2/NN counters/止め方を主張に必要な範囲。旧432provider numeric fixture/source不変はreuse可。変更guardはcmd argv/path/ancestorとactualCPUtoolを区別、offenderPIDtickを保存。4core速度/重い生成は自然supervisor実tool/owned回収後の十分窓で開始し、LLM人数だけのgateへ読み替えない。CPU fixture/critic checkerとの重い同時実行なし。

## 総資源・費用・時刻
新generation physicalNN累積2200000、各provider cap307200/startup課金/各hard600s（30minより小さい）、allgenheavy5400s・CPU0provider+2/4/6workers計4/RAM家族6GiBguard5.5/VRAM6。source/debug180s/資格exportpackGitbackup管理600s、原全attempt費/Unknownを保持。静的修復/同manifest再入口は総NN/全費/全予定分母内、成功runの置換・余分な独立局数追加なし。

新learning+validation+frozen test physicalsample累積2000000、CPU2single/torch1/各jobhard300s・allheavy900s/家族RAM6GiBguard5.5/GPUtraining0、source/test-fixture180s/管理180s。observer追加forwardは必要ならこのsamplecap内課金。モデル/FT最大RAMやdynamic counts不足を結果前typed stop、未知GPUtraining残をCPU学習へ置換して上限増加0。旧225/221/227全費reset0。

新保存計画gen384MiB+learn128MiB=512MiBを既exp1980poolの225263MiB配分後確認unused702652416Bから計画、残165781504B。共有モデル/環境copy0、旧有効予約は返却認定しない。new512内データ/依存/Git/cache/tmp+unusedを直前現在admit、guard448MiB/forecast384MiB、未知減額/parent12GiB追加0。不足は必要payload圧縮/停止SHA・member復元を保ち確認済unusedだけ再配分。解析者用compactとsealedtest別、全rawcopy/全sourcecopyで増やさない。

準備11:35目安、firstgeneration11:45目安、newgen開始12:50まで・genstop13:05（結果前数量branch）、train/validation candidatefreeze13:50/testnewheavy14:05/teststop14:15/source必要保存14:23/最終親14:33:18。元22511時台期限を変更せず新issueの配分。4h開始取り直し0。newworkが期限に入らなければtyped NOT_STARTEDと費用付き不足を保存し自動延長しない。

coordinatorへ受領/claim/static/source→actualNN→停止/compact/予算/選定分岐を返す。227準備完了の全稿/critic全文/rootACK待ちではなく必要interface/現在資源確認後実進行。意味のある結果で主計画/次配分を更新。source/子wait/PIDtick不在/必要Gitbyte復元/index保持/Beads notes+backup/有限handoff、goal未達を保持。
