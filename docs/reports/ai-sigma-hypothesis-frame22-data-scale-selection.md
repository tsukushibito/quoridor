# frame22 /284 — 独立データ規模と教師Kの配分比較

次の主配分は**独立familyを入れ子で増やし、D保持NNUEを約6000→10000→30000行で比較する**案を推奨する。小候補がDを超えることを増量の入口にしない。273の現行生成費では、分布・tail・保存費を広げても、この連続枠内に生成とCPU学習を結ぶ現実的な余地がある。K感度は有力な並行診断として残すが、282の欠測を理由に量検証全体を待たせない。今回実行したのは保存値のNN0推定だけで、新生成・fit・モデルimportは0。

## 観測と限界

273は同48family/1720適格行、active48 whole guardian41.484730秒、91603physical NN。train36family/1328、selection12/392。兄弟条件のactive24も同48familyであり独立96familyにはならない。旧4653+1328=5981train、274/280の新selectionではD超え未支持。新tau1全plyと旧16ply以降argmax、同seenでepochが変わるため、旧・新の追加は純数量介入ではない。

282は資格296NNと主180.516秒timeout/4complete recordを保持し、phase母集団の感度は未成立。管理記録修復は別明示配分。回収4条件から教師安定/不安定や高Kの真値を一般認定しない。generation/repeatは乱数seedではない。

[推定JSON](../../research-data/ai-sigma/frame22-independent-data-planning/scenarios-v1.json)はcompact/manifest/cache仕様とfilebytesを読み、教師label本体・旧openedtest/173を読んでいない。Arrow manifestの1family当たり行数は15–80、平均35.83、train平均36.89。working仮定20–70は保証区間やconfidence intervalではなく、短観測に対する費用感度のシナリオである。

## 行数目標と独立family

| train設計点 | 5981から増やす行 | 新train familyの中心見積 | 20–70行/family仮定 | 同256kseenのnominal row epoch |
| --- | ---: | ---: | ---: | ---: |
| 約6000 | 既5981を基準に保持 | 追加不要 | 19行差を工程化しない | 42.80（5981） |
| 約10000 | 4019 | 109 | 58–201 | 25.60 |
| 約30000 | 24019 | 652 | 344–1201 | 8.53 |

観測15–80行の端点を用いると1万は51–268、3万は301–1602familyとなる。理論最低データ量ではない。適格/露出除外後の行数と完整familyで判断し、閾値を跨いだ最後のfamily/blockの全行を残す。短いfamilyだけを失敗、長いfamilyだけを追加としない。

UID/entropy/seed/opening8/12/16/20/24/28/side/cohort、family兄弟の色交換・対称・派生、train/selection/future-evalは生成label前に固定する。全game/family重複を拒否し、state/history/actualSTM-f32 input一致はOR row露出として分母を保持する。旧history形式との互換UNVERIFIEDを残し、キー非一致を完全履歴非露出保証にしない。

## 推薦する段階1と段階2

**段階1**は新train最大240family、固定新selection48、sealed future-eval96、最大384独立family/48family job8本を準備する。trainは登録順の48family blockで入れ子とし、合計適格train1万を初めて跨いだ完整blockを第1増量点にする。中心見積では新train144/既train合計11293行、holdout系144を含め新288family/6jobで成立する。48selectionと96future-evalは目的を分け、shared cache metadataにlabelsがあればcontainer全体をlabel-freeと呼ばない。future-evalは生成ownerが別sealed labelpathを保持し、hypothesisには必要なlabel-free metadataだけを渡す。

**段階2**は同じ新train UID/順序の続きで3万行へ向かい、最大新train1248family、同48selection/96future-evalを維持する。中心は新train672、全新816family/17job、合計train約30770行。working下限20行でもmax1248なら約30941行。15行の短分布等では未達を許容し、max超過・成功補充を自動実行しない。

段階2判断は、最初48/96familyからの適格密度・censoring・物理NN/行・全attempt wall・Arrow/cache/Git/temp・RAMと残時間を使う。**段階1candidateのMSE勝利を必要条件にしない**。安全guard内で完整group/正しいsplit・入力対応が成立し、準備・全生成・学習・freeze・評価・回収の上側計画が残時間内なら進む。teacher誤差が改善しなくても、量不足と表現/target/学習仕事を区別する情報はある。費用がstress上側へ寄る場合は残余からfamily/job数を結果前に有限再配分し、未達量と理由を保持する。schema/入力対応不成立は修復が必要だが、小学習不支持とは別である。

**固定maskの注意**：新48family valの所属は固定するが、largest-train露出maskは最後のactual train集合が揃った後、候補選定前に1版を固定する。段階1途中のprefixmaskはprovisional診断で、最終1248/672 maskへ読み替えない。途中は旧1248valの既固定curve・label-free生成費を使い、最終候補比較では保存済み全stage weightsを同じfinal eligible new-val subsetへ評価する。段階2を行わず止めた場合はそのactual最大prefixを基準に固定する。test maskは最大train+全valに対して固定し、freeze後1回だけ開封する。将来train未生成のまま最終maskが完成したとは主張しない。

## 全生成・保持の概算

273のknown opening/cache/bytecheck込み1.01372秒/familyを中心に置く。workingは.45–2.5秒/family+5–20秒/job、stressはfamily部分の上側を3倍に広げた。実測と独立した仮定であり、inclusive時間列を足してexclusive支配費にしていない。

| 計画 | 新独立family | 中心physical NN | known中心分 | working生成分 | stress生成上側分 | Arrow+cache中心 /保守forecast |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 段階1中心 | 288 | .550m | 4.87 | 2.7–14.0 | 38.0 | 38.7MB /189MB |
| 段階1最大 | 384 | .733m | 6.49 | 3.5–18.7 | 50.7 | 51.6MB /252MB |
| 段階2中心（累計） | 816 | 1.557m | 13.79 | 7.5–39.7 | 107.7 | 109.7MB /536MB |
| 段階2最大（累計） | 1392 | 2.656m | 23.52 | 12.9–67.7 | 183.7 | 187.2MB /914MB |

別途、opening/partition/資格・mask・export・停止・記録の準備15–45分を置く。これには既資格成果を再用できる部分と、futuresealed cacheの実対応を必要小範囲で確認する部分がある。既179.958秒compile/testlintや管理失敗を0へ置かず、新版資格が必要ならその全費を計上する。current binaryを使う限り新build/モデル取得は不要。現main/coreの採用を新teacherに反映する場合はsource/versionと小parityを先に束縛し、旧273速度の保証として流用しない。

physical NN/行は53.26、NN/family1908.40が観測値。working20–70行×40–80NN/行では段階2最大1.11–7.80m。安全counterの候補は273登録に合わせ48family×200ply×K64+warm36=614436/job、29job累計17.819mで、**旧27310mのresetではなく次契約の新総配分候補**。この値は新producer/configに実guardとして束縛するもので、prefix再生・隠れたwarm・terminal/枝実行を調べず数学的なphysical upper証明にしない。段階1の候補guard4.916m/8job、各job科学hard600秒・GPU30分より早く停止、全attempt/部分/NOT_STARTEDを保存する。科学jobは新契約が必要で本284は起動しない。

全保持はArrow675376B+tensor cache5778862B/1720=3752.46B/row。dense xだけ2496B/row、shared rows metadata平均約847B/rowが入る。表の保守forecastは70行/family×観測bytes/row×2.5（Git/raw・一時共存等）を置いた。圧縮率・prefix長・shard数の変化を保証しない。初期data384MiB、段階2はactual増分を確認して合計最大1GiB程度を候補にする。これは旧unusedとparent12GiBのfresh headroomから統括が配分する案で、現284の1MiBへ科学dataを持ち込まない。sharedモデル/engine/既cacheをコピー増殖しない。source/checkpoint・uniqueGit/一時/残metadataも別に含める。

新生成はworker2/infer4の2logical+運用1logicalを基本候補、RAM2GiB guard1.75/GPU6GiBをfresh admitする。273のpeak535MB/device全体上界1.722GBは短点の材料で、future VRAM/RSS保証ではない。学習はCPU1単logical/Torch1/RAM2GiB guard1.75/GPU0、固定clock測定との競合を避ける。generation wallとfit wallを同時に測って速度比較の根拠にしない。運用を含むaggregate4logical/RAM8GiBを維持する。

支配未知は長い局面/末尾pool、完走率、new distributionのNN/eligible比、cache物理量/Git一時共存、Python row objectsと評価callbackのmemory、test sealing/export費、dispatch/backupである。最初48/96完整familyの既jobにこれらを記録し、別巨大benchmarkや完璧な見積もりを入口にしない。表の3倍stressでも最大生成約3時間+準備45分で、約8時間残の主配分候補から外す理由にはならないが、残時点の実時計で更新する。

## 学習仕事を分ける

第一比較はD保持A/v3 H32/routezero4/raw a0b8/旧train-only尺度/Adam1e-4/WD0/rootmean/gameequalを固定する。量比較にλ変更・幅・target・routeを混ぜない。全stage fresh共通initial weights/seedを使い、256000seenと同eval pointsを固定する。旧5981 Bの学習成果は再用し、新48valへの評価だけを新費として計上できる。

データ量が変わると同seedでも選ばれるrowIDは同一にはならない。共通random variates/seed・登録family順を維持し、**actual batch SHAはstageごと記録する**。同データの256k/512k仕事対照では、前半2000stepのbatch列を一致させる。初期D parity・native input/output・scale/STMを有限fixtureで保持する。単に“samebatch”と書いて量条件間の同一row列を保証しない。

| train設計量 | 256kseen+10eval（旧1248val+新val中心1720を含む） | nominal epoch | 同量512k+15eval |
| --- | ---: | ---: | ---: |
| 6000 | 345680 samples | 42.67 | 646520 |
| 10000 | 385680 | 25.60 | 706520 |
| 30000 | 585680 | 8.53 | 1006520 |

推薦する追加仕事対照は**代表的な3万stageだけ512kseen**。同256kで最大量が未fitなら、データ増が無効か単に最適化仕事が不足かを一つの延長trajectoryで区別する。512kがDを超えることを量生成の事前gateにしない。名目epochはgameequal samplingで各rowへの均等epochではないため、family/cohortごとのsample露出も残す。

旧B328290 train/eval samplesのguardian4.926秒による短外挿は表の約5–15秒だが、load・record・native parity・freeze/testを含むjob見込み15–120秒を別に置く。callbackが全group metadataを保持するため、この速度を大規模保証にしない。最大30kのdense tensor約74.88MB、old/newvalおよびrootmean/zは小さいが、Python metadata・framework・export等を含むcurrent guardは実測する。全stage比較+代表仕事対照+parity/凍結testでCPU learn/eval **2.0–2.5m sample程度**を初期提案とし、actual row数×eval点×unique model/testを実契約へ束縛する。既274/280の費を新予算へ減額移転しない。

## 候補比較と判断変更

| 優先 | 何を判別できるか | 全工程費の候補 /保留・変更条件 |
| --- | --- | --- |
| 主: independent family入れ子量+一仕事対照 | 小96+36trainや高反復/新分布で見えなかった転移を量・仕事から検査。欠測量を「NNUE無効」へ変換しない | 上記全生成+split/cache/freeze、学習資格/解析/記録30–90分を追加計画。中心総1–2時間、working大側2–3時間、stress3–5時間程度（自然窓待ち未知）。改善が小さくても量でtrain-val gap/方向が変わる材料を得る |
| 並行短診断: 決定的K感度 | 同完全rootでK変更によるteacher残差方向/Action/πを測る。K256は真値・期待値正解ではない | 282の源・phase32rootを再用できる。純searchの少数記録と新serialization資格を基に、準備/修復/停止20–60分+科学1–5分を候補に置く。batch1とB8生成倍率を同一視しない。欠測を解消できなければUNKNOWNのまま主増量を継続 |
| 次設計: 位置付き経路/壁効果一群 | 既2distanceやDAG4が潰した位置依存の情報を増やす。DAG4一負例で全経路を棄却しない | 例:既goalmapから駒近傍位置付き値18等の一群。source/STM/壁更新/full-delta/undo・schema/roundtrip・train-onlyscale・学習・native葉費で2–4時間の粗い準備計画、fixture/学習15–60分。実cache costは未測。teacher残差がKに安定し量/仕事を増やしても補正alignmentが不利なら順位を上げる |
| leaf/horizon/history接続 | teacher rootmean蒸留がminimax葉に有効か、terminal/履歴/完成depth差を直接問う。teacherMSE改善と同時間利益を分ける | 完全prefixの同depth全合法root判断とterminal originを束縛する準備30–90分、科学5–30分の小有限対照候補。samewall/色交換/全予定強度は別に1–3時間または必要NN capの再計画。量改善が凍結teacher精度へ移ってもroot判断へ移らなければここを優先 |

これらの時間は開発・資格・失敗・停止・整理を含む概算で、過去fixtureが動いたことだけで全効用を保証しない。Kがteacher残差方向を大きく変えるなら、次のpair relabel/target用途を優先し、新生成K64へ無告知K256を混ぜない。Kが安定しても真の有用教師/leaftruthの証明ではない。量/学習の方向改善がなければ位置付き入力やleaf意味へ変える。高K修復だけを完了して役割上の成功とすることも、見積UNKNOWNだけで量を無期限保留することも避ける。

## 未選定評価に必要な観測量

新48selectionは設定/候補選定用。旧1248valは既使用curve。future96familyはfreeze後一巡の未選定評価候補で、testlabelsをearlystop/比較/split/maskへ使わない。candidate checkpoint/config/source/feature/scale/selectionrule/最大trainとmaskを固定し、D・train-only定数・旧Bまたは同seenの対照を同evaluateで測る。同tensor予測を再用し、uniqueモデル/全row/全plannedfamily/0eligible/censorを記録する。test後の設定再選定・交換はしない。

再用12selectionのλ200−D paired差SD .02228を機械的な参考にすると、95%halfwidth .01で約20family、.005で約77familyの正規近似となる。96を提案する根拠はこの精度候補とcohort/side分母の確保だが、selection済み小12群のSDを将来モデルへ保証していない。SDが2倍なら約4倍（.005で約306family）、履歴/phase/長gameの偏りでも必要量が変わる。96は十分性/検出力確定ではない。family bootstrap paired区間・実eligible分母と、期待する効果/精度を結果前に宣言する。将来より厳密な一般化や最高棋力には追加未選定family・同時間WDL・teacher K/モデル/leaf分布の別観測が必要で、MSE96gameだけで最終認定しない。

## 本284の実費・保存

14:54 ready/show/no pause/self assigned確認、claim、静的開始。extension23 runningloaded/configcontract/current24hash/正scheduler・monitor PIDtick、foreign compute0、CPU1 affinity、RAM点を直前admitして、保存費推定を1job実行した。**NN0解析 .295540秒、peak16572416B、newNN/modelimport/forward/fit/game/GPU0**。最多2/総60秒内、追加解析は予定しない。source-read180/管理90は新284、旧費は保持。未測LLM経過は別である。main/Rust/Python trainer/roles/runtime/Git/index編集0。

1MiBを274確認unusedから移転し274retain23MiB+2808MiB+2841MiB=元32MiBを維持した。旧274current4769457+保守Git/tmp/rem6815744=11585201B<23MiB。新284 source/output forecast512KiB、Git/temp込1MiB、旧unknown/WT/build保持を減額していない。[intake-storage.json](../../research-data/ai-sigma/frame22-independent-data-planning/intake-storage.json)とfinal receiptを参照する。

estimate.pyはpure stdlibでformat→check/lint、最大512MiB/CPU1/singleに制限。入力8compact/manifestのSHA、actual entry、出力purpose/schema、現在physics、source/report停止・bytes復元、notes/close/backupを自域へ保持する。研究Git/index/commitは統括soleownerへpath/hashを引渡し、本人独自commit0。推定と推奨は本人判断で、統括の採否/新実科学配分とは別。15:10早報、15:20以内停止引渡し、親23:36:03/旧caps/最高goal未達を維持する。

## 15:08以降の現在配分285/286への更新

上記は284の独立推奨であり、現在285実契約の数字へ黙って書き替えない。統括は **train最大1024/selection64/sealed future-eval64/最大1152family、K64 resident48/B8、NN17m、MAX6（資格1+生成5）** を登録した。現契約SHA `ba34cee53157891a2a825f6580fbd3220f33d20957b90b4732c7f1b8fc3e8b8a` を [scenarios-285-v2.json](../../research-data/ai-sigma/frame22-independent-data-planning/scenarios-285-v2.json) に束縛した。独立推奨の96eval/1248train上限とは区別する。

この実配分は量優先の実行開始案として支持する。1万に必要な新train平均は192familyの場合20.93適格行/family、3万には1024familyの場合23.46。working20行なら最大trainは26461で3万未達となるが、不足量を記録して学習効果をその量で測ればよく、自動増量/NNUE反証にはしない。中心では最大train43755行の潜在量があり、完整prefixの3万付近を使える。threshold超過48family blockを丸ごと採るなら実行前sample/RAM上界を再計算する。小candidateの不支持をこの取得の停止条件にしない。

MAX6に収まる具体packingは、生成job1=`192train+64selection`、job2=`192train+64future-eval`、job3/4各256train、job5=128trainである。第1段192train+64+64は320familyなので、1job256上限のまま一jobで全て受領するとはしない。job1停止から第1段trainとval接線を早く渡し、sealed evalはjob2を自然に完了して保全する。これは提案で、producer既登録順/UIDを後から並べ替える指示ではない。

1152familyの中心費はphysical NN2.198m、known opening/cacheまで19.46分。working生成8.8–49.7分、stress145.7分+準備15–45分。中心Arrow+cache154.9MBに対して、70行/family×2.5 retained/Git/tempの保守値は756.5MBで、**285 data forecast448MiBより大きいシナリオがある**。448MiBを成立済みと偽らず、最初の完整jobでbytes/row・cache共有/圧縮・必要Git共存を測り、物理guardへ近付く前に次段forecastとquantityを調整する。余分なdense全cacheコピーを作らない。current不足なら具体未使用/増分を返し、見積もりが完璧になるまで全生成を保留しない。17mに対し登録1152×200×65=14.976mがwarm/資格等の余裕を持つ候補計算だが、新sourceのguardとactual counterで検証する。

新286は**約10k/256k、約30k/256k、同約30k/512kの3fresh fit**を別実配分した。284の2trajectory内snapshot案からの統括選定として保持する。256k量比較primaryはstep2000、work primaryは4000、oldB LAST2000を同seen primary、BEST200はsecondary。同largest-dataの256k/512k条件は同初期/seed/サンプリングでfirst2000 actualbatch列の一致を検査できる。量が異なる条件のrow列を同一とはしない。

newval64の中心2294行+oldval1248、thresholdを完整一familyで跨ぎtrain上側10199/30199とする参考では、新fit sampleは10k/10eval393410、30k256k/10eval593410、30k512k/13eval950633、合計1937453。parity/oldB newval/凍結後将来評価等を加えて中心約2m。**実286の3m上限**に対して、完整48block overshoot・actualval行・全curveのfinalmask再評価/追加call・warm・fixtureを入れ直す必要がある。保存全curve予測scalar+IDを使ってfinalmaskで算術再集計できれば、不要なcurve再forwardを減らせる。λ0の現役形式は変更しない。checkpoint/native layoutは1モデル約49KB+PT約52KBを参考に、initial/primary/BEST/LAST/仕事対照・曲線・圧縮row scalar・Git/tempを含む64MiBは有力な出力配分だが、sharedteacher cache費とは別である。

64future-evalはpilotとして実施可能。旧12群SDを当てた参考halfwidthは約.00546、SD倍なら.01092となる。64を十分量認定せず、96の独立推奨を有力将来精度案として残す。今回登録familyの差替えやtest結果後の追加/交換を要求しない。

**受領interfaceの不整合**：285の正本は64selection/64future-eval、続いて受領した286本文には48selection/96future-evalとmax1392の字句がある。統括へ15:13頃に具体差を返した。生成前に双方の正本を統一できるが、既登録/生成familyを結果で64/64→48/96へ読み替えない。現在のNN0/源準備は止めず、実data binding/finalmaskには統一されたproducer handoffを用いる。別ownerの修正/実データ・採否は本284が完了したとは主張しない。

第二NN0推定は .093067秒/peak16211968B、2job合計 **.388607秒**。NN/modelimport0、CPU1single、2/2枠を使用し追加解析なし。最初の見積/source/結果を保持し、新285/286実配分は旧284capのresetではない。
