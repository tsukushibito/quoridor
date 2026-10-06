# 公開Sigma 100万行・GPU学習の実行依頼

Beads `quoridor-4lc.319`。ユーザーは2026-10-06、Rootの100万行GPU学習案を承認し、待機中の学習セッションへの実配分を指示した。旧待機限定契約をこの仕事に置き換える。固定チーム、過去frame、旧GPU残予算は再開しない。

同日の独立レビュー後、ユーザーは**元観測だけで100万行を再抽出**する案を明示選択した。以下は前向きのv2差分で、元のmixed corpus・抽出規則・費・失敗・SHAを保存したまま適用する。

- 全43の前半original観測だけを候補にし、新T1,000,000/V50,000/sealed E50,000を作る。naiveLR後半は今回の教師へ入れず、鏡側だけ保持されたaliasを元盤面の観測へ読み替えない。有効originalの同入力・別勝敗は保持する。元のseedとalias単位splitは可能な限り維持し、original-only対象と新version/output/configを結果前に固定する。
- 最初のmixed corpusのoriginal alias distinct942,288/47,187/47,191は行数ではない。実保持original行は824,069/41,230/41,322で、単にfilterするだけでは指定件数に届かない。v2で不足を繰返し・LR変換・別盤面ラベルのコピーで補わない。
- XOR priorityの複数stream独立性や厳密な包含確率を主張しない。v2はoriginal-onlyの全域固定擬似乱数順位で新規抽出し、sampling-planに実規則・tie扱い・候補分母・実保持率を記録する。抽出の数学を別方式へ変える必要があればRootへ戻す。v1のplan/source SHAへ訂正を書き込まず別補足へ残す。
- 再取得は別attempt系列に最大2,163,752,072B（fixed43合計＋30%）を新しく配分する。最初の系列のcap/実取得1,664,424,671Bは保持し、系列合算最大4,327,504,144B。前回の未使用をrefundしない。decode/資格/compile等の時間は既7200秒/600秒の残内、GPU3600秒は未消費ならそのまま。再取得・再処理は約6分の旧実績であり保証ではない。
- 原mixed corpus191,400,000B・元証拠を保持し、新original-only出力/scratch/証拠/Gitまで768MiB内のpeak forecastへ含める。新assets rootをdirected manifestへ加え、fresh within・既slot非競合成立後に再処理する。成立しない場合は具体不足をRootへ戻し、旧保護資産を削除しない。
- F1 frozen manifestとtestcacheのlabel開封前照合、F2教師適格と露出UNKNOWNの分離、F3一candidate/D/定数のみの最終評価、F4row monitor・実fit config/曲線予定の固定は通常修正する。F5は上の説明と実規則を一致させる。同reviewerへv2の差分とC++ z/STM signの一次sourceを渡し、導入採用前に確認する。本fitはv2の入力/ラベル/主指標と資格成立後のみ。sealed最終評価はfreezeと修正review後の一巡に保つ。

### v2入口失敗後の同scope取得枠

2026-10-06のjob1ea785c5はチェック未完了後のshell後続submitにより入口違反で開始し、取消・子回収された。旧費85.864364695秒、系列2取得845,837,744B、元output/source/progress/未保存reservoirの喪失を保持し、後着withinをbefore-start成功へ読み替えない。Rootは確認済み系列1の未使用枠から256MiBを系列2へ前向き移譲した。原cap各2,163,752,072Bは履歴として保持し、現在有効ceilingは系列1=1,895,316,616B、系列2=2,432,187,528B、合算4,327,504,144B不変。系列1実費1,664,424,671Bと失敗系列2実費を減額しない。

検証済み4blobのimmutable直接再用で必要再取得1,534,317,836B、系列2実残1,586,349,784Bの範囲で復旧できる。元seed/split/順位/original-onlyの数学を変更せず再runでreservoirを再計算する。既7200秒/768MiB内の全attempt・scratch・失敗証拠を保持し、fresh observer完了成功→値/admission確認→source/config/正確停止/残予算確認→submitを依存する別callで順序付ける。source制御修復差分を明示し、失敗しても後続launchが走る経路を残さない。Root通常復旧allocationとreceiptを参照する。

## 基準学習後の正しい左右反転

ユーザーはoriginal-onlyで学習フローを確立した後、正しい左右反転を追加して比較する方向を承認した。まず上のv2をaugmentation OFFで進め、入力/教師/供給/詳細曲線/checkpoint/native対応・保存/評価callerの機能と基準結果を得る。距離超えや棋力改善を次段の恒久gateにしない。

- 次段は正規盤面から左右反転を定義し、正しいnative特徴の再計算との一致・二回反転の完全復帰・合法手/遷移/ゴール/手番/ラベル対応を独立oracleと非対称壁/境界fixtureで確認する。既公開後半のnaiveLRを修正して使ったことにせず、original-only cacheはimmutableに保つ。モデル/探索の数学・重みlayoutは変更しない。
- 一括反転cacheを保存する方式より、train batch供給時に50%の確率で正しい左右反転を適用するオンラインaugmentationを優先する。元観測ID/分割/ラベルを保持し、shuffleと別の固定seed RNGで反転選択を記録する。validationは固定した元入力で比較し、反転前後の値の差はsecondary。左右だけに限定し、上下/90度回転/プレイヤー交換を自動追加しない。
- 反転なし/ありは同じ元データ・split・train-only尺度・初期重み・元行順序・batch/LR/optimizerと同更新回数/seenで比較する。先に成立したbaselineの完了更新数を比較対象として固定し、early stopping/BEST選定と計算量を区別する。反転を加えて見かけの保存行数やepochを倍にしない。
- 現契約のone fitはoriginal-only基準run。基準フロー成立後のaugmentation比較は、同一条件・50%LR一要因・追加一fitまでを次の具体runにし、実残GPU全job3600秒/compile600秒/768MiB内で双方の比較と保存・回収を収めるforecast/条件を結果前にRootへ渡す。Rootが既承認範囲と資源・計時slotを確認して配分し、同じ人間方針の再承認は要求しない。資源不足、batch/LR等の別変更が必要なら具体不足・代替をRootへ戻す。初回runの結果を見てLR/幅/教師まで同時変更するsweepは未配分。
- 新反転境界は同reviewerへ関連差分・native oracle/fixtureを戻す。損失、左右一致、全時間と凍結後の棋力を採用指標とするが、現在のsealed評価は契約の一候補/D/定数一巡のまま。開封後の同testで新候補を選び直さず、augmentation最終評価・新arenaに必要な未選定入力と予算は別具体配分で用意する。元の対局数が増えたことにはせず、元観測の量・多様性の拡大も競合として保持する。

## 目的と選択済み方針

公開Sigma全43 NPZの全域から訓練1,000,000行、validation 50,000行、最終評価50,000行を構成し、現QF1＋距離logit残差H32のGPU学習を実施する。これは保存する適格観測行数であり、distinct盤面数・独立game数・学習seen数ではない。学習効果、過学習の推移、GPU供給から保存までの全工程を確認する。小候補の距離超えや全43 distinct数の確定は開始条件にしない。

- 固定公開source `751186344fc52ad0c29bc65922e62c6fa915f006`、43 NPZ（18,914,078保存行、compressed合計1,664,424,671B）を既存source manifestで確認する。ネットワーク取得とboundedなdecode・変換を今回許可する。同blobを必要範囲で再用し、単一shardずつ処理して全rawを保存しない。
- 全43ファイルに機会のある固定seedの抽出・分割を行う。先頭行、先頭入力群、直近数cycleだけを採る方式を使わない。source/shard/row index、採択確率・件数、原入力とモデル入力の資格・SHA、各分割の実distinct数、phase proxyを記録する。全体の完全な重複除去・全域入力ledgerの完成を恒久gateにしない。
- 入力・座標・範囲・finite・合法到達性など、証明できる不正を除く。公開z0は不正と断定せず、終了理由が不明な教師として初回学習・選定・最終評価から除外し、元値と除外理由・分母を残す。有効な同入力の複数勝敗観測は保持する。1群の不正から有効な別観測を一律に消さない。
- 訓練とvalidationの盤面一致を理由に訓練行を削除しない。同じ元観測のコピーとoriginal/reflectionの兄弟は同じ分割へ束縛する。反射対応はsourceと実byte/非対称壁fixtureで確認し、見かけの入力一致から由来を捏造しない。異なるcycleの同盤面は許容し、source game/history欠測を独立gameの証明にしない。
- 分割・抽出seedと規則は結果前に固定する。最終評価labelsはcandidate/config/checkpoint選定規則freezeまで別出力でsealed。過去の開封済み43/RuleA48/96/173を新しい未見評価として扱わない。可能な元観測IDを旧使用manifestと照合して露出を報告し、確認できない履歴はUNKNOWN。新testは公開分布のheld-out観測評価であり、完全な未見game棋力評価ではない。
- 主samplingはepoch shuffle、各epochで全train行を一度ずつ消費し、最後の小batchも記録する。主loss/validationはrow平均、入力群等重みと既知/未見入力・source/phase別はsecondary。入力群を均等抽出するgame samplerを公開inputgroupへ代用しない。尺度・距離/定数基準はtrainだけで固定する。

## 実装と学習

既存の現役 `python/quoridor_training` とRust `quoridor-data`/runnerを拡張し、省容量cacheとbounded batch供給を実callerへ接続する。100万行dense tensorの約2.51GBを新保存768MiBへ押し込まない。bitset等のlossless表現から必要batchだけ展開し、元入力・モデル入力・ラベルの対応をfixtureとnative資格で確認する。全行JSONの巨大metadataや全row Python dictを常駐させない。新しい学習器コピーや互換shimを残さない。

モデル/特徴/targetはQF1＋D残差H32/route4 off/decisive outcome zを維持する。新特徴・幅・方策・teacher生成は行わない。初回はAdam、weight decay 0、FP32、LR3e-5、batch128のepoch方式を基本にする。低LRは旧詳細曲線Bの末期退行の小ささを開始根拠とし、新corpusで最適と認定しない。

GPU供給の実装資格としてbatch128/512/2048の短い計算・転送計測を合計30秒以内で行える。学習重みを選ぶ実験に使わず、同固定入力・初期重み・数学で時間/VRAM/数値を確認する。128から変える場合は、数値対応と全費の結果に基づく推奨batchと理由をRootへ渡し、Root経由の人間判断前に本fitのbatch/LRを変更しない。128でもGPU本fitを開始でき、大batchの判断待ちを全作業gateにしない。

初回one fitは最大20epochs、validation primary rowMSEによるearly stopping（patience3epochs/min_delta1e-4）、GPU全job費3600秒で止める。短い資格失敗の通常修復は可能だが、LR・モデル・データ・教師のsweepや本fitの自動再学習は行わない。1,000,000seenは1epoch相当であり、100万種類でも完了学習でもない。予算内で途中停止ならactual epoch/step/seen・coverageをそのまま報告する。

曲線はstep0/1/2/5/10/20、最初2000更新は25更新ごと、その後1250更新ごと＋epoch境界を初期案にし、最大250点に結果前に束縛する。固定train診断subsetと全validationを同forwardの保存値から集計し、eval費を課金する。epoch境界にはtrain全件誤差も測る。evalが支配する場合は、dense初期観測を残し、結果を見て勝手に間引かず全費と予定点をRootへ報告する。

CSV/JSONにstep、seen、actual completed epochと進行率、wall、train診断/fulltrainの区別、validation row/group MSE、距離/定数基準、符号・飽和を保存し、PNG/SVGを出力して画像を確認する。補間を実観測にしない。initial/BEST/LASTと凍結候補、native full/delta/undo/STM/ScalarSIMDの対応を限定確認する。訓練・選定の完了後、一候補/D/定数をsealed最終評価へ一巡する。評価後の再選定・訓練転用・新arenaは未配分。

## writer・資源・停止

- 同じsaved thread `01a1100f-6d45-78e0-8a87-84503ff0fbf6` を再用する。Root同fullaccess（danger-full-access/never）、同model/effort。cwdは新managed WT `/workspaces/quoridor/.worktree/learning-million`、base main `d61a91d`。本人はready/show/ownerと実cwdを確認してclaimし、待機解除を実開始と区別する。
- 本人一人がWTの `crates/quoridor-data`、runnerのdataset/cache入口、`python/quoridor_training`、対応tests/config/docsを編集する。core/ai/nnueの探索数学・モデルレイアウトは変更しない。Rootのみmain/Git index/commit統合担当。stage/commit/ref/merge操作・main source書込は行わない。下記の独立レビュー一担当に限り学習担当から直接依頼でき、それ以外の再帰委譲は行わない。停止path/SHAでRootへ引き渡す。
- CPU最大2logical（探索318の0,1を避け2,3を候補にactual affinity/topology確認）、RAM family最大4GiB、VRAM最大6GiB。検索profile・速度比較・arena実時計は本fitと非重複にする。2026-10-06の連携調整により、SHA/sizeを確認したprivate immutable native binary/libraryへ実callerを束縛した後は、318→320の一人ずつのビルド・NN0ソフト検証をCPU0,1/RAM2GiB/GPU0で並行可。共有targetのlearner reader/writerは0、builder writerは一人、合計資源は親内を守る。同時実行費は競合ありと記録し速度差の根拠にしない。前のjobを無断interruptしない。private ELF約1.15MBも本768MiBへ含める。
- 初回実data取得/decode/変換/資格は累計7200秒、compile/testsは600秒、GPUfit/qualification/transfer/eval/init/failure/recovery合計3600秒、最終CPU/native評価・解析300秒。取得最大固定43blob compressed合計に再試行30%まで、全attempt費を記録。旧GPU7200 UNKNOWN/旧3600残3586秒は保持し、本新配分と混同しない。
- 新保存768MiB inclusive（compact corpus/index/provenance 512、shard scratch96、build/source/WT48、weights32、必要evidence/Git/temp80MiBが目安）。Rootのfresh directed admissionと再配分を参照し、旧保持12GiB/UNKNOWN128MiBを維持する。Rootは終了済み273/274/275 future growth512MiB、旧1d2 growth160MiB、完了maintenance future growth96MiBを前向き移譲する。旧current資産・科学費・失敗・原capは変更/削除せず、未使用future予約の使途だけ変更。新rootをaggregateへ追加してpeak含むforecastが成立するまで大取得/computeは開始しない。自己tmpの不要scratchはSHA/provenanceと資格後に撤去でき、共有cache・旧資産は削除しない。
- 通常の実装詳細・修復・lossless転送は自律的に進める。100万行の意味変更、未知0の教師採用、重要なsplit変更、batch/学習/特徴変更や容量・時間超過が必要なら具体不足・競合・全費をRootへ戻す。達成不能なら不足件数を報告し、繰返しで100万行へ水増ししない。
- 長jobは既存research-jobのguardian/子回収/一度の完了通知で起動してturnを終了する。周期的LLM監視・固定role・新server/cronを作らない。pause、owner変更、budget超過、入出力不整合、未解決の重大資格不足で自己子を正確に回収し停止する。

## 成果と受入れ

初報はclaim/actual cwd/固定source/資源admission/実取得・実学習の開始有無を短く報告する。次はデータ実分母・distinct/alias・GPU供給の意味ある結果、学習曲線、最終評価、重要判断か障害の節目でRootへ通知する。Root thread `01a0f2e9-357d-7ef3-a2fe-b16f80accda5`、宛先issue `quoridor-4lc`。定型通知のためのturnを作らない。

ユーザーが担当直接依頼＋Root採用時確認を選択したため、学習担当は次の条件で独立レビューを一担当へ直接依頼できる。Rootによる監視・起動代行・毎回の承認待ちを作らない。

- 起動条件は、公開データの入力/STM変換・幾何反転・zと除外理由・元観測alias/分割・compact encoder/decoderと学習callerへの接続が、仕様・source SHA・差分・fixture結果としてレビュー可能な版になった時。原sourceと固定仕様から確認するread-onlyレビューをまとめて一度依頼し、指摘修正は同じレビュワーへ戻す。毎fit/epoch/runの再レビューは行わない。
- 対象は上記導入境界だけ。新研究案、LR/batch/modelの選定、全史監査、全dataset再decode・全suite再実行を依頼しない。元資料・仕様・問い・対象版/差分・実検証を渡し、自分の長い推論履歴・全会話forkを引き継がせない。レビュー中は対象版の整合を保証し、変更した場合は変更点を明示する。
- レビュー子issueをBeadsに登録し、目的・対象・read-only/証拠writer範囲・owner・版・実予算・停止・受入れを記載する。独立saved session又はfresh-context subagentを必要な一担当だけ作れる。追加レビュワー、レビュー側の再帰委譲は未配分。担当もRoot同fullaccess/neverを明示確認し、モデル/effortを無断変更しない。
- 予算は親319の768MiB内evidence80MiBからreview2MiBを取り分け、親増額・current資産減額なし。CPU最大1logical/RAM512MiB、読み取りcommand累計60秒＋必要な小NN0 fixture累計20秒を親compile/tests600秒の残内から前向き配分する。build/NNforward/学習/GPU/新取得/重scanは0。親・探索の計時とfixtureを競合させず、source静的確認は並行できる。2MiBにreport/metadata/Git/tmpを含めてforecastを更新する。
- レビュワーはsourceを変更せず、対象版・指摘・根拠・重大度・確認限界を依頼担当とRootへ返す。通常修正は学習担当が行い、指摘確認を同レビュー担当へ戻す。重大な意味/分割/ラベル/設計変更、想定外の矛盾、追加予算、レビュー要否の不明はRootへ戻す。
- 導入の採用・最終評価releaseでは、Rootが必要境界を確認した証拠と重大未解決指摘の有無を確認する。採用前に自己レビューだけで独立確認を代用しない。影響しない実装/準備/測定を全稿待ちで止めず、未確認境界の採用だけ保留する。重要な研究結論のレビューは別の採用判断で要否・対象を決める。

停止時にsource/process/正確child回収、変更path/SHA、取得source/hash/配布条件、実分母/除外、元観測aliasとsplit、cache/input/model binding、曲線/画像、whole費、checkpoint/freeze/評価と限界、未完了と次判断を残す。raw/model/cacheはignored assetsへ、small manifestと必要圧縮証拠をmain専用保存先へRootが統合する。Beads status/backupを本人が維持し、最高棋力・独立game汎化・新データ量だけの因果を先取りしない。

## 学習済みnative資格の仕上げ（2026-10-06）

同じ凍結BESTのScalar19状態/P1P2・delta16children・親履歴対応はPASS_LIMITED、明示ScalarSIMD/inplace undoは未確認として保持する。既存APIを使う最小の維持native caller/fixtureで、同19状態/16childrenの明示mode・make/unmake・親accumulator/history/ply復帰を確認する。初期重みの既資格とBEST=LAST byte対応は再用し、新モデル/数学/入力・追加fitへ拡張しない。SIMD mode資格を残差headのSIMD高速化の証拠にはしない。

318比較STOP→320最終software STOPの後に、ONE completion phase全体最大120秒を既compile/tests600・最終CPU/native300秒の各確認済み残内で配分する（outer120/worker100、数値仕事最大30秒、新forward上界256は既samples60m残内）。実残の範囲確認とfresh source/bin/資産binding・storage・物理成立後のみ開始。CPU2,3/RAM4/GPU0/768MiB不変、nativeはprimaryCPU2・既admission guardを保持する。unsupported APIを理由に未確認資格をPASSへ読み替えず、必要なsupported callerを版固定しold ELF/proofを保全する。通常source整形・限定oracleを使い、shared target writerは一人。新attempt失敗は保持し自動反復しない。凍結後の一候補/D/定数一巡は既契約のまま、native仕上げと実freeze/cache一致の確認前にsealed labelsを開けない。
